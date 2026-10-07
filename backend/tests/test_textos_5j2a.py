"""Fase 5J-2a — el informe y el PDF sin identificadores con barra baja ni palabras sin tilde.

El motor sigue guardando CÓDIGOS en el resultado (los fija la foto del §19); lo que cambia es
cómo los REDACTA M14 (`app/engine/textos.py`). Estos tests barren el Markdown y el texto real
del PDF en casos que ejercitan ramas distintas: veto competitivo, RVC improbable, hipoteca,
perfil rentista, escalera degenerada, sin comparables, otras fuentes y estados de ocupación.
"""
from __future__ import annotations

import io
import re

import pytest
from pypdf import PdfReader

from app.engine.contracts import AnalisisInput, FinanciacionInput, OcupacionInput, RentistaInput
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from app.engine.textos import ETIQUETAS, SIMBOLOS, etiqueta, legible
from app.services.pdf_service import informe_a_pdf
from tests.test_golden_caso19 import entrada_caso_19
from tests.test_puja_inviable import _caso_inviable

IDENTIFICADOR = re.compile(r"(?<![\w])[^\W\d_][^\W_]*(?:_[^\W_]+)+(?![\w])")
# Palabras que el motor escribía sin tilde (códigos y textos), en minúscula.
SIN_TILDE = re.compile(r"\b(juridico|tecnico|urbanistico|ocupacion|comercializacion|plusvalia|critico|"
                       r"vacio|semaforo|adquisicion|posesion|informacion|valoracion|analisis|deposito|"
                       r"regimen|metodo|limite|minimo|maximo|numero|tramite|desalojo_|subsanacion)\b")
RATIO = "adjudicacion.ratios.judicial_boe.vivienda.ocupado"


def _con(e: AnalisisInput, **cambios) -> AnalisisInput:
    return e.model_copy(update=cambios)


@pytest.fixture(scope="module")
def informes() -> dict[str, str]:
    e = entrada_caso_19()
    base = cargar_defaults()
    casos = {
        "dorado": ejecutar_analisis(e),
        # RVC < rvc_veto del perfil ⇒ VETO-COMP-01, cuyo motivo trae «P_max».
        "veto_competitivo": ejecutar_analisis(e, params=base.con_overrides({RATIO: 1.0})),
        # RVC entre 0,80 y 0,90 ⇒ la línea del plan que decía «P_ideal».
        "rvc_improbable": ejecutar_analisis(e, params=base.con_overrides({RATIO: 0.532})),
        "hipoteca": ejecutar_analisis(_con(e, financiacion=FinanciacionInput(
            tipo="hipoteca", preaprobada=True, ltv=0.7, interes_anual_pct=3.5))),
        "rentista": ejecutar_analisis(_con(e, perfil="rentista", rentista=RentistaInput(
            renta_mensual_estimada=950, ibi_anual=350, comunidad_mensual=60))),
        "degenerado": ejecutar_analisis(e, params=base.con_overrides({"capital.coste_capital_anual": 0.31})),
        "inviable_aeat": ejecutar_analisis(_caso_inviable()),
        "vacio_arrendado": ejecutar_analisis(_con(e, ocupacion=OcupacionInput(estado="arrendado_anterior"))),
    }
    return {k: r.informe_markdown for k, r in casos.items()}


def test_los_casos_ejercitan_las_ramas_previstas(informes):
    assert "VETO-COMP-01" in informes["veto_competitivo"]
    assert "RVC 0,80–0,90: pujar solo el precio ideal" in informes["rvc_improbable"]


@pytest.mark.parametrize("caso", ["dorado", "veto_competitivo", "rvc_improbable", "hipoteca", "rentista",
                                  "degenerado", "inviable_aeat", "vacio_arrendado"])
def test_el_informe_no_muestra_identificadores_ni_palabras_sin_tilde(informes, caso):
    # Los códigos de regla van entre comillas invertidas (`VETO-COMP-01`) y no llevan «_».
    texto = informes[caso]
    assert IDENTIFICADOR.findall(texto) == []
    assert SIN_TILDE.findall(texto.lower()) == []


@pytest.mark.parametrize("caso", ["dorado", "veto_competitivo", "rvc_improbable", "rentista"])
def test_el_pdf_no_muestra_identificadores_ni_palabras_sin_tilde(informes, caso):
    pdf = informe_a_pdf(informes[caso])
    texto = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
    assert "VS prudente" in texto                      # premisa: se ha extraído texto de verdad
    assert IDENTIFICADOR.findall(texto) == []
    assert SIN_TILDE.findall(texto.lower()) == []


def test_el_motivo_del_veto_competitivo_se_redacta_legible(informes):
    assert "Rojo competitivo: precio máximo queda tan por debajo" in informes["veto_competitivo"]


# ─────────────────────────── funciones ───────────────────────────

def test_legible_sustituye_simbolos_y_codigos_pero_no_palabras_sueltas():
    assert legible("incorporadas a C_F (o inexistentes)") == "incorporadas a costes fijos (o inexistentes)"
    assert legible("Subsanar: posesion_verificada; δ_v") == "Subsanar: posesión verificada; descuento de prudencia"
    # Sin barra baja no se toca nada: «reforma» y «medio» son también palabras de una frase.
    assert legible("reforma de nivel medio") == "reforma de nivel medio"
    # Un código desconocido se queda como está (el barrido de arriba lo detectaría).
    assert legible("valor otra_clave") == "valor otra_clave"


def test_etiqueta_de_codigos_de_una_palabra():
    assert etiqueta("juridico") == "jurídico"
    assert etiqueta("semaforo") == "semáforo"
    assert etiqueta("muy_alto") == "muy alto"
    assert etiqueta("no_existe") == "no_existe"
    assert etiqueta(None) == ""


def test_ninguna_etiqueta_ni_simbolo_traducido_lleva_barra_baja():
    for v in [*ETIQUETAS.values(), *SIMBOLOS.values()]:
        assert "_" not in v, v

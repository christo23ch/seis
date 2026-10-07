"""Fase 5J-1 — datos del procedimiento de subasta (diseño A, ADR-0022).

Vigila tres cosas:
1. Los importes que calcula `app/engine/procedimiento.py` con los parámetros T3, para
   cada procedimiento y supuesto (régimen «No sé», vivienda habitual «No consta»,
   cantidad reclamada, depósito mínimo, datos ausentes).
2. Que los UMBRALES son informativos: cambiar la cantidad reclamada o la vivienda habitual
   no mueve ni una hoja del resto del resultado (la guarda del §19 está en
   `test_invariante_5h1.py`). Desde la Fase 5J-2b el depósito, la forma de puja y los meses
   de inmovilización SÍ entran en el cálculo; eso lo vigila `test_deposito_plazo_5j2b.py`.
3. El texto del subapartado del informe: aviso orientativo, sin claves internas y en
   formato español.
"""
from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from app.engine import procedimiento
from app.engine.contracts import ActivoInput, AnalisisInput, SubastaInput
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19

VT = 152000.0


def _entrada(*, activo: dict | None = None, **subasta) -> AnalisisInput:
    base = entrada_caso_19()
    return base.model_copy(update={
        "subasta": base.subasta.model_copy(update=subasta),
        "activo": base.activo.model_copy(update=activo or {}),
    })


def _calc(**kw):
    return procedimiento.calcular(_entrada(**kw), cargar_defaults())


# ─────────────────────────── caso §19 tal cual ───────────────────────────

def test_caso19_aplica_el_regimen_desfavorable_y_lo_declara():
    r = _calc()
    assert (r.procedimiento, r.procedimiento_deducido) == ("judicial", True)
    assert (r.regimen, r.regimen_asumido) == ("judicial_lec_2025", True)
    assert r.deposito_pct == 0.20 and r.deposito_eur == 30400.0 == r.capital_para_pujar
    assert (r.plazo_pago_dias, r.plazo_pago_unidad) == (20, "naturales")
    assert r.meses_inmovilizacion == 1.8
    # Fase 5J-2b: sin fecha de inicio, el plazo suma el del régimen más largo (2015: 2,5 meses).
    assert r.meses_inmovilizacion_aplicados == 2.5 and not r.meses_inmovilizacion_asumidos
    assert any(a.startswith("No consta cuándo se inició el procedimiento judicial") for a in r.avisos)
    assert any("el depósito es del 5 % y el plazo de 40 días" in a for a in r.avisos)


def test_caso19_vivienda_no_consta_se_asume_habitual():
    r = _calc()
    assert (r.vivienda_habitual, r.vivienda_habitual_asumida) == ("no_consta", True)
    # Sin cantidad reclamada, la vivienda habitual solo se aprueba desde el 70 %.
    assert r.puja_minima_aprobable == 106400.0 and r.umbral_aprobacion_pct == 0.70
    assert r.puja_aprobacion_segura == 106400.0
    assert (r.suelo_absoluto_pct, r.suelo_absoluto) == (0.60, 91200.0)
    assert any(a.startswith("No consta si es la vivienda habitual del ejecutado: se asume que sí")
               for a in r.avisos)


def test_caso19_avisa_del_deposito_declarado_distinto():
    r = _calc()
    assert r.deposito_declarado_pct == 0.05
    assert any("El depósito indicado en el alta (5 %) no coincide" in a for a in r.avisos)


# ─────────────────────────── judicial ───────────────────────────

def test_judicial_posterior_sin_vivienda_habitual_umbral_general_50():
    r = _calc(procedimiento="judicial", regimen_judicial="posterior",
              activo={"vivienda_habitual_ejecutado": "no"})
    assert not r.regimen_asumido and not r.procedimiento_deducido
    assert r.puja_minima_aprobable == 76000.0 and r.umbral_aprobacion_pct == 0.50
    assert r.puja_aprobacion_segura == 106400.0
    assert r.suelo_absoluto is None
    assert not any("No consta cuándo" in a for a in r.avisos)
    assert any("Sin la cantidad reclamada" in a and "desde el 40 %" in a for a in r.avisos)


@pytest.mark.parametrize("cantidad, esperado", [
    (65000.0, 65000.0),    # cubre la deuda y supera el 40 %
    (50000.0, 60800.0),    # cubre la deuda pero el suelo del 40 % manda
    (90000.0, 76000.0),    # la deuda supera el 50 %: manda el umbral general
])
def test_judicial_posterior_ruta_del_40_con_cantidad_reclamada(cantidad, esperado):
    r = _calc(procedimiento="judicial", regimen_judicial="posterior", cantidad_reclamada=cantidad,
              activo={"vivienda_habitual_ejecutado": "no"})
    assert r.puja_minima_aprobable == pytest.approx(esperado)
    assert not any("Sin la cantidad reclamada" in a for a in r.avisos)


@pytest.mark.parametrize("cantidad, esperado", [
    (None, 106400.0),      # sin deuda conocida: 70 %
    (95000.0, 95000.0),    # cubre la deuda: puede bajar del 70 %…
    (80000.0, 91200.0),    # …pero nunca del 60 %
])
def test_judicial_vivienda_habitual_declarada(cantidad, esperado):
    r = _calc(procedimiento="judicial", regimen_judicial="posterior", cantidad_reclamada=cantidad,
              activo={"vivienda_habitual_ejecutado": "si"})
    assert not r.vivienda_habitual_asumida
    assert r.puja_minima_aprobable == pytest.approx(esperado)
    assert r.suelo_absoluto == 91200.0


def test_judicial_anterior_deposito_5_plazo_40_sin_suelo_de_deuda():
    r = _calc(procedimiento="judicial", regimen_judicial="anterior", cantidad_reclamada=30000.0,
              activo={"vivienda_habitual_ejecutado": "no"})
    assert r.regimen == "judicial_lec_2015" and not r.regimen_asumido
    assert r.deposito_eur == 7600.0 and r.plazo_pago_dias == 40
    # En 2015 bastaba con cubrir lo reclamado, sin el suelo del 40 %.
    assert r.puja_minima_aprobable == 30000.0
    assert not any("no coincide" in a for a in r.avisos)
    # En 2015 la norma dice «supere el 50 %»: se avisa de que igualarlo no basta.
    assert any(a.startswith("La norma exige superar el 50 %") for a in r.avisos)


def test_umbral_inclusivo_no_avisa_de_superarlo():
    r = _calc(procedimiento="judicial", regimen_judicial="posterior", activo={"vivienda_habitual_ejecutado": "no"})
    assert not any(a.startswith("La norma exige superar") for a in r.avisos)


def test_ningun_aviso_muestra_codigos_internos_de_la_especificacion():
    for r in (_calc(), _calc(procedimiento="tgss"), _calc(procedimiento="judicial", regimen_judicial="anterior")):
        assert not any(re.search(r"\bP\d+\b", a) for a in r.avisos), r.avisos


def test_deposito_minimo_de_1000_euros():
    r = procedimiento.calcular(_entrada(procedimiento="judicial", regimen_judicial="posterior",
                                        valor_subasta=3000.0), cargar_defaults())
    assert r.deposito_eur == 1000.0


# ─────────────────────────── otros procedimientos ───────────────────────────

def test_aeat():
    r = _calc(procedimiento="aeat")
    assert r.deposito_eur == 7600.0 and r.plazo_pago_dias == 15
    assert r.puja_minima_aprobable == 76000.0 and r.puja_aprobacion_segura == 76000.0
    # Sin regla de vivienda habitual: «No consta» no se asume ni pone suelo del 60 %.
    assert not r.vivienda_habitual_asumida
    assert (r.suelo_absoluto_pct, r.suelo_absoluto) == (0.10, 15200.0)


def test_tgss_declara_los_datos_sin_confirmar():
    r = _calc(procedimiento="tgss")
    assert r.deposito_eur == 38000.0 and r.plazo_pago_unidad == "habiles"
    aviso = next(a for a in r.avisos if a.startswith("Datos sin confirmar en la norma"))
    assert "depósito para pujar" in aviso and "plazo de pago del resto" in aviso


def test_notarial_sin_umbrales_no_calcula_puja_aprobable():
    r = _calc(procedimiento="notarial")
    assert r.deposito_eur == 7600.0
    assert r.puja_minima_aprobable is None and r.puja_aprobacion_segura is None
    assert any(a.startswith("No hay umbrales de aprobación confirmados") for a in r.avisos)


def test_extrajudicial_sin_deposito_confirmado_no_inventa_capital():
    r = _calc(procedimiento="extrajudicial", activo={"vivienda_habitual_ejecutado": "no"})
    assert r.deposito_eur is None and r.capital_para_pujar is None and r.plazo_pago_dias is None
    assert r.puja_minima_aprobable == 76000.0
    assert any(a.startswith("No hay un depósito confirmado") for a in r.avisos)


def test_concursal_todo_ausente():
    r = _calc(procedimiento="concursal")
    assert (r.deposito_eur, r.puja_minima_aprobable, r.meses_inmovilizacion) == (None, None, None)


@pytest.mark.parametrize("fuente", ["banco", "privada"])
def test_venta_no_reglada_por_fuente(fuente):
    r = _calc(fuente=fuente)
    assert (r.procedimiento, r.procedimiento_deducido, r.regimen) == ("no_aplica", True, None)
    assert r.deposito_eur is None and r.datos_legales == []
    assert r.avisos[0].startswith("Venta no reglada")


# ─────────────────────────── vivienda habitual ───────────────────────────

def test_no_consta_en_un_garaje_no_se_asume_vivienda_habitual():
    r = _calc(activo={"tipologia": "garaje"})
    assert not r.vivienda_habitual_asumida and r.suelo_absoluto is None


def test_entrada_anterior_a_la_fase_usa_el_booleano():
    assert _calc(activo={"es_vivienda_habitual": True}).vivienda_habitual == "si"
    # `False` antiguo no distingue «no» de «no marcado»: no consta (P4).
    assert _calc(activo={"es_vivienda_habitual": False}).vivienda_habitual == "no_consta"


# ─────────────────── informativo: los umbrales de aprobación ───────────────────

def _sin_procedimiento(r) -> dict:
    d = r.model_dump(mode="json")
    d.pop("procedimiento"), d.pop("informe_markdown")
    return d


@pytest.mark.parametrize("cambio", [
    {"cantidad_reclamada": 30000.0}, {"cantidad_reclamada": 200000.0},
    {"procedimiento": "judicial"},                 # el mismo que se deduce de la fuente
])
def test_los_umbrales_del_procedimiento_no_mueven_nada_mas(cambio):
    base = _sin_procedimiento(ejecutar_analisis(entrada_caso_19()))
    otro = _sin_procedimiento(ejecutar_analisis(_entrada(**cambio)))
    assert otro == base


def test_vivienda_habitual_no_mueve_nada_mas():
    base = _sin_procedimiento(ejecutar_analisis(entrada_caso_19()))
    otro = _sin_procedimiento(ejecutar_analisis(_entrada(activo={"vivienda_habitual_ejecutado": "si"})))
    assert otro == base


def test_el_resultado_lleva_el_procedimiento_y_es_determinista():
    a, b = ejecutar_analisis(entrada_caso_19()), ejecutar_analisis(entrada_caso_19())
    assert a.procedimiento is not None and a.procedimiento == b.procedimiento


def test_no_modifica_los_parametros():
    params = cargar_defaults()
    antes = params.raw()
    procedimiento.calcular(entrada_caso_19(), params)
    assert params.raw() == antes


# ─────────────────────────── contrato ───────────────────────────

def test_cantidad_reclamada_debe_ser_positiva():
    with pytest.raises(ValidationError):
        SubastaInput(valor_subasta=VT, cantidad_reclamada=0)


@pytest.mark.parametrize("campo, valor", [("procedimiento", "bancaria"), ("regimen_judicial", "quizas")])
def test_valores_no_admitidos(campo, valor):
    with pytest.raises(ValidationError):
        SubastaInput(valor_subasta=VT, **{campo: valor})


def test_vivienda_habitual_no_admite_otro_valor():
    with pytest.raises(ValidationError):
        ActivoInput(superficie_m2=80, vivienda_habitual_ejecutado="tal vez")


# ─────────────────────────── informe ───────────────────────────

@pytest.fixture(scope="module")
def informe() -> str:
    return ejecutar_analisis(entrada_caso_19()).informe_markdown


def test_el_informe_lleva_el_subapartado_al_final_del_8(informe):
    i8, isec, i9 = (informe.index("## 8 · Estrategia de puja"),
                    informe.index("**Procedimiento y umbrales legales (orientativo)**"),
                    informe.index("## 9 · Checklist"))
    assert i8 < isec < i9
    for fragmento in ("| Depósito exigido | 30.400 € (20 % del valor de subasta) |",
                      "| Capital necesario para pujar | 30.400 € |",
                      "| Pago del resto del precio | 20 días naturales |",
                      "| Inmovilización estimada del depósito | 2,5 meses (régimen judicial más "
                      "largo: no consta la fecha de inicio) |",
                      "| Puja de aprobación segura | 106.400 € (70 % del valor de subasta) |",
                      "| Suelo absoluto | 91.200 € (60 % del valor de subasta) |",
                      "- Depósito para pujar: LEC, art. 669, apdo. 1 (LO 1/2025) (confirmado)"):
        assert fragmento in informe, fragmento


def test_el_informe_lleva_el_aviso_orientativo(informe):
    assert "_Cálculo orientativo con los parámetros legales de SEIS (versión 2026.07): no es " \
           "asesoramiento jurídico." in informe
    # Fase 5J-2b: el aviso ya no dice que nada del procedimiento mueve las cifras.
    assert ("Los umbrales de aprobación no modifican la escalera de precios, el RVC ni el semáforo; "
            "el depósito exigido sí se usa en el plan de puja, y los meses de inmovilización, en el "
            "plazo de la operación._") in informe
    assert "ni la rentabilidad" not in informe


def _seccion(informe: str) -> str:
    return informe[informe.index("**Procedimiento y umbrales"):informe.index("## 9 · Checklist")]


def test_la_seccion_no_muestra_claves_internas(informe):
    # Ningún identificador con barra baja (judicial_lec_2025, no_consta…). El único «_»
    # permitido es el del énfasis del aviso, al principio y al final de su línea.
    seccion = _seccion(informe)
    assert re.findall(r"[^\W_]+_[^\W_]+", seccion) == []


def test_la_seccion_no_usa_punto_decimal_ni_porcentaje_pegado(informe):
    seccion = re.sub(r"\d{1,3}(?:\.\d{3})+ €", "", _seccion(informe)).replace("2026.07", "")
    assert re.findall(r"\d\.\d", seccion) == []
    assert re.findall(r"\d%", seccion) == []

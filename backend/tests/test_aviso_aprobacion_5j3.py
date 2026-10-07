"""Fase 5J-3 — aviso de la franja del letrado (ADR-0027).

Decisiones del responsable: herramienta de cálculo, sin implicaciones legales y sin vetos. En un
procedimiento judicial, si la puja máxima recomendada (P_max) cae por debajo de la aprobación
segura del remate:

- el informe lo declara de forma destacada, con el riesgo y los umbrales aplicados (T3), cada uno
  con su estado;
- se añade una condición a la decisión y un ítem al checklist;
- por debajo del suelo de la vivienda habitual o a decisión del letrado, techo naranja (nunca
  veto) e ítem bloqueante; sujeta a mejora (entre la mínima aprobable y la segura), sin techo e
  ítem no bloqueante;
- ningún número cambia. Vivienda habitual «no consta» ⇒ se asume que sí, con aviso.
"""
from __future__ import annotations

import pytest

from app.engine import procedimiento
from app.engine.contracts import AnalisisInput, ProcedimientoResultado
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19

POSTERIOR = {"procedimiento": "judicial", "regimen_judicial": "posterior"}
ITEM = "Riesgo de aprobación del remate asumido por escrito"


def _entrada(vivienda: str | None = None, **subasta) -> AnalisisInput:
    base = entrada_caso_19()
    activo = base.activo if vivienda is None else base.activo.model_copy(
        update={"vivienda_habitual_ejecutado": vivienda})
    return base.model_copy(update={"subasta": base.subasta.model_copy(update=subasta), "activo": activo})


def _analizar(vivienda: str | None = None, params=None, **subasta):
    return ejecutar_analisis(_entrada(vivienda, **subasta), params=params)


def _numeros(r) -> tuple:
    p, rt = r.decision.precios, r.rentabilidad
    return (p.p_ideal, p.p_objetivo, p.p_max, p.p_limite, r.decision.rvc, r.decision.ico,
            rt.tir_anual, rt.van_coste_capital, rt.roi, r.decision.margen_seguridad_valor)


def _item(r):
    return next((c for c in r.checklist if c.texto == ITEM), None)


# ─────────────────────────── franjas ───────────────────────────

@pytest.mark.parametrize("vivienda,subasta,franja,techo,semaforo", [
    (None, {}, "bajo_suelo", True, "naranja"),                       # §19: vivienda habitual supuesta
    ("si", {}, "bajo_suelo", True, "naranja"),
    ("no", {}, "discrecional", True, "naranja"),
    ("no", {"procedimiento": "judicial", "regimen_judicial": "anterior"}, "discrecional", True, "naranja"),
    ("no", {**POSTERIOR, "cantidad_reclamada": 60000.0}, "sujeta_a_mejora", False, "amarillo"),
    ("no", {**POSTERIOR, "valor_subasta": 110000.0}, "sujeta_a_mejora", False, "amarillo"),
])
def test_franja_techo_y_semaforo(vivienda, subasta, franja, techo, semaforo):
    r = _analizar(vivienda, **subasta)
    aviso = r.procedimiento.aviso_aprobacion
    assert (aviso.franja, aviso.techo_naranja, r.decision.semaforo) == (franja, techo, semaforo)
    assert aviso.condicion in r.decision.condiciones
    assert ("naranja" in r.decision.techos_aplicados) is techo
    item = _item(r)
    assert item.estado == "pendiente" and item.bloqueante is techo and item.detalle == aviso.condicion


@pytest.mark.parametrize("vivienda,subasta", [
    (None, {}), ("no", {}), ("no", {**POSTERIOR, "cantidad_reclamada": 60000.0}),
])
def test_ningun_numero_cambia(vivienda, subasta, monkeypatch):
    """Con el aviso desactivado, las mismas cifras: solo cambian semáforo, condiciones y textos."""
    r = _analizar(vivienda, **subasta)
    assert r.procedimiento.aviso_aprobacion is not None
    monkeypatch.setattr(procedimiento, "aviso_aprobacion", lambda *_a, **_k: None)
    sin = _analizar(vivienda, **subasta)
    assert sin.procedimiento.aviso_aprobacion is None
    assert _numeros(r) == _numeros(sin)
    assert r.costes == sin.costes and r.puja.p_adj_esperado == sin.puja.p_adj_esperado


def test_el_techo_nunca_sube_un_semaforo_ni_veta():
    r = _analizar(params=cargar_defaults().con_overrides({"capital.coste_capital_anual": 0.31}))
    assert r.decision.semaforo == "rojo" and r.procedimiento.aviso_aprobacion is None   # degenerada
    assert not _analizar().decision.vetos


def test_sin_aviso_fuera_del_judicial_o_con_p_max_aprobable():
    for subasta in ({"fuente": "aeat"}, {"procedimiento": "notarial"}, {"procedimiento": "no_aplica"}):
        r = _analizar(**subasta)
        assert r.procedimiento.aviso_aprobacion is None and _item(r) is None, subasta
    # Con un valor de subasta bajo, P_max supera el 70 %: aprobación segura, sin aviso.
    r = _analizar("no", **POSTERIOR, valor_subasta=80000.0)
    assert r.decision.precios.p_max >= r.procedimiento.puja_aprobacion_segura
    assert r.procedimiento.aviso_aprobacion is None


# ─────────────────────────── textos ───────────────────────────

def test_el_informe_lo_destaca_bajo_el_semaforo():
    md = _analizar().informe_markdown
    cabeza = md[:md.index("| Métrica")]
    assert cabeza.startswith("# Informe de análisis SEIS\n\n## 1 · Página de decisión\n\n# 🟠 NARANJA\n\n"
                             "**Atención: remate no aprobable si es la vivienda habitual del ejecutado.** "
                             "La puja máxima recomendada (67.941 €, 44,7 % del valor de subasta) queda por "
                             "debajo del suelo de la vivienda habitual del ejecutado (91.200 €, 60 %)")
    assert "No consta si es la vivienda habitual: se asume que sí, por prudencia" in cabeza
    assert "No consta cuándo se inició el procedimiento" in cabeza
    assert ("**Umbrales aplicados:** aprobación segura (70 %): LEC, art. 670, apdo. 1 (confirmado); "
            "aprobación sin depender de la autoridad (50 %): LEC, art. 670, apdo. 3, párrafo 4 (confirmado); "
            "vivienda habitual del ejecutado: umbral (70 %)") in cabeza
    assert "_El semáforo queda como máximo en naranja. Los precios, el RVC y la rentabilidad no cambian." in cabeza


def test_sujeta_a_mejora_no_limita_el_semaforo_y_lo_dice():
    r = _analizar("no", **POSTERIOR, cantidad_reclamada=60000.0)
    md = r.informe_markdown
    assert "**Atención: aprobación del remate sujeta a mejora.**" in md
    assert "_No limita el semáforo: es una condición. " in md
    # Con la deuda informada, el umbral de «cubre la deuda» entra en los aplicados.
    assert "aprobación si la puja cubre la deuda (40 %)" in md
    assert not any("5J-3" in x for x in r.decision.razones)


def test_a_decision_del_letrado():
    a = _analizar("no").procedimiento.aviso_aprobacion
    assert a.titulo == "Aprobación del remate a decisión del letrado"
    assert "la decide el letrado de la Administración de Justicia, oídas las partes, y puede denegarla" in a.riesgo
    assert [d.dato for d in a.datos_legales] == ["Aprobación segura", "Aprobación sin depender de la autoridad"]
    assert all(d.estado == "confirmado" for d in a.datos_legales)


def test_vivienda_habitual_conocida_no_lleva_el_aviso_de_supuesto():
    a = _analizar("si").procedimiento.aviso_aprobacion
    assert "se asume que sí" not in a.riesgo and a.vivienda_habitual_asumida is False


def test_regimen_anterior_menciona_al_ejecutante():
    r = _analizar("no", procedimiento="judicial", regimen_judicial="anterior", valor_subasta=110000.0)
    a = r.procedimiento.aviso_aprobacion
    assert a.franja == "sujeta_a_mejora"
    assert "y el ejecutante pedir la adjudicación (régimen anterior a la LO 1/2025)" in a.riesgo


# ─────────────────────── cesión de remate (LEC 647.3) ───────────────────────

@pytest.mark.parametrize("subasta,esperado", [
    ({}, "Cesión de remate solo disponible para el ejecutante y los acreedores posteriores (LEC, art. 647, "
         "apdo. 3, LO 1/2025): un postor que no sea uno de ellos no puede cederlo: la estructura compradora "
         "final debe pujar directamente; si el procedimiento se inició antes del 3-4-2025, solo el ejecutante"),
    (POSTERIOR, "Cesión de remate solo disponible para el ejecutante y los acreedores posteriores (LEC, art. "
                "647, apdo. 3, LO 1/2025): un postor que no sea uno de ellos no puede cederlo: la estructura "
                "compradora final debe pujar directamente"),
    ({"procedimiento": "judicial", "regimen_judicial": "anterior"},
     "Cesión de remate solo disponible para el ejecutante (LEC, art. 647, apdo. 3, redacción de 2015): un "
     "postor que no sea uno de ellos no puede cederlo: la estructura compradora final debe pujar directamente"),
])
def test_cesion_de_remate_por_regimen(subasta, esperado):
    assert _analizar(**subasta).puja.riesgo_ejecucion[-1] == esperado


def test_sem_ejec_01_incluye_a_los_acreedores_posteriores():
    r = _analizar()
    regla = next(x for x in r.reglas_disparadas if x.codigo == "SEM-EJEC-01")
    assert regla.version == "2026.10.07"
    assert ("cesión de remate solo por el ejecutante y, con la LO 1/2025, también por los acreedores "
            "posteriores (LEC, art. 647, apdo. 3)") in regla.efecto["condicion"]


# ─────────────────────────── compatibilidad ───────────────────────────

def test_un_resultado_anterior_sin_el_aviso_sigue_validando():
    d = _analizar().procedimiento.model_dump()
    d.pop("aviso_aprobacion")
    assert ProcedimientoResultado.model_validate(d).aviso_aprobacion is None


def test_la_funcion_es_pura_y_determinista():
    r = _analizar()
    a = procedimiento.aviso_aprobacion(r.procedimiento, r.decision.precios)
    assert a == procedimiento.aviso_aprobacion(r.procedimiento, r.decision.precios) == r.procedimiento.aviso_aprobacion

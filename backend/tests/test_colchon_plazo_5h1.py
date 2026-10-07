"""Fase 5H.1-C — colchón de plazo (§9.5, auditoría 5G.4 E5; supuestos en ADR-0019).

    colchón(P) = B_base(P) / (tenencia_mensual + intereses_mensuales(P) + cc · capital_propio(P) / 12)

con B_base(P) = VS_p − I(P, C_F^P50), capital_propio(P) = I(P, C_F^P50) − LTV · P (D5) e
intereses_mensuales(P) = LTV · P · i / 12 (0 sin hipoteca). Meses EXTRA que la operación
aguanta antes de que el beneficio base llegue a cero. Se informa a P_objetivo y a P_max.
Informativo: no entra en el ICO, el semáforo ni la escalera.
"""
from __future__ import annotations

import pytest

from app.engine import fiscal
from app.engine.contracts import CostesInput, DecisionFinal
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19
from tests.test_invariante_5h1 import con_hipoteca


@pytest.fixture(scope="module")
def dorado():
    return ejecutar_analisis(entrada_caso_19())


def _con_tenencia(mensual: float):
    e = entrada_caso_19()
    return ejecutar_analisis(e.model_copy(update={"costes": e.costes.model_copy(
        update={"tenencia_mensual": mensual})}))


def test_colchon_del_caso_dorado(dorado):
    # B_obj = 35.348,77 €; 240 + 0,015 · 141.395,67 / 12 = 416,74 €/mes ⇒ 84,8 meses.
    # A P_max (5J-2b): 61,5 meses (antes 60,9; P_max baja al sumar la inmovilización al plazo).
    assert dorado.decision.colchon_plazo_meses == 84.8
    assert dorado.decision.colchon_plazo_meses_p_max == 61.5


def _formula(r, entrada, p: float) -> float:
    """La fórmula del ADR-0019, escrita aparte del motor, con la tasa que el motor aplicó."""
    c = r.costes
    cc = r.decision.precios.detalle["coste_capital_anual"]
    hip = entrada.financiacion.tipo == "hipoteca"
    ltv = entrada.financiacion.ltv if hip else 0.0
    i = fiscal.inversion(p, c, c.c_f_p50)
    mensual = (c.tenencia_mensual + ltv * p * entrada.financiacion.interes_anual_pct / 100 / 12
               + cc * max(0.0, i - ltv * p) / 12)
    return round(max(0.0, r.vs_prudente - i) / mensual, 1)


def _base_fiscal_minima():
    """Valor de referencia por encima del precio: `fiscal.inversion` usa el otro tramo."""
    e = entrada_caso_19()
    return e.model_copy(update={"costes": e.costes.model_copy(update={"valor_referencia_catastral": 120000})})


def _rentista():
    from app.engine.contracts import RentistaInput
    return entrada_caso_19().model_copy(update={"perfil": "rentista", "rentista": RentistaInput(
        renta_mensual_estimada=950, ibi_anual=350, comunidad_mensual=60)})


@pytest.mark.parametrize("nombre,entrada", [
    ("§19", entrada_caso_19()),
    ("hipoteca", con_hipoteca(entrada_caso_19())),
    ("base fiscal mínima", _base_fiscal_minima()),
    ("rentista", _rentista()),
    ("rentista con hipoteca", con_hipoteca(_rentista())),
])
def test_la_formula_es_la_declarada_a_p_objetivo_y_a_p_max(nombre, entrada):
    r = ejecutar_analisis(entrada)
    d = r.decision
    assert not d.precios.degenerada, nombre
    assert d.colchon_plazo_meses == _formula(r, entrada, d.precios.p_objetivo), nombre
    assert d.colchon_plazo_meses_p_max == _formula(r, entrada, d.precios.p_max), nombre


def test_la_base_fiscal_minima_ejerce_el_otro_tramo_y_el_colchon_no_cambia(dorado):
    """El caso de base mínima ejerce de verdad el otro tramo de `fiscal.inversion` (P_objetivo
    distinto), pero el colchón a P_objetivo es el mismo POR CONSTRUCCIÓN: P_objetivo se despeja
    para que I(P_objetivo) = VS_p / (1 + m), así que el beneficio base y el coste mensual no
    dependen del tramo fiscal (auditoría 5G.4, H2)."""
    r = ejecutar_analisis(_base_fiscal_minima())
    assert r.costes.base_fiscal_minima > r.decision.precios.p_objetivo
    assert r.decision.precios.p_objetivo != dorado.decision.precios.p_objetivo
    assert r.decision.colchon_plazo_meses == dorado.decision.colchon_plazo_meses


def test_mas_tenencia_menos_colchon():
    colchones = [_con_tenencia(m).decision.colchon_plazo_meses for m in (100, 240, 600, 1200)]
    assert colchones == sorted(colchones, reverse=True) and len(set(colchones)) == len(colchones)


def test_mas_coste_de_capital_menos_colchon():
    colchones = [ejecutar_analisis(entrada_caso_19(), params=cargar_defaults().con_overrides(
        {"capital.coste_capital_anual": cc})).decision.colchon_plazo_meses for cc in (0.0, 0.015, 0.05)]
    assert colchones == sorted(colchones, reverse=True)
    assert colchones[0] == pytest.approx(147.3, abs=0.05)     # solo tenencia (auditoría E5)


def test_con_escalera_degenerada_no_hay_colchon():
    """Revisión de 5H.1-C: sin escalera utilizable (precios ≤ 0) no se evalúa a un precio
    ficticio; el campo queda en `None` y el informe no imprime la línea."""
    from tests.test_puja_inviable import _caso_inviable
    r = ejecutar_analisis(_caso_inviable())
    assert r.decision.precios.degenerada
    assert r.decision.colchon_plazo_meses is None and r.decision.colchon_plazo_meses_p_max is None
    assert "Colchón de plazo" not in r.informe_markdown


def test_sin_beneficio_el_colchon_es_cero(dorado):
    """A un precio que agota el beneficio base, 0 meses, nunca negativo."""
    from app.engine.modules.m11_rentabilidad import colchon_plazo
    assert colchon_plazo(dorado.vs_prudente, dorado.costes, dorado.vs_prudente,
                         entrada_caso_19(), 0.015) == 0.0


def test_sin_coste_mensual_el_colchon_no_se_puede_calcular():
    """Tenencia 0 y coste de capital 0: no hay coste que agote el beneficio ⇒ `None`, no ∞."""
    e = entrada_caso_19()
    e = e.model_copy(update={"costes": e.costes.model_copy(update={"tenencia_mensual": 0.0})})
    d = ejecutar_analisis(e, params=cargar_defaults().con_overrides({"capital.coste_capital_anual": 0.0})).decision
    assert d.colchon_plazo_meses is None


def test_con_coste_mensual_negativo_tampoco(dorado):
    """Una tenencia negativa (dato de entrada absurdo) no produce un colchón negativo ni
    infinito: `None`. Distingue `mensual <= 0` de `mensual == 0`."""
    from app.engine.modules.m11_rentabilidad import colchon_plazo
    costes = dorado.costes.model_copy(update={"tenencia_mensual": -500.0})
    assert colchon_plazo(dorado.decision.precios.p_objetivo, costes, dorado.vs_prudente,
                         entrada_caso_19(), 0.0) is None


def test_financiacion_total_el_capital_propio_no_es_negativo():
    """LTV 3,0: el capital propio satura en 0 (como en ADR-0018) y solo cuentan tenencia e
    intereses. Sin el `max(0, …)` el coste de oportunidad restaría y el colchón crecería."""
    from app.engine.contracts import FinanciacionInput
    e = entrada_caso_19().model_copy(update={"financiacion": FinanciacionInput(
        tipo="hipoteca", preaprobada=True, ltv=3.0, interes_anual_pct=3.5)})
    r = ejecutar_analisis(e)
    p = r.decision.precios.p_objetivo
    i = fiscal.inversion(p, r.costes, r.costes.c_f_p50)
    mensual = r.costes.tenencia_mensual + 3.0 * p * 0.035 / 12          # sin coste de oportunidad
    assert r.decision.colchon_plazo_meses == round(max(0.0, r.vs_prudente - i) / mensual, 1)


def test_cash_con_ltv_informado_es_como_cash(dorado):
    from app.engine.contracts import FinanciacionInput
    d = ejecutar_analisis(entrada_caso_19().model_copy(update={"financiacion": FinanciacionInput(
        tipo="cash", ltv=0.7)})).decision
    assert (d.colchon_plazo_meses, d.colchon_plazo_meses_p_max) == (84.8, 61.5)


def test_con_hipoteca_cuenta_los_intereses_y_solo_el_capital_propio():
    r = ejecutar_analisis(con_hipoteca(entrada_caso_19()))
    c, d = r.costes, r.decision
    p = d.precios.p_objetivo
    i = fiscal.inversion(p, c, c.c_f_p50)
    mensual = c.tenencia_mensual + 0.7 * p * 0.035 / 12 + 0.015 * (i - 0.7 * p) / 12
    assert d.colchon_plazo_meses == round((r.vs_prudente - i) / mensual, 1)


def test_un_resultado_antiguo_sin_el_campo_se_lee_igual(dorado):
    antiguo = dorado.decision.model_dump()
    antiguo.pop("colchon_plazo_meses")
    antiguo.pop("colchon_plazo_meses_p_max")
    d = DecisionFinal(**antiguo)
    assert d.colchon_plazo_meses is None and d.colchon_plazo_meses_p_max is None


def test_el_informe_da_el_colchon(dorado):
    seccion = dorado.informe_markdown.split("## 7 · Análisis financiero")[1].split("## 8")[0]
    assert ("Colchón de plazo: 84,8 meses a precio objetivo (61,5 a precio máximo), "
            "hasta beneficio cero por tenencia y coste de capital") in seccion


def _informe(dorado, **cambios) -> str:
    from app.engine.modules import m14_informe
    dec = dorado.decision.model_copy(update=cambios)
    parciales = {"valoracion": dorado.valoracion, "icu": dorado.icu, "reforma": dorado.reforma,
                 "costes": dorado.costes, "riesgos": dorado.riesgos, "rentabilidad": dorado.rentabilidad,
                 "puja": dorado.puja, "ici": dorado.ici, "delta_v": dorado.delta_v,
                 "vs_p": dorado.vs_prudente, "reglas": dorado.reglas_disparadas,
                 "coste_capital_anual": 0.015}
    return m14_informe.construir_informe(entrada_caso_19(), parciales, dec, dorado.checklist)


def test_sin_colchon_el_informe_no_imprime_la_linea(dorado):
    assert "Colchón de plazo" not in _informe(dorado, colchon_plazo_meses=None, colchon_plazo_meses_p_max=None)


def test_sin_colchon_a_p_max_el_informe_omite_el_parentesis(dorado):
    texto = _informe(dorado, colchon_plazo_meses_p_max=None)
    assert ("Colchón de plazo: 84,8 meses a precio objetivo, hasta beneficio cero "
            "por tenencia y coste de capital.") in texto


def test_un_valor_existente_no_cambia(dorado):
    """El colchón es nuevo: la guarda de la 5H.1 (`test_invariante_5h1.py`) vigila el resto."""
    assert dorado.decision.margen_seguridad_valor == 0.248 and dorado.decision.ico == 64


def test_la_comparacion_trae_el_colchon(api, headers):
    import json

    from tests.conftest import entrada_base
    aid = api.post("/api/v1/analisis", json=json.loads(entrada_base().model_dump_json()), headers=headers).json()["id"]
    sim = api.post(f"/api/v1/analisis/{aid}/simulaciones",
                   json={"overrides": {"capital.coste_capital_anual": 0.05}}, headers=headers).json()
    cmp = api.get(f"/api/v1/analisis/{aid}/simulaciones/{sim['id']}/comparacion", headers=headers).json()
    o, s = cmp["resultado"]["original"], cmp["resultado"]["simulacion"]
    assert o["colchon_plazo_meses"] > s["colchon_plazo_meses"] > 0

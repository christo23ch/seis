"""Fase 5H.1-B — el coste de capital del precio límite solo sobre el capital propio (D5).

ADR-0016 D5 y auditoría 5G.4, E1. Con hipoteca, la parte financiada (LTV · P_max) ya paga su
coste real como intereses dentro de `c_v` (M06); cobrarle además el coste de oportunidad la
contaba dos veces. Ahora:

    coste_capital = cc · max(0, I(P_max, C_F^P80) − LTV · P_max) · plazo_P80 / 12

Sin hipoteca, LTV no interviene y la fórmula es exactamente la de antes (la guarda
`test_invariante_5h1.py` lo comprueba sobre el §19 hoja a hoja).

Fase 5J-2b: la foto del invariante se regeneró (el plazo suma la inmovilización, ADR-0026),
así que ya no guarda el estado anterior a D5. Las cifras de antes de D5 quedan aquí como
historia y lo que se deja de cobrar se comprueba con la fórmula, no restando de la foto.
"""
from __future__ import annotations

import copy

import pytest

from app.engine import fiscal
from app.engine.contracts import FinanciacionInput, RentistaInput
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19
from tests.test_invariante_5h1 import FOTO, con_hipoteca


@pytest.fixture(scope="module")
def hipoteca():
    return ejecutar_analisis(con_hipoteca(entrada_caso_19()))


def test_con_hipoteca_el_precio_limite_sube_lo_medido_en_la_auditoria(hipoteca):
    # Historia: antes de D5, 3.659,05 € y límite 77.100 €; con D5 (auditoría E1), 2.603,76 € y
    # 78.156 € (+1.056 €). Desde la 5J-2b el plazo P80 suma la inmovilización y las cifras son:
    e = hipoteca.decision.precios
    assert e.detalle["coste_capital"] == 3124.78
    assert e.p_limite == 76499.0


def test_lo_que_se_deja_de_cobrar_es_exactamente_la_parte_financiada(hipoteca):
    e, c = hipoteca.decision.precios, hipoteca.costes
    p_max = min(e.detalle["p_por_margen_min"], e.detalle["p_por_pesimista"])
    cc, ltv, h = 0.015, 0.7, c.plazo_meses_p80 / 12
    sin_d5 = cc * fiscal.inversion(p_max, c, c.c_f_p80) * h               # lo que se cobraba antes de D5
    retirado = sin_d5 - e.detalle["coste_capital"]
    assert retirado == pytest.approx(cc * ltv * p_max * h, abs=0.01)      # 1.055,29 € en la 5H.1
    assert e.detalle["capital_propio"] == pytest.approx(
        fiscal.inversion(p_max, c, c.c_f_p80) - ltv * p_max, abs=0.01)


def test_en_cash_el_capital_propio_es_toda_la_inversion():
    r = ejecutar_analisis(entrada_caso_19())
    e, c = r.decision.precios, r.costes
    p_max = min(e.detalle["p_por_margen_min"], e.detalle["p_por_pesimista"])
    assert e.detalle["capital_propio"] == pytest.approx(fiscal.inversion(p_max, c, c.c_f_p80), abs=0.01)
    assert e.detalle["coste_capital"] == 4362.72 and e.p_limite == 78529.0    # 5J-2b (antes 3.659,05 y 80.022)


def test_el_capital_propio_nunca_es_negativo():
    """Financiación mayor que la inversión: el coste de capital es 0, nunca un abono.

    Revisión de 5H.1-B: con LTV 1,2 el capital propio NO llega a cero en el §19 (P_max baja al
    subir `c_v` y queda en 83.017 €), así que ese caso no ejercitaba el `max(0, …)`. Con LTV
    3,0 sí: sin el `max`, el coste de capital saldría negativo y subiría el límite."""
    r = ejecutar_analisis(entrada_caso_19().model_copy(update={"financiacion": FinanciacionInput(
        tipo="hipoteca", preaprobada=True, ltv=3.0, interes_anual_pct=3.5)}))
    assert r.decision.precios.detalle["capital_propio"] == 0.0
    assert r.decision.precios.detalle["coste_capital"] == 0.0


def test_cash_con_ltv_informado_no_resta_nada():
    """Solo `tipo == "hipoteca"` financia: un LTV informado en una compra al contado se ignora,
    igual que hace M06 con los intereses (revisión de 5H.1-B)."""
    e = ejecutar_analisis(entrada_caso_19().model_copy(update={"financiacion": FinanciacionInput(
        tipo="cash", ltv=0.7)})).decision.precios
    assert (e.p_limite, e.detalle["coste_capital"]) == (78529.0, 4362.72)


def test_el_rentista_con_hipoteca_tambien_paga_solo_por_su_capital():
    """D5 es general: el rentista con hipoteca también deja de pagar por la parte financiada.
    (Que el rentista reste o no coste de capital, §9.2, es E4 y queda fuera de la 5H.1.)

    El P_max del rentista no queda en `detalle` sin redondear: con el redondeado al euro, la
    base calculada aquí difiere a lo sumo en (1 + c_v + LTV) / 2 ≈ 0,9 €."""
    base = entrada_caso_19().model_copy(update={"perfil": "rentista", "rentista": RentistaInput(
        renta_mensual_estimada=950, ibi_anual=350, comunidad_mensual=60)})
    r = ejecutar_analisis(con_hipoteca(base))
    e, c = r.decision.precios, r.costes
    esperado = fiscal.inversion(e.p_max, c, c.c_f_p80) - 0.7 * e.p_max
    assert e.detalle["capital_propio"] == pytest.approx(esperado, abs=1.0)
    assert e.detalle["coste_capital"] == pytest.approx(
        0.015 * e.detalle["capital_propio"] * c.plazo_meses_p80 / 12, abs=0.01)
    assert e.detalle["coste_capital"] < ejecutar_analisis(base).decision.precios.detalle["coste_capital"]


def test_con_mas_ltv_menos_coste_de_capital():
    costes = []
    for ltv in (0.0, 0.3, 0.6, 0.8):
        e = entrada_caso_19().model_copy(update={"financiacion": FinanciacionInput(
            tipo="hipoteca", preaprobada=True, ltv=ltv, interes_anual_pct=3.5)})
        costes.append(ejecutar_analisis(e, params=cargar_defaults()).decision.precios.detalle["coste_capital"])
    assert costes == sorted(costes, reverse=True) and len(set(costes)) == len(costes)


# ─────────────── los informes ya emitidos no cambian ───────────────

def test_un_informe_emitido_antes_de_d5_conserva_su_precio_limite(api, headers):
    """Un informe oficial es un snapshot por valor y nunca se recalcula (5F.3): uno emitido
    antes de la 5H.1-B, con el límite de 77.100 €, sigue diciendo 77.100 € después."""
    import json as _json

    from app import models
    from app.core.db import SessionLocal

    entrada = con_hipoteca(entrada_caso_19())
    aid = api.post("/api/v1/analisis", json=_json.loads(entrada.model_dump_json()), headers=headers).json()["id"]
    inf = api.post(f"/api/v1/analisis/{aid}/informes", headers=headers)
    assert inf.status_code == 201, inf.text
    iid = inf.json()["id"]
    assert inf.json()["resultado"]["decision"]["precios"]["p_limite"] == 76499.0   # motor actual (5J-2b)

    # Se congela en la fila el resultado que habría emitido el motor anterior a D5.
    anterior = copy.deepcopy(FOTO["hipoteca"])
    anterior["decision"]["precios"]["p_limite"] = 77100.0
    anterior["decision"]["precios"]["detalle"]["coste_capital"] = 3659.05
    anterior["informe_markdown"] = "| **Precio límite absoluto** | 77.100 € — infranqueable |"
    db = SessionLocal()
    try:
        fila = db.get(models.Informe, iid)
        fila.resultado = anterior
        db.commit()
    finally:
        db.close()

    leido = api.get(f"/api/v1/analisis/{aid}/informes/{iid}", headers=headers).json()
    assert leido["resultado"]["decision"]["precios"]["p_limite"] == 77100.0
    assert leido["resultado"]["decision"]["precios"]["detalle"]["coste_capital"] == 3659.05
    assert "77.100 €" in leido["resultado"]["informe_markdown"]

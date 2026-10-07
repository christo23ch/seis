"""Fase 5H.1-A — VAN al coste de capital y diferencial TIR − coste de capital (ADR-0017).

Convenciones (auditoría 5G.4, E6): mismos flujos mensuales que la TIR (escenario base, a
precio objetivo); el coste de capital es una tasa EFECTIVA anual y se descuenta al mes con
`(1 + cc)^(1/12) − 1`, la misma equivalencia con la que `_tir_anual` anualiza. Por eso el
VAN vale 0 exactamente cuando cc = TIR. Son informativos: no entran en el ICO, el semáforo
ni la escalera (la guarda de `test_invariante_5h1.py` lo vigila).
"""
from __future__ import annotations

import json

import pytest

from app.engine.contracts import RentabilidadResultado
from app.engine.modules import m14_informe
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base
from tests.test_golden_caso19 import entrada_caso_19
from tests.test_invariante_5h1 import con_hipoteca

CC = "capital.coste_capital_anual"
# Fase 5J-2b (ADR-0026): antes 33.230 € y +32,37 puntos; el plazo suma la inmovilización.
LINEA_CASO19 = ("VAN al coste de capital (1,5 %): 32.721 € · "
                "TIR frente a coste de capital: +24,91 puntos")


def _con_cc(cc: float):
    return ejecutar_analisis(entrada_caso_19(), params=cargar_defaults().con_overrides({CC: cc}))


@pytest.fixture(scope="module")
def dorado():
    return ejecutar_analisis(entrada_caso_19())


# ─────────────────────────── valores ───────────────────────────

def test_van_y_diferencial_del_caso_dorado(dorado):
    r = dorado.rentabilidad
    assert r.van_coste_capital == 32721.46
    assert r.diferencial_tir_coste_capital == 24.91      # puntos porcentuales


def test_con_coste_de_capital_cero_el_van_es_el_beneficio_base():
    r = _con_cc(0.0).rentabilidad
    assert r.van_coste_capital == pytest.approx(r.beneficio, abs=0.01)
    assert r.diferencial_tir_coste_capital == pytest.approx(r.tir_anual * 100, abs=0.005)


def test_el_van_decrece_al_subir_el_coste_de_capital():
    vans = [_con_cc(cc).rentabilidad.van_coste_capital for cc in (0.0, 0.015, 0.05, 0.10, 0.15)]
    assert vans == sorted(vans, reverse=True) and len(set(vans)) == len(vans)


def test_el_diferencial_es_tir_menos_coste_de_capital():
    for cc in (0.0, 0.015, 0.06, 0.15):
        r = _con_cc(cc).rentabilidad
        assert r.diferencial_tir_coste_capital == pytest.approx((r.tir_anual - cc) * 100, abs=0.005)


def test_el_van_es_cero_cuando_el_coste_de_capital_es_la_tir(dorado):
    """Prueba de la convención: misma equivalencia mensual que `_tir_anual`."""
    tir = dorado.rentabilidad.tir_anual
    assert abs(_con_cc(tir).rentabilidad.van_coste_capital) < 0.005 * dorado.rentabilidad.beneficio


def test_con_hipoteca_se_calcula_igual(dorado):
    """M11 trabaja sobre la inversión total (auditoría H1/H2): los flujos son los mismos salvo
    el redondeo de P_objetivo al euro (57.812 frente a 60.011), que mueve el beneficio base
    unos céntimos (35.349,40 frente a 35.348,68) y el VAN en la misma medida."""
    r = ejecutar_analisis(con_hipoteca(entrada_caso_19())).rentabilidad
    assert r.van_coste_capital == pytest.approx(dorado.rentabilidad.van_coste_capital, abs=1.0)
    assert r.diferencial_tir_coste_capital == dorado.rentabilidad.diferencial_tir_coste_capital


# ─────────────────── contrato: resultados antiguos ───────────────────

def test_un_resultado_antiguo_sin_los_campos_se_lee_igual(dorado):
    antiguo = dorado.rentabilidad.model_dump()
    antiguo.pop("van_coste_capital")
    antiguo.pop("diferencial_tir_coste_capital")
    leido = RentabilidadResultado(**antiguo)
    assert leido.van_coste_capital is None and leido.diferencial_tir_coste_capital is None


# ─────────────────────────── informe ───────────────────────────

def test_el_informe_da_el_van_y_el_diferencial(dorado):
    seccion = dorado.informe_markdown.split("## 7 · Análisis financiero")[1].split("## 8")[0]
    assert LINEA_CASO19 in seccion


def test_sin_el_dato_el_informe_no_imprime_la_linea(dorado):
    rent = dorado.rentabilidad.model_copy(update={"van_coste_capital": None,
                                                  "diferencial_tir_coste_capital": None})
    parciales = {"valoracion": dorado.valoracion, "icu": dorado.icu, "reforma": dorado.reforma,
                 "costes": dorado.costes, "riesgos": dorado.riesgos, "rentabilidad": rent,
                 "puja": dorado.puja, "ici": dorado.ici, "delta_v": dorado.delta_v,
                 "vs_p": dorado.vs_prudente, "reglas": dorado.reglas_disparadas,
                 "coste_capital_anual": 0.015}
    texto = m14_informe.construir_informe(entrada_caso_19(), parciales, dorado.decision, dorado.checklist)
    assert "VAN al coste de capital" not in texto


# ─────────────────── comparación de simulaciones ───────────────────

def test_la_comparacion_trae_van_y_diferencial(api, headers):
    r = api.post("/api/v1/analisis", json=json.loads(entrada_base().model_dump_json()), headers=headers)
    aid = r.json()["id"]
    sim = api.post(f"/api/v1/analisis/{aid}/simulaciones",
                   json={"overrides": {CC: 0.05}}, headers=headers).json()
    cmp = api.get(f"/api/v1/analisis/{aid}/simulaciones/{sim['id']}/comparacion", headers=headers).json()
    original, simulada = cmp["resultado"]["original"], cmp["resultado"]["simulacion"]
    assert original["van_coste_capital"] > simulada["van_coste_capital"]
    assert simulada["diferencial_tir_coste_capital"] == pytest.approx(
        original["diferencial_tir_coste_capital"] - 3.5, abs=0.01)

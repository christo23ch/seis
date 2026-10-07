"""Fase 5J-2a — campos NUEVOS y opcionales del resultado para «Ver cálculo».

Cada campo se recalcula aquí con la fórmula del motor y debe reproducir la cifra que el
motor ya daba: así se comprueba que los operandos emitidos son los que se usaron. Ningún
valor existente cambia (`test_invariante_5h1.py`). Un resultado antiguo sin estos campos
sigue validando (todos son opcionales).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.contracts import (AnalisisInput, AnalisisResult, CostesInput, DocumentosInput,
                                  FinanciacionInput, RentistaInput)
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19

FOTO = json.loads((Path(__file__).parent / "datos" / "invariante_5h1.json").read_text(encoding="utf-8"))


def _con(e: AnalisisInput, **cambios) -> AnalisisInput:
    return e.model_copy(update=cambios)


@pytest.fixture(scope="module")
def r():
    return ejecutar_analisis(entrada_caso_19())


# ─────────────────────────── escalera ───────────────────────────

def test_p_ideal_con_su_margen_excepcional(r):
    d, c = r.decision.precios.detalle, r.costes
    p = (r.vs_prudente / (1 + d["m_excepcional_ajustado"]) - c.c_f_p50) / (1 + c.c_v)
    assert abs(p - r.decision.precios.p_ideal) < 1.5          # VS_p viaja redondeado
    assert d["m_excepcional_ajustado"] == pytest.approx(d["m_objetivo_ajustado"] * 1.35)


def test_p_pesimista_con_estres_y_piso(r):
    d, c = r.decision.precios.detalle, r.costes
    assert r.vs_prudente * (1 - d["stress_mercado"]) == pytest.approx(d["vs_pesimista"], abs=1)
    p = (d["vs_pesimista"] / (1 + d["piso_pesimista"]) - c.c_f_p80) / (1 + c.c_v)
    assert p == pytest.approx(d["p_por_pesimista"], abs=0.5)


def test_p_limite_bruto_menos_coste_de_capital(r):
    d, c = r.decision.precios.detalle, r.costes
    assert (r.vs_prudente - c.c_f_p80) / (1 + c.c_v) == pytest.approx(d["p_limite_bruto"], abs=1.5)
    assert round(d["p_limite_bruto"] - d["coste_capital"]) == r.decision.precios.p_limite


def test_tramos_fiscales_un_solo_tramo_en_el_caso_dorado(r):
    assert r.decision.precios.tramos_fiscales == {
        "p_ideal": "unico", "p_objetivo": "unico", "p_por_margen_min": "unico",
        "p_por_pesimista": "unico", "p_limite": "unico"}


def test_tramos_fiscales_con_base_imponible_minima():
    # Valor de referencia alto ⇒ base mínima por encima de los precios ⇒ tramo «bajo».
    e = entrada_caso_19()
    res = ejecutar_analisis(_con(e, costes=CostesInput(**{**e.costes.model_dump(), "valor_referencia_catastral": 150000})))
    c, t = res.costes, res.decision.precios.tramos_fiscales
    assert c.base_fiscal_minima == 150000 and c.tipo_base_minima > 0
    assert t["p_objetivo"] == "bajo"
    # Tramo bajo: c_v efectivo = c_v − t, y un fijo extra t·B.
    d = res.decision.precios.detalle
    p = (res.vs_prudente / (1 + d["m_objetivo_ajustado"]) - c.c_f_p50 - c.tipo_base_minima * c.base_fiscal_minima) \
        / (1 + c.c_v - c.tipo_base_minima)
    assert abs(p - res.decision.precios.p_objetivo) < 1.5


def test_candidatos_del_perfil_rentista():
    e = _con(entrada_caso_19(), perfil="rentista",
             rentista=RentistaInput(renta_mensual_estimada=950, ibi_anual=350, comunidad_mensual=60),
             financiacion=FinanciacionInput(tipo="hipoteca", preaprobada=True, ltv=0.7, interes_anual_pct=3.5))
    res = ejecutar_analisis(e)
    d = res.decision.precios.detalle
    cand = [d[k] for k in ("p_por_rentabilidad", "p_por_dscr", "p_por_cash_on_cash")]
    assert round(min(cand)) == res.decision.precios.p_max
    assert "p_limite_rentista" in d and res.decision.precios.tramos_fiscales is None


# ─────────────────────────── RA, P_adj, ICI y evidencias ───────────────────────────

def test_ra_con_pesos_y_suelo_de_dominancia(r):
    ra = r.riesgos
    base = sum(ra.pesos[d.dimension] * d.score / 25 * 100 for d in ra.dimensiones)
    assert base == pytest.approx(ra.ra_base, abs=0.01)
    assert ra.dominancia_aplicada == "una_alta" and ra.suelo_dominancia == 40
    assert ra.ra == round(min(100, max(ra.ra_base, ra.suelo_dominancia)))


def test_ratio_de_adjudicacion_con_sus_ajustes():
    e = entrada_caso_19()
    res = ejecutar_analisis(_con(e, subasta=e.subasta.model_copy(update={"subastas_desiertas_previas": 2})))
    p = res.puja
    assert [a.concepto for a in p.ajustes_ratio] == ["2 subasta(s) previa(s) desierta(s)"]
    ratio = max(0.10, min(1.10, p.ratio_segmento + sum(a.ajuste for a in p.ajustes_ratio)))
    assert ratio == pytest.approx(p.ratio_base, abs=1e-3)
    assert p.p_adj_esperado == pytest.approx(e.subasta.valor_subasta * p.ratio_base, abs=1)
    assert p.ratio_acotado is False


def test_ratio_acotado_se_declara():
    e = entrada_caso_19()
    res = ejecutar_analisis(_con(e, subasta=e.subasta.model_copy(update={"subastas_desiertas_previas": 6})))
    assert res.puja.ratio_acotado is True and res.puja.ratio_base == pytest.approx(0.10)


def test_penalizaciones_del_ici_estructuradas():
    e = entrada_caso_19()
    res = ejecutar_analisis(_con(e, documentos=DocumentosInput(
        **{**e.documentos.model_dump(), "inconsistencias": ["superficie_inconsistente"]})))
    det = res.ici.penalizaciones_detalle
    assert [p.codigo for p in det] == ["superficie_inconsistente"]
    assert res.ici.ici == max(0, min(100, round(sum(res.ici.desglose.values()) - sum(p.puntos for p in det))))


def test_evidencias_estructuradas(r):
    tec = next(d for d in r.riesgos.dimensiones if d.dimension == "tecnico")
    assert [(e.dato, e.valor) for e in tec.evidencias_detalle] == [("nivel_reforma", "media"), ("sin_visita_interior", None)]
    for d in r.riesgos.dimensiones:
        assert len(d.evidencias_detalle) == len(d.evidencias)


# ─────────────────────────── TIR, VAN, colchón y plazo ───────────────────────────

def test_tir_y_van_con_los_flujos_emitidos(r):
    f, rt = r.rentabilidad.flujos_base, r.rentabilidad
    assert len(f) == round(r.costes.plazo_meses_p50) + 1 and f[0] < 0 < f[-1]
    mensual = (1 + rt.tir_anual) ** (1 / 12) - 1
    assert abs(sum(x / (1 + mensual) ** t for t, x in enumerate(f))) < 50       # TIR redondeada a 4 decimales
    tasa = (1 + rt.tasa_van) ** (1 / 12) - 1
    assert sum(x / (1 + tasa) ** t for t, x in enumerate(f)) == pytest.approx(rt.van_coste_capital, abs=0.5)


def test_colchon_con_sus_operandos(r):
    c = r.decision.colchon_detalle
    assert c.coste_mensual == pytest.approx(c.tenencia_mensual + c.intereses_mensuales + c.coste_capital_mensual)
    assert round(max(0, c.beneficio) / c.coste_mensual, 1) == r.decision.colchon_plazo_meses


def test_plazo_con_su_desglose(r):
    d, c = r.costes.plazo_desglose, r.costes
    assert d["ocupacion"] + d["obra"] + d["comercializacion"] == c.plazo_meses_p50
    assert c.plazo_meses_p50 * d["multiplicador_p80"] == pytest.approx(c.plazo_meses_p80)


# ─────────────────────────── compatibilidad ───────────────────────────

@pytest.mark.parametrize("caso", ["caso19", "hipoteca"])
def test_un_resultado_anterior_sin_los_campos_nuevos_sigue_validando(caso):
    """La foto del §19 es un resultado de antes de la fase: no trae ningún campo nuevo."""
    antiguo = AnalisisResult.model_validate({**FOTO[caso], "informe_markdown": ""})
    assert antiguo.decision.precios.tramos_fiscales is None
    assert antiguo.riesgos.pesos is None and antiguo.puja.ajustes_ratio is None
    assert antiguo.rentabilidad.flujos_base is None and antiguo.decision.colchon_detalle is None


def test_no_cambia_ningun_valor_existente_del_caso_dorado():
    """Redundante con la guarda invariante, pero explícito: solo se AÑADEN hojas."""
    from tests.test_invariante_5h1 import _diferencias
    assert _diferencias(FOTO["caso19"], entrada_caso_19()) == {}


def test_los_parametros_no_se_modifican():
    p = cargar_defaults()
    antes = p.raw()
    ejecutar_analisis(entrada_caso_19(), params=p)
    assert p.raw() == antes

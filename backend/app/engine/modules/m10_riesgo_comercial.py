"""M10 — Riesgo comercial, de liquidez y de mercado (§7.5), sobre datos de M04."""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, RiesgoOut, ValoracionResultado
from app.engine.modules.m07_riesgo_juridico import _mk


def ejecutar(inp: AnalisisInput, params, hechos: dict, val: ValoracionResultado) -> list[RiesgoOut]:
    ma = inp.zona.macro
    riesgos: list[RiesgoOut] = []

    # ── comercial ────────────────────────────────────────────────────────
    p, i, cond, ev = 2, 3, [], []
    if inp.zona.precio_m2_p85 and val.vs_m2 > inp.zona.precio_m2_p85:
        p += 1
        ev.append("vs_m2_sobre_p85_zona")
        cond.append("Producto caro para su calle: revisar calidad de acabados objetivo vs. demanda local")
    if inp.activo.tipologia in ("hotel", "singular", "suelo_rustico"):
        i += 1
        ev.append("tipologia_singular")
    riesgos.append(_mk("comercial", p, i, params, condiciones=cond, evidencias=ev))

    # ── liquidez ─────────────────────────────────────────────────────────
    dom = ma.dom_venta_dias
    if val.n_comparables < 3:
        pl, il, evl = 4, 4, ["mercado_sin_profundidad(n<3)"]
    elif dom <= 45:
        pl, il, evl = 1, 2, [f"DOM={dom:.0f}d"]
    elif dom <= 90:
        pl, il, evl = 2, 2, [f"DOM={dom:.0f}d"]
    elif dom <= 180:
        pl, il, evl = 3, 3, [f"DOM={dom:.0f}d"]
    else:
        pl, il, evl = 4, 4, [f"DOM={dom:.0f}d"]
    riesgos.append(_mk("liquidez", pl, il, params, evidencias=evl))

    # ── mercado ──────────────────────────────────────────────────────────
    pm, im, evm, condm = 2, 3, [], []
    if ma.stock_meses > 12:
        pm += 1
        evm.append(f"stock={ma.stock_meses:.0f}m")
    if ma.tendencia_5a_pct < -3:
        pm += 1
        evm.append(f"tendencia={ma.tendencia_5a_pct:.1f}%/a")
        condm.append("Mercado en corrección: reforzar descuento de prudencia y acortar plazo objetivo")
    riesgos.append(_mk("mercado", pm, im, params, condiciones=condm, evidencias=evm))

    for r in riesgos:
        hechos[f"riesgo.{r.dimension}.score"] = r.score
    return riesgos

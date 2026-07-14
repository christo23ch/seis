"""M04 — Estudio de mercado y ubicación → ICU (§6.4).

Modelo compensatorio: ningún indicador negativo aislado descarta; todos ponderan.
En F1 los indicadores se cargan manualmente; en F2 los adaptadores (INE, OSM,
Interior, portales) rellenan exactamente los mismos campos (P8).
"""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, ICUResultado


def _lin(x: float, x0: float, x100: float) -> float:
    """Normalización lineal a 0–100 con saturación (x0→0, x100→100)."""
    if x100 == x0:
        return 50.0
    v = (x - x0) / (x100 - x0) * 100.0
    return max(0.0, min(100.0, v))


def ejecutar(inp: AnalisisInput, params, hechos: dict) -> ICUResultado:
    ma, mi = inp.zona.macro, inp.zona.micro
    norm = params.seccion("icu.norm")
    pm: dict = params.seccion("icu.pesos_macro")
    pmi: dict = params.seccion("icu.pesos_micro")

    macro_vals = {
        "tendencia": _lin(ma.tendencia_5a_pct, norm["tendencia"]["min"], norm["tendencia"]["max"]),
        "stock": _lin(ma.stock_meses, norm["stock_meses"]["zero"], norm["stock_meses"]["full"]),
        "dom_venta": _lin(ma.dom_venta_dias, norm["dom_venta"]["zero"], norm["dom_venta"]["full"]),
        "dom_alquiler": _lin(ma.dom_alquiler_dias, norm["dom_alquiler"]["zero"], norm["dom_alquiler"]["full"]),
        "poblacion": _lin(ma.crecimiento_pobl_5a_pct, norm["poblacion"]["min"], norm["poblacion"]["max"]),
        "renta": _lin(ma.renta_hogar, norm["renta"]["min"], norm["renta"]["max"]),
    }
    macro_score = sum(pm[k] * v for k, v in macro_vals.items()) / sum(pm.values())

    micro_vals = {
        "transporte": mi.transporte, "seguridad": mi.seguridad, "sanidad": mi.sanidad,
        "educacion": mi.educacion, "comercio": mi.comercio, "zonas_verdes": mi.zonas_verdes,
        "pipeline_urbanistico": mi.pipeline_urbanistico,
        "potencial_transformacion": mi.potencial_transformacion,
        "entorno_construido": mi.entorno_construido,
    }
    micro_score = sum(pmi[k] * v for k, v in micro_vals.items()) / sum(pmi.values())

    icu = round(params.get("icu.peso_macro") * macro_score + params.get("icu.peso_micro") * micro_score)
    potencial = round(0.5 * mi.pipeline_urbanistico + 0.5 * mi.potencial_transformacion)

    hechos.update({
        "icu": icu, "zona.stock_meses": ma.stock_meses, "zona.tendencia": ma.tendencia_5a_pct,
        "zona.dom_venta": ma.dom_venta_dias, "zona.dom_alquiler": ma.dom_alquiler_dias,
        "potencial_revalorizacion": potencial,
    })

    return ICUResultado(
        icu=icu, macro_score=round(macro_score, 2), micro_score=round(micro_score, 2),
        desglose={**{f"macro.{k}": round(v, 1) for k, v in macro_vals.items()},
                  **{f"micro.{k}": round(v, 1) for k, v in micro_vals.items()}},
        potencial_revalorizacion=potencial,
        dom_venta_dias=ma.dom_venta_dias, dom_alquiler_dias=ma.dom_alquiler_dias,
        tendencia_5a_pct=ma.tendencia_5a_pct, y_zona_pct=ma.y_zona_pct,
    )

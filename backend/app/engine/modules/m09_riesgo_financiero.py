"""M09 — Riesgo financiero (§7.4): estructura, DSCR estresado, plazos de la fuente."""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, RiesgoOut
from app.engine.modules.m07_riesgo_juridico import _mk


def ejecutar(inp: AnalisisInput, params, hechos: dict) -> tuple[list[RiesgoOut], float | None]:
    f = inp.financiacion
    dscr: float | None = None
    cond, ev = [], [f"estructura={f.tipo}"]

    if f.tipo == "cash":
        p, i, mit = 1, 2, True
    elif f.preaprobada:
        p, i, mit = 2, 3, True
        cond.append("Confirmar que la preaprobación no contiene condición suspensiva incompatible con el plazo de pago del remate")
    else:
        p, i, mit = 4, 5, False          # pérdida probable del depósito → veto FIN-01
        ev.append("financiacion_sin_preaprobar")

    perfil_tipo = params.get(f"perfiles.{inp.perfil}.tipo", "venta")
    if perfil_tipo == "rentista" and f.tipo == "hipoteca" and inp.rentista:
        r = inp.rentista
        rna = (r.renta_mensual_estimada * 12 * (1 - r.vacancia_pct / 100)
               - r.ibi_anual - r.comunidad_mensual * 12 - r.seguro_anual
               - (r.mantenimiento_pct_renta + r.gestion_pct_renta) / 100 * r.renta_mensual_estimada * 12)
        tipo_stress = (f.interes_anual_pct + float(params.get("financiacion.stress_tipos_pp"))) / 100
        servicio = f.ltv * inp.subasta.valor_subasta * tipo_stress      # aprox. sobre VT (F1)
        dscr = round(rna / servicio, 3) if servicio > 0 else None
        if dscr is not None and dscr < float(params.get("financiacion.dscr_minimo")):
            p, i = max(p, 3), max(i, 4)
            ev.append(f"DSCR_estresado={dscr}")
            cond.append("DSCR < 1,2 con tipos +200 pb: reducir LTV o descartar apalancamiento")

    hechos["financiacion.dscr"] = dscr
    riesgo = _mk("financiero", p, i, params, mitigable=mit, condiciones=cond, evidencias=ev)
    hechos["riesgo.financiero.score"] = riesgo.score
    return [riesgo], dscr

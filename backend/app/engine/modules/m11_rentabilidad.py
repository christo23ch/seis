"""M11 — Rentabilidad y escenarios (§7.7).

Construye las funciones financieras I(P), B(P) y las evalúa en tres escenarios
deterministas. TIR mensual por bisección sobre el calendario real de flujos
(determinista, sin optimizadores externos).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.engine.contracts import (AnalisisInput, CostesResultado, EscenarioOut,
                                  RentabilidadResultado, ValoracionResultado)


@dataclass(frozen=True)
class ParametrosEscenario:
    nombre: str
    probabilidad: float
    vs: float
    c_f: float
    plazo_meses: float
    contingencia_incluida: float          # para el calendario de flujos


def inversion(p: float, c_v: float, c_f: float) -> float:
    return p * (1 + c_v) + c_f


def _roi_anualizado(roi: float, plazo_meses: float) -> float:
    if plazo_meses <= 0:
        return roi
    base = 1 + roi
    if base <= 0:
        return -1.0
    return base ** (12.0 / plazo_meses) - 1


def _flujos_detallados(p: float, esc: ParametrosEscenario, costes: CostesResultado,
                       d: dict, n: int) -> list[float]:
    flujos = [0.0] * (n + 1)
    flujos[0] -= p * (1 + costes.c_v) + d["adquisicion_fija"] + d["atrasos_comunidad_ibi"] \
        + esc.contingencia_incluida + d["cargas_subsistentes"] + d["plusvalia_municipal"]

    # tenencia del escenario = C_F del escenario − resto de partidas ⇒ suma exacta = B(P)
    tenencia_total = esc.c_f - sum(v for k, v in d.items() if k != "tenencia") \
        - (esc.contingencia_incluida - d.get("contingencia", 0.0))
    tenencia_mensual = max(0.0, tenencia_total / n)

    meses_ocu = min(n, max(0, round(n * 0.45)))            # tramo posesorio aproximado
    meses_obra = min(n - meses_ocu, max(0, round(n * 0.3)))
    mes_pago_ocu = max(1, meses_ocu)
    obra = d["reforma"]
    for m in range(1, n + 1):
        flujos[m] -= tenencia_mensual
        if m == mes_pago_ocu and d["ocupacion_desalojo"]:
            flujos[m] -= d["ocupacion_desalojo"]
        if meses_ocu < m <= meses_ocu + meses_obra and meses_obra > 0:
            flujos[m] -= obra / meses_obra
        elif meses_obra == 0 and m == 1:
            flujos[m] -= obra
    flujos[n] += esc.vs - d["comercializacion"]
    return flujos


def _tir_anual(flujos: list[float]) -> float:
    """TIR mensual por bisección; devuelve tasa anual equivalente."""
    def npv(r: float) -> float:
        return sum(f / (1 + r) ** t for t, f in enumerate(flujos))

    lo, hi = -0.95, 3.0
    if npv(lo) < 0:                      # pérdida incluso a tasa mínima
        return -1.0
    if npv(hi) > 0:
        return (1 + hi) ** 12 - 1
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    r_mensual = (lo + hi) / 2
    return (1 + r_mensual) ** 12 - 1


def construir_escenarios(inp: AnalisisInput, params, hechos: dict, val: ValoracionResultado,
                         costes: CostesResultado, vs_p: float, banda_ra: str,
                         potencial: int, ici: int) -> list[ParametrosEscenario]:
    stress = float(params.get(f"primas_ra.{banda_ra}.stress_mercado"))
    plazo_mult = params.seccion("escenarios.plazo_mult")
    prob = params.seccion("escenarios.prob") if ici >= int(params.get("escenarios.ici_umbral_prob")) \
        else params.seccion("escenarios.prob_ici_bajo")
    conting = costes.desglose_p50["contingencia"]

    vs_opt = min(val.vs * float(params.get("escenarios.vs_opt_cap")),
                 vs_p * (1 + potencial / float(params.get("escenarios.potencial_divisor"))))
    reforma_ahorro = costes.desglose_p50["reforma"] * (1 - float(params.get("escenarios.reforma_opt_mult")))

    return [
        ParametrosEscenario("pesimista", float(prob["pesimista"]), vs_p * (1 - stress),
                            costes.c_f_p80, costes.plazo_meses_p50 * float(plazo_mult["pesimista"]),
                            contingencia_incluida=0.0),
        ParametrosEscenario("base", float(prob["base"]), vs_p,
                            costes.c_f_p50, costes.plazo_meses_p50 * float(plazo_mult["base"]),
                            contingencia_incluida=conting),
        ParametrosEscenario("optimista", float(prob["optimista"]), vs_opt,
                            costes.c_f_p50 - conting - reforma_ahorro,
                            costes.plazo_meses_p50 * float(plazo_mult["optimista"]),
                            contingencia_incluida=0.0),
    ]


def evaluar(p: float, escenarios: list[ParametrosEscenario], costes: CostesResultado,
            inp: AnalisisInput, params) -> RentabilidadResultado:
    outs: list[EscenarioOut] = []
    for e in escenarios:
        i_total = inversion(p, costes.c_v, e.c_f)
        b = e.vs - i_total
        roi = b / i_total if i_total > 0 else 0.0
        outs.append(EscenarioOut(nombre=e.nombre, probabilidad=e.probabilidad, vs=round(e.vs, 2),
                                 coste_total=round(i_total, 2), beneficio=round(b, 2),
                                 roi=round(roi, 4), roi_anualizado=round(_roi_anualizado(roi, e.plazo_meses), 4),
                                 plazo_meses=round(e.plazo_meses, 1)))

    base = next(o for o in outs if o.nombre == "base")
    esc_base = next(e for e in escenarios if e.nombre == "base")
    d = costes.desglose_p50
    n = max(1, round(esc_base.plazo_meses))
    flujos = _flujos_detallados(p, esc_base, costes, d, n)
    tir = _tir_anual(flujos)
    ve = sum(o.probabilidad * o.beneficio for o in outs)

    # Métricas rentista (si aplica)
    y_neta = dscr = coc = None
    if params.get(f"perfiles.{inp.perfil}.tipo", "venta") == "rentista" and inp.rentista:
        r = inp.rentista
        rna = (r.renta_mensual_estimada * 12 * (1 - r.vacancia_pct / 100)
               - r.ibi_anual - r.comunidad_mensual * 12 - r.seguro_anual
               - (r.mantenimiento_pct_renta + r.gestion_pct_renta) / 100 * r.renta_mensual_estimada * 12)
        y_neta = round(rna / base.coste_total, 4) if base.coste_total > 0 else None
        f = inp.financiacion
        if f.tipo == "hipoteca" and f.ltv > 0:
            servicio = f.ltv * p * (f.interes_anual_pct + float(params.get("financiacion.stress_tipos_pp"))) / 100
            dscr = round(rna / servicio, 3) if servicio > 0 else None
            equity = base.coste_total - f.ltv * p
            coc = round((rna - f.ltv * p * f.interes_anual_pct / 100) / equity, 4) if equity > 0 else None

    return RentabilidadResultado(
        precio_evaluado=round(p, 2), inversion_total=base.coste_total, beneficio=base.beneficio,
        roi=base.roi, roi_anualizado=base.roi_anualizado, tir_anual=round(tir, 4),
        valor_esperado=round(ve, 2), escenarios=outs, y_neta=y_neta, dscr=dscr, cash_on_cash=coc,
    )

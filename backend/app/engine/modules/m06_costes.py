"""M06 — Cálculo de costes (§6.6). Consolida C_F (fijos) y c_v (proporcionales a P).

Nota de orden del DAG: la contingencia depende de la banda de RA y del ICI (§9.4),
por lo que el pipeline ejecuta los módulos de riesgo antes de cerrar M06
(resolución de la dependencia documentada en §6.6/§9.4 de la especificación).
"""
from __future__ import annotations

import math

from app.engine.contracts import AnalisisInput, CostesResultado, ICIResultado, ReformaResultado, ValoracionResultado


def _arbol_fiscal(inp: AnalisisInput, params) -> tuple[str, float, dict]:
    """Árbol §8.7.3 → (régimen, tipo total sobre P, desglose)."""
    c = inp.costes
    if c.regimen_fiscal == "itp" or (c.regimen_fiscal == "auto" and not c.transmitente_empresario):
        tipo = c.itp_tipo_override if c.itp_tipo_override is not None \
            else float(params.get(f"fiscal.itp_por_ccaa.{inp.activo.ccaa}",
                                  params.get("fiscal.itp_por_ccaa.madrid")))
        return "itp", tipo, {"itp": tipo}
    # sujeta a IVA: primera entrega, o renuncia a exención con inversión del sujeto pasivo
    if c.regimen_fiscal == "iva" or c.primera_entrega or c.comprador_deduce_iva:
        iva = float(params.get("fiscal.iva_vivienda")) if inp.activo.tipologia == "vivienda" \
            else float(params.get("fiscal.iva_general"))
        ajd = float(params.get("fiscal.ajd_defecto"))
        return "iva", iva + ajd, {"iva": iva, "ajd": ajd}
    tipo = c.itp_tipo_override if c.itp_tipo_override is not None \
        else float(params.get(f"fiscal.itp_por_ccaa.{inp.activo.ccaa}", 0.08))
    return "itp", tipo, {"itp": tipo}


def ejecutar(inp: AnalisisInput, params, hechos: dict, reforma: ReformaResultado,
             valoracion: ValoracionResultado, ici: ICIResultado, banda_ra: str) -> CostesResultado:
    vt = inp.subasta.valor_subasta
    vs = valoracion.vs

    # ── c_v: componentes proporcionales a P ─────────────────────────────
    regimen, tipo_imp, desglose_fiscal = _arbol_fiscal(inp, params)
    c_v_d: dict[str, float] = {**desglose_fiscal,
                               "aranceles_variables": float(params.get("aranceles.variable_pct"))}
    fin = inp.financiacion
    plazo_obra = reforma.plazo_obra_meses

    # ── ocupación (tabla §7.2) ──────────────────────────────────────────
    tabla_ocu = params.seccion("ocupacion")
    estado = inp.ocupacion.estado
    fila = tabla_ocu[estado] if estado in tabla_ocu and "usa" not in tabla_ocu.get(estado, {}) \
        else tabla_ocu[tabla_ocu["desconocida"]["usa"]]
    ocu_p50, ocu_p80 = float(fila["coste_p50"]), float(fila["coste_p80"])
    meses_ocu_p50, meses_ocu_p80 = float(fila["meses_p50"]), float(fila["meses_p80"])

    # ── atrasos comunidad/IBI (estimación al alza si no hay certificado, P5) ──
    if inp.costes.atrasos_comunidad_ibi is not None:
        atrasos_p50 = inp.costes.atrasos_comunidad_ibi
    else:
        atrasos_p50 = max(float(params.get("atrasos.minimo")),
                          float(params.get("atrasos.defecto_pct_vt")) * vt)
    atrasos_p80 = atrasos_p50 * float(params.get("atrasos.stress_p80"))

    # ── plazos totales ──────────────────────────────────────────────────
    meses_com = max(int(params.get("precios.meses_comercializacion_min")),
                    math.ceil(inp.zona.macro.dom_venta_dias / 30.0))
    plazo_p50 = meses_ocu_p50 + plazo_obra + meses_com
    plazo_p80 = plazo_p50 * float(params.get("escenarios.plazo_mult.pesimista"))

    # financiación: interés proporcional a P (interés simple sobre LTV·P durante el plazo)
    if fin.tipo == "hipoteca":
        c_v_d["financiacion_apertura"] = float(params.get("financiacion.apertura_pct")) * fin.ltv
        c_v_d["financiacion_intereses"] = fin.ltv * (fin.interes_anual_pct / 100.0) * (plazo_p50 / 12.0)
    c_v = sum(c_v_d.values())

    # ── C_F: fijos ──────────────────────────────────────────────────────
    adquisicion = inp.costes.adquisicion_fija_override if inp.costes.adquisicion_fija_override is not None \
        else float(params.get("aranceles.adquisicion_fija")) + float(params.get("aranceles.procurador"))
    if fin.tipo == "hipoteca":
        adquisicion += float(params.get("financiacion.tasacion_banco"))

    tenencia_mensual = inp.costes.tenencia_mensual if inp.costes.tenencia_mensual is not None \
        else float(params.get("tenencia.mensual_defecto"))
    tenencia_p50 = tenencia_mensual * plazo_p50
    tenencia_p80 = tenencia_mensual * plazo_p80

    comercializacion = float(params.get("comercializacion.agencia_pct_vs")) * vs \
        + float(params.get("comercializacion.marketing_fijo"))

    cargas_subsistentes = float(hechos.get("carga_subsistente_total", 0.0))
    plusvalia = inp.costes.plusvalia_municipal_estimada

    # ── contingencia (§9.4 + efecto ICI §6.2) sobre reforma+posesión ────
    conting_pct = float(params.get(f"primas_ra.{banda_ra}.conting_pct")) \
        + ici.efecto_contingencia_pp / 100.0
    base_conting = reforma.total_p50 + ocu_p50 + atrasos_p50
    contingencia = conting_pct * base_conting

    d50 = {"reforma": reforma.total_p50, "ocupacion_desalojo": ocu_p50, "atrasos_comunidad_ibi": round(atrasos_p50, 2),
           "adquisicion_fija": adquisicion, "tenencia": round(tenencia_p50, 2),
           "comercializacion": round(comercializacion, 2), "contingencia": round(contingencia, 2),
           "cargas_subsistentes": cargas_subsistentes, "plusvalia_municipal": plusvalia}
    d80 = {"reforma": reforma.total_p80, "ocupacion_desalojo": ocu_p80, "atrasos_comunidad_ibi": round(atrasos_p80, 2),
           "adquisicion_fija": adquisicion, "tenencia": round(tenencia_p80, 2),
           "comercializacion": round(comercializacion, 2), "contingencia": 0.0,   # consumida en estrés (§7.7)
           "cargas_subsistentes": cargas_subsistentes, "plusvalia_municipal": plusvalia}

    res = CostesResultado(
        c_v=round(c_v, 5), c_v_desglose={k: round(v, 5) for k, v in c_v_d.items()},
        c_f_p50=round(sum(d50.values()), 2), c_f_p80=round(sum(d80.values()), 2),
        desglose_p50=d50, desglose_p80=d80, contingencia_pct=round(conting_pct, 4),
        tenencia_mensual=tenencia_mensual, plazo_meses_p50=plazo_p50, plazo_meses_p80=round(plazo_p80, 1),
        regimen_fiscal=regimen, tipo_impositivo=tipo_imp,
    )
    hechos.update({"c_v": res.c_v, "c_f_p50": res.c_f_p50, "c_f_p80": res.c_f_p80,
                   "plazo_p50": plazo_p50, "plazo_p80": res.plazo_meses_p80})
    return res

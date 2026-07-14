"""Pipeline SEIS — DAG determinista M01→M14 sobre la pizarra de hechos (T1, §4.6).

Orden de ejecución (resolución de dependencias documentada en §6.6/§9.4):
M01 → M02(ICI) → M03(valoración) → M04(ICU) → M05(reforma) → M07–M10(riesgos)
→ RA → M06(costes, contingencia=f(RA,ICI)) → escalera §9 → M11(escenarios a P_obj)
→ M13(P_adj, RVC) → reglas T2 (vetos+techos) → ICO → semáforo → M14(informe+checklist).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.engine.contracts import (AnalisisInput, AnalisisResult, DecisionFinal,
                                  ReglaDisparadaOut)
from app.engine.modules import (m01_captura, m02_validacion, m03_valoracion,
                                m04_mercado, m05_reforma, m06_costes,
                                m07_riesgo_juridico, m08_riesgo_urbanistico,
                                m09_riesgo_financiero, m10_riesgo_comercial,
                                m11_rentabilidad, m12_decision, m13_puja,
                                m14_informe)
from app.engine.params.store import Parametros, cargar_defaults
from app.engine.rules.engine import RuleEngine

_CATALOGO_PATH = Path(__file__).parent / "rules" / "catalogo.yaml"


def cargar_catalogo() -> tuple[list[dict], str]:
    with open(_CATALOGO_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["reglas"], str(data["version"])


def ejecutar_analisis(inp: AnalisisInput, params: Parametros | None = None,
                      reglas: list[dict] | None = None,
                      version_reglas: str | None = None) -> AnalisisResult:
    params = params or cargar_defaults()
    if reglas is None:
        reglas, version_reglas = cargar_catalogo()
    version_reglas = version_reglas or "dev"

    hechos: dict = {"perfil.tipo": params.get(f"perfiles.{inp.perfil}.tipo"),
                    "perfil.rvc_veto": float(params.get(f"perfiles.{inp.perfil}.rvc_veto"))}

    # ── Capa de datos ────────────────────────────────────────────────────
    m01_captura.ejecutar(inp, params, hechos)
    valoracion = m03_valoracion.ejecutar(inp, params, hechos)        # CV disponible para ICI
    ici = m02_validacion.ejecutar(inp, params, hechos)
    icu = m04_mercado.ejecutar(inp, params, hechos)
    reforma = m05_reforma.ejecutar(inp, params, hechos)

    # ── Riesgos (9 dimensiones) y RA ─────────────────────────────────────
    riesgos = []
    riesgos += m07_riesgo_juridico.ejecutar(inp, params, hechos, ici, valoracion.vs)
    riesgos += m08_riesgo_urbanistico.ejecutar(inp, params, hechos, reforma)
    r_fin, _ = m09_riesgo_financiero.ejecutar(inp, params, hechos)
    riesgos += r_fin
    riesgos += m10_riesgo_comercial.ejecutar(inp, params, hechos, valoracion)
    ra_res = m12_decision.agregar_ra(riesgos, params)
    hechos["ra"] = ra_res.ra

    # ── Costes (contingencia = f(banda RA, ICI)) ─────────────────────────
    costes = m06_costes.ejecutar(inp, params, hechos, reforma, valoracion, ici, ra_res.banda)

    # ── VS prudente y escalera de precios (§9) ───────────────────────────
    delta_v = m12_decision.calcular_delta_v(params, ra_res.banda, valoracion.dispersion_cv, ici)
    vs_p = valoracion.vs * (1 - delta_v)
    hechos["vs_prudente"] = vs_p

    rna = None
    if params.get(f"perfiles.{inp.perfil}.tipo") == "rentista" and inp.rentista:
        r = inp.rentista
        rna = (r.renta_mensual_estimada * 12 * (1 - r.vacancia_pct / 100)
               - r.ibi_anual - r.comunidad_mensual * 12 - r.seguro_anual
               - (r.mantenimiento_pct_renta + r.gestion_pct_renta) / 100 * r.renta_mensual_estimada * 12)

    escalera = m12_decision.calcular_escalera(inp, params, ra_res.banda, vs_p, costes,
                                              rna, icu.y_zona_pct, ici.ici)

    # VPO: viabilidad frente a precio máximo legal (alimenta VETO-VPO-01)
    if inp.activo.vpo and inp.activo.vpo_precio_max_legal:
        i_min = escalera.p_objetivo * (1 + costes.c_v) + costes.c_f_p50
        hechos["vpo_inviable"] = inp.activo.vpo_precio_max_legal < i_min

    # ── Escenarios y rentabilidad al precio objetivo ─────────────────────
    escenarios = m11_rentabilidad.construir_escenarios(inp, params, hechos, valoracion, costes,
                                                       vs_p, ra_res.banda,
                                                       icu.potencial_revalorizacion, ici.ici)
    p_eval = max(escalera.p_objetivo, 1.0)
    rentabilidad = m11_rentabilidad.evaluar(p_eval, escenarios, costes, inp, params)

    # ── Estrategia de puja y viabilidad competitiva ──────────────────────
    puja = m13_puja.ejecutar(inp, params, hechos, escalera, valoracion.vm)

    # ── Reglas T2: vetos, techos y condiciones (una sola pasada, determinista) ──
    motor = RuleEngine(reglas)
    disparos = motor.evaluar(hechos)
    vetos, techos, condiciones = m12_decision.procesar_disparos(disparos)
    condiciones += sorted({c for r in riesgos if r.nivel in ("alto", "critico") for c in r.condiciones})

    # ── ICO y semáforo ───────────────────────────────────────────────────
    ms_valor = m12_decision.margen_seguridad(p_eval, costes.c_v, costes.c_f_p50, valoracion.vs)
    ico, ico_desglose = m12_decision.calcular_ico(inp, params, ra_res, rentabilidad, icu,
                                                  ici.ici, escalera, costes.plazo_meses_p50)
    semaforo, razones = m12_decision.decidir_semaforo(
        params, ico, ra_res, rentabilidad, ms_valor, puja.rvc, ici.ici,
        ici.techo_semaforo, escalera, vetos, techos, inp)

    decision = DecisionFinal(
        semaforo=semaforo, ico=ico, ico_desglose=ico_desglose, ra=ra_res.ra, ici=ici.ici,
        icu=icu.icu, precios=escalera, margen_seguridad_valor=round(ms_valor, 4),
        rvc=puja.rvc, p_adj_esperado=puja.p_adj_esperado, vetos=vetos,
        condiciones=sorted(set(condiciones)), techos_aplicados=sorted(set(techos)),
        razones=razones, version_reglas=version_reglas, version_parametros=params.version,
    )

    reglas_out = [ReglaDisparadaOut(codigo=d.codigo, version=d.version, categoria=d.categoria,
                                    efecto=d.efecto, evidencias=d.evidencias) for d in disparos]

    parciales = {"valoracion": valoracion, "icu": icu, "reforma": reforma, "costes": costes,
                 "riesgos": ra_res, "rentabilidad": rentabilidad, "puja": puja, "ici": ici,
                 "delta_v": delta_v, "vs_p": vs_p, "reglas": reglas_out}
    checklist = m14_informe.construir_checklist(inp, decision, hechos)
    informe = m14_informe.construir_informe(inp, parciales, decision, checklist)

    return AnalisisResult(
        decision=decision, ici=ici, valoracion=valoracion, icu=icu, reforma=reforma,
        costes=costes, riesgos=ra_res, rentabilidad=rentabilidad, puja=puja,
        checklist=checklist, reglas_disparadas=reglas_out, informe_markdown=informe,
        delta_v=round(delta_v, 4), vs_prudente=round(vs_p, 2),
    )

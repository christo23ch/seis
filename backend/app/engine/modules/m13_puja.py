"""M13 — Estrategia de puja y viabilidad competitiva (§11)."""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, EscaleraPrecios, PujaResultado


def _ratio_segmento(inp: AnalisisInput, params) -> float:
    ratios = params.seccion("adjudicacion.ratios")
    fuente = ratios.get(inp.subasta.fuente, ratios["default"])
    tip = fuente.get(inp.activo.tipologia)
    if isinstance(tip, dict):
        estado = inp.ocupacion.estado
        if estado == "vacio":
            clave = "vacio"
        elif estado == "desconocida":
            clave = "desconocida"
        else:
            clave = "ocupado"
        return float(tip.get(clave, fuente.get("default", 0.55)))
    return float(fuente.get("default", 0.55))


def ejecutar(inp: AnalisisInput, params, hechos: dict, escalera: EscaleraPrecios,
             vm: float) -> PujaResultado:
    vt = inp.subasta.valor_subasta
    ratio = _ratio_segmento(inp, params)

    # Capa B (§11.1): ajustes por historial y descuento aparente
    ratio += float(params.get("adjudicacion.ajuste_desierta_pp")) * inp.subasta.subastas_desiertas_previas
    if vm > 0 and vt / vm < 0.6:
        ratio += float(params.get("adjudicacion.ajuste_chollo_pp"))
    ratio = max(0.10, min(1.10, ratio))

    p_adj = vt * ratio
    rvc = escalera.p_max / p_adj if p_adj > 0 else 0.0
    banda = next(b["banda"] for b in params.get("adjudicacion.rvc_bandas") if rvc >= b["min"])

    deposito = inp.subasta.deposito_pct * vt
    plan = [
        f"Cargar límites en la interfaz antes de abrir la puja: objetivo {escalera.p_objetivo:,.0f} € · "
        f"máximo {escalera.p_max:,.0f} € · límite absoluto {escalera.p_limite:,.0f} € (infranqueable por software)",
        "Pujar siempre el tramo mínimo; sin pujas psicológicas redondas",
        "Entrar tarde con límites precargados: la extensión automática del cierre neutraliza el sniping; la ventaja es la disciplina",
        f"Depósito requerido: {deposito:,.0f} € ({inp.subasta.deposito_pct:.0%} del valor de subasta)",
        "Si aparece información nueva durante la subasta, re-análisis exprés; si el semáforo cae, retirada",
    ]
    if banda == "ajustado":
        plan.append("RVC 0,90–1,05: operación de oportunidad, no de plan — aceptar por escrito antes de pujar")
    if banda == "improbable":
        plan.append("RVC 0,80–0,90: pujar solo P_ideal 'por si acaso', asumiendo el coste del depósito")

    riesgo_ejecucion = [
        "Suspensión/sobreseimiento del procedimiento: capital del depósito inmovilizado sin operación",
        "Pago del remate en plazo legal sin condición suspensiva de financiación (incumplir ⇒ pérdida del depósito)",
        "Cargas descubiertas entre puja y pago: mitigación con nota simple ≤ 5 días antes del cierre",
    ]
    if inp.subasta.fuente == "judicial_boe":
        riesgo_ejecucion.append("Cesión de remate solo disponible para el ejecutante: la estructura compradora final debe pujar directamente")

    hechos.update({"rvc": round(rvc, 3), "p_adj_esperado": round(p_adj, 2), "p_max": escalera.p_max})
    return PujaResultado(p_adj_esperado=round(p_adj, 2), ratio_base=round(ratio, 3),
                         rvc=round(rvc, 3), banda_rvc=banda, plan=plan,
                         riesgo_ejecucion=riesgo_ejecucion)

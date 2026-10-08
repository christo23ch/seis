"""M13 — Estrategia de puja y viabilidad competitiva (§11)."""
from __future__ import annotations

from app.engine.contracts import (AjusteRatio, AnalisisInput, EscaleraPrecios, ProcedimientoResultado,
                                  PujaResultado)
from app.engine.procedimiento import texto_deposito
from app.engine.formato import eur, pct


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


def _tacticas(escalera: EscaleraPrecios, forma: str | None, regimen_asumido: bool = False) -> list[str]:
    """Fase 5J-2b (ADR-0025): táctica según cómo se puja en el régimen del procedimiento
    (LEC 648.6.ª y 649.1; RGR 104; RGRSS 117-120; Ley del Notariado 75)."""
    limites = (f"objetivo {eur(escalera.p_objetivo)} · máximo {eur(escalera.p_max)} · "
               f"límite absoluto {eur(escalera.p_limite)} (infranqueable por software)")
    if forma == "secretas_sin_prorroga":
        secretas = ("Pujas secretas y cierre improrrogable (LO 1/2025): no se ven las pujas ajenas ni hay "
                    "prórroga, así que no cabe reaccionar al final ni subir por tramos; se puja directamente la "
                    "cifra decidida")
        if regimen_asumido:
            secretas += ("; si el procedimiento se inició antes del 3-4-2025, las pujas se ven y el cierre se "
                         "prorroga, y esta táctica sigue siendo válida")
        return [
            f"Decidir la cifra antes de abrir la puja, entre {limites}",
            secretas,
            "No apurar el cierre: sin prórroga, una puja que no llegue a tiempo por un fallo técnico queda fuera",
        ]
    if forma == "visibles_con_prorroga":
        return [
            f"Cargar límites en la interfaz antes de abrir la puja: {limites}",
            "Pujar siempre el tramo mínimo; sin pujas psicológicas redondas",
            "Entrar tarde con límites precargados: la extensión automática del cierre neutraliza el sniping; "
            "la ventaja es la disciplina",
        ]
    if forma == "visibles":
        return [
            f"Cargar límites en la interfaz antes de abrir la puja: {limites}",
            "Pujar siempre el tramo mínimo; sin pujas psicológicas redondas",
            "Las pujas se ven, pero la norma no fija si el cierre se prorroga: confirmarlo en el anuncio y no "
            "dejar la puja para el último minuto",
        ]
    if forma == "presencial":
        return [
            f"Llevar decididas la cifra del sobre cerrado y el límite de la puja a viva voz: {limites}",
            "Subasta presencial: sobre cerrado antes del acto y pujas a viva voz en él, con tramos de al menos el "
            "2 % del tipo; confirmar en el anuncio el lugar, la hora y si se celebra ya en el Portal del BOE",
        ]
    return [
        f"Cargar límites antes de pujar: {limites}",
        "No consta cómo se puja en este procedimiento: confirmar en el edicto o en las condiciones de venta si "
        "las pujas son visibles y si el cierre se prorroga antes de decidir la táctica",
    ]


def _cesion_remate(procedimiento: ProcedimientoResultado | None) -> str:
    """Fase 5J-3: con la LO 1/2025 ceden el remate el ejecutante y los acreedores posteriores
    (LEC 647.3); antes, solo el ejecutante."""
    final = "un postor que no sea uno de ellos no puede cederlo: la estructura compradora final debe pujar directamente"
    if procedimiento is not None and procedimiento.regimen == "judicial_lec_2015":
        return ("Cesión de remate solo disponible para el ejecutante (LEC, art. 647, apdo. 3, redacción de 2015): "
                "cualquier otro postor no puede cederlo: la estructura compradora final debe pujar directamente")
    texto = ("Cesión de remate solo disponible para el ejecutante y los acreedores posteriores "
             f"(LEC, art. 647, apdo. 3, LO 1/2025): {final}")
    if procedimiento is not None and procedimiento.regimen_asumido:
        texto += "; si el procedimiento se inició antes del 3-4-2025, solo el ejecutante"
    return texto


def ejecutar(inp: AnalisisInput, params, hechos: dict, escalera: EscaleraPrecios,
             vm: float, procedimiento: ProcedimientoResultado | None = None,
             veredicto=None) -> PujaResultado:
    vt = inp.subasta.valor_subasta
    ratio = _ratio_segmento(inp, params)
    ratio_segmento = ratio
    ajustes: list[AjusteRatio] = []                     # Fase 5J-2a (informativo)

    # Capa B (§11.1): ajustes por historial y descuento aparente
    desiertas = float(params.get("adjudicacion.ajuste_desierta_pp")) * inp.subasta.subastas_desiertas_previas
    ratio += desiertas
    if inp.subasta.subastas_desiertas_previas:
        ajustes.append(AjusteRatio(concepto=f"{inp.subasta.subastas_desiertas_previas} subasta(s) previa(s) desierta(s)",
                                   ajuste=desiertas))
    if vm > 0 and vt / vm < 0.6:
        chollo = float(params.get("adjudicacion.ajuste_chollo_pp"))
        ratio += chollo
        ajustes.append(AjusteRatio(concepto="valor de subasta inferior al 60 % del valor de mercado", ajuste=chollo))
    sin_acotar = ratio
    ratio = max(0.10, min(1.10, ratio))

    p_adj = vt * ratio
    rvc = escalera.p_max / p_adj if p_adj > 0 else 0.0
    # `inviable` por defecto, y no es defensa decorativa: `rvc` puede ser
    # NEGATIVO. Ocurre siempre que la puja máxima sensata sale por debajo de
    # cero, es decir, cuando la operación no se sostiene ni pujando 0 € — el
    # caso más común es una tasación baja sin comparables, con ICI hundido y
    # por tanto contingencia alta.
    #
    # La tabla `rvc_bandas` ya termina en `{min: 0.0, banda: inviable}`, de modo
    # que la INTENCIÓN de cubrir este caso estaba escrita; lo que faltaba era
    # que un valor negativo encajara en alguna banda. Sin el valor por defecto,
    # `next()` lanzaba `StopIteration` y el motor devolvía un 500 **justo en las
    # operaciones que debe rechazar**, que son la mitad de las reales. Detectado
    # con un caso real de la AEAT (44 m², 1940, sin comparables), no con una
    # fixture: el caso dorado §19 no lo cubre porque es una operación buena.
    banda = next((b["banda"] for b in params.get("adjudicacion.rvc_bandas")
                  if rvc >= b["min"]), "inviable")

    # Fase 5G.2: solo redacción. Importes con `formato.eur` (antes `:,.0f`, que
    # escribía «7,600 €»), y con la escalera degenerada (§9.3, marca de M12) el
    # plan no instruye a cargar límites ni a pujar: no hay límite utilizable.
    if escalera.degenerada:
        tacticas = [
            "No cargar límites ni pujar: la escalera de precios es degenerada (§9.3); "
            "la estructura de costes consume el valor y no hay precio límite utilizable",
        ]
    elif veredicto is not None and veredicto.estado == "inviable":
        # Fase 5J-4 (ADR-0028): no se inventa una recomendación.
        tacticas = [
            f"No pujar con estas condiciones: la puja mínima aprobable ({eur(veredicto.puja_minima_efectiva)}) "
            f"supera el precio máximo económico ({eur(veredicto.p_max)}); el informe dice qué tendría que cambiar",
        ]
    else:
        tacticas = (_tacticas(escalera, procedimiento.forma_puja, procedimiento.regimen_asumido) if procedimiento
                    else _tacticas(escalera, "visibles_con_prorroga"))
        if veredicto is not None and veredicto.puja_recomendada is not None \
                and veredicto.puja_recomendada != escalera.p_objetivo:
            tacticas.insert(0, f"Puja recomendada: {eur(veredicto.puja_recomendada)}, la mínima aprobable (el "
                               f"objetivo de {eur(escalera.p_objetivo)} no se aprobaría sin depender de la autoridad)")
    plan = [
        *tacticas,
        # Fase 5J-2b (ADR-0024): el depósito exigido por el régimen, no el 5 % del alta.
        ("Depósito requerido: " + texto_deposito(procedimiento)) if procedimiento else
        f"Depósito requerido: {eur(inp.subasta.deposito_pct * vt)} ({pct(inp.subasta.deposito_pct, 0)} del valor de subasta)",
        "Si aparece información nueva durante la subasta, re-análisis exprés; si el semáforo cae, retirada",
    ]
    if banda == "ajustado":
        plan.append("RVC 0,90–1,05: operación de oportunidad, no de plan — aceptar por escrito antes de pujar")
    if banda == "improbable":
        plan.append("RVC 0,80–0,90: pujar solo el precio ideal «por si acaso», asumiendo el coste del depósito")

    riesgo_ejecucion = [
        "Suspensión/sobreseimiento del procedimiento: capital del depósito inmovilizado sin operación",
        "Pago del remate en plazo legal sin condición suspensiva de financiación (incumplir ⇒ pérdida del depósito)",
        "Cargas descubiertas entre puja y pago: mitigación con nota simple ≤ 5 días antes del cierre",
    ]
    if inp.subasta.fuente == "judicial_boe":
        riesgo_ejecucion.append(_cesion_remate(procedimiento))

    hechos.update({"rvc": round(rvc, 3), "p_adj_esperado": round(p_adj, 2), "p_max": escalera.p_max})
    return PujaResultado(p_adj_esperado=round(p_adj, 2), ratio_base=round(ratio, 3),
                         rvc=round(rvc, 3), banda_rvc=banda, plan=plan,
                         riesgo_ejecucion=riesgo_ejecucion,
                         ratio_segmento=round(ratio_segmento, 3), ajustes_ratio=ajustes,
                         ratio_acotado=sin_acotar != ratio)

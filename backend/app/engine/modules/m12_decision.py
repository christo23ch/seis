"""M12 — Motor de decisión experto (§8) + algoritmo multicriterio de precios (§9).

Cuatro capas en orden estricto: vetos (T2) → riesgo agregado con dominancia →
MCDA (ICO) + escalera de precios (fórmulas cerradas) → escenarios y semáforo.
Todo determinista; cada disparo de regla queda trazado (P1, P2, P6).
"""
from __future__ import annotations

from app.engine.contracts import (AnalisisInput, CostesResultado, DecisionFinal,
                                  EscaleraPrecios, ICIResultado, ICUResultado,
                                  RAResultado, RentabilidadResultado, RiesgoOut,
                                  VetoOut)
from app.engine.rules.engine import Disparo

_ORDEN_SEM = {"verde": 0, "amarillo": 1, "naranja": 2, "rojo": 3}


# ───────────────────────── CAPA 2 · Riesgo agregado (§7.6) ─────────────────────────
def agregar_ra(riesgos: list[RiesgoOut], params) -> RAResultado:
    pesos: dict = params.seccion("riesgos.pesos")
    ra_base = sum(pesos[r.dimension] * (r.score / 25.0) * 100.0 for r in riesgos)

    altas = [r for r in riesgos if r.nivel == "alto"]
    criticas = [r for r in riesgos if r.nivel == "critico"]
    dom = params.seccion("riesgos.dominancia")
    ra, dominancia = ra_base, None
    if criticas:
        if any(not r.mitigable for r in criticas):
            ra, dominancia = max(ra, dom["critica_no_mitigable"]), "critica_no_mitigable"
        else:
            ra, dominancia = max(ra, dom["critica_mitigable"]), "critica_mitigable"
    elif len(altas) >= 2:
        ra, dominancia = max(ra, dom["dos_altas"]), "dos_altas"
    elif len(altas) == 1:
        ra, dominancia = max(ra, dom["una_alta"]), "una_alta"

    ra = round(min(100, ra))
    banda = next(b["banda"] for b in params.get("riesgos.bandas_ra") if ra <= b["max"])
    return RAResultado(ra=ra, ra_base=round(ra_base, 2), banda=banda,
                       dominancia_aplicada=dominancia, dimensiones=riesgos)


# ───────────────────── δ_v y valor de salida prudente (§9.4) ─────────────────────
def calcular_delta_v(params, banda_ra: str, cv: float, ici: ICIResultado) -> float:
    delta = float(params.get("valoracion.delta_base_pp"))
    delta += float(params.get(f"primas_ra.{banda_ra}.delta_mercado_pp"))
    for tramo in params.get("valoracion.delta_dispersion"):
        if cv <= float(tramo["max_cv"]):
            delta += float(tramo["pp"])
            break
    delta += ici.efecto_delta_v_pp
    return min(delta / 100.0, float(params.get("valoracion.delta_max_pct")))


# ───────────────────── CAPA 3 · Escalera de precios (§9.1–9.3) ────────────────────
def _precio_venta(m: float, vs: float, c_f: float, c_v: float) -> float:
    return (vs / (1 + m) - c_f) / (1 + c_v)


def calcular_escalera(inp: AnalisisInput, params, banda_ra: str, vs_p: float,
                      costes: CostesResultado, rna: float | None,
                      y_zona_pct: float, ici: int) -> EscaleraPrecios:
    perfil = params.seccion(f"perfiles.{inp.perfil}")
    fila = params.seccion(f"primas_ra.{banda_ra}")
    c_v, cf50, cf80 = costes.c_v, costes.c_f_p50, costes.c_f_p80
    detalle: dict[str, float] = {"delta_v_aplicado": 0.0}

    if perfil["tipo"] == "venta":
        m_obj = float(perfil["m_objetivo"]) * float(fila["mult_m"])
        m_min = float(perfil["m_minimo"]) * float(fila["mult_m"])
        m_exc = m_obj * float(params.get("precios.m_exc_mult"))
        p_ideal = _precio_venta(m_exc, vs_p, cf50, c_v)
        p_obj = _precio_venta(m_obj, vs_p, cf50, c_v)
        p_a = _precio_venta(m_min, vs_p, cf50, c_v)
        # rama pesimista: B_pes(P) = piso·I(P) ⇒ I = VS_pes/(1+piso)
        piso = float(perfil.get("piso_pesimista_frac_i", 0.0))
        vs_pes = vs_p * (1 - float(fila["stress_mercado"]))
        p_pes = (vs_pes / (1 + piso) - cf80) / (1 + c_v)
        p_max = min(p_a, p_pes)
        detalle.update({"m_objetivo_ajustado": round(m_obj, 4), "m_minimo_ajustado": round(m_min, 4),
                        "vs_pesimista": round(vs_pes, 2), "p_por_margen_min": round(p_a, 2),
                        "p_por_pesimista": round(p_pes, 2)})
    else:                                                     # rentista (§9.2)
        y_req = y_zona_pct + float(fila["y_req_pp"])
        if inp.zona.macro.dom_alquiler_dias > 60:
            y_req += 0.5                                      # prima de iliquidez de alquiler
        if ici < 60:
            y_req += 0.25                                     # prima de información
        rna = rna or 0.0
        y_suelo = float(perfil["y_bono_10a"]) + float(perfil["y_suelo_pp_sobre_bono"])

        def p_de_y(y_pct: float) -> float:
            return (rna / (y_pct / 100.0) - cf50) / (1 + c_v) if y_pct > 0 else 0.0

        p_ideal, p_obj = p_de_y(y_req + 1.0), p_de_y(y_req + 0.5)
        candidatos = [p_de_y(y_req)]
        f = inp.financiacion
        if f.tipo == "hipoteca" and f.ltv > 0:
            ts = (f.interes_anual_pct + float(params.get("financiacion.stress_tipos_pp"))) / 100
            dscr_min = float(params.get("financiacion.dscr_minimo"))
            candidatos.append(rna / (dscr_min * f.ltv * ts))              # DSCR = 1,2 estresado
            coc = float(perfil["coc_min"])
            den = coc * (1 + c_v - f.ltv) + f.ltv * f.interes_anual_pct / 100
            candidatos.append((rna - coc * cf50) / den if den > 0 else 0.0)
        p_max = min(candidatos)
        p_lim_rent = p_de_y(y_suelo)
        detalle.update({"y_req_pct": round(y_req, 3), "y_suelo_pct": round(y_suelo, 3), "rna": round(rna, 2)})

    # P_límite (§9.1): indiferencia estresada − coste de capital. Infranqueable por software.
    cc_anual = float(params.get("capital.coste_capital_anual"))
    p_lim_bruto = (vs_p - cf80) / (1 + c_v)
    i_aprox = p_max * (1 + c_v) + cf80
    coste_capital = cc_anual * i_aprox * (costes.plazo_meses_p80 / 12.0)
    p_lim = p_lim_bruto - coste_capital
    if perfil["tipo"] == "rentista":
        p_lim = min(p_lim, p_lim_rent) if p_lim_rent > 0 else p_lim
    detalle.update({"coste_capital": round(coste_capital, 2)})

    escalera = EscaleraPrecios(
        p_ideal=round(p_ideal), p_objetivo=round(p_obj), p_max=round(p_max),
        p_limite=round(p_lim), detalle=detalle,
    )
    escalera.degenerada = not (0 < escalera.p_ideal < escalera.p_objetivo
                               < escalera.p_max < escalera.p_limite)
    return escalera


# ───────────────────────── CAPA 3 · ICO (§8.5) ─────────────────────────
def _u_rentabilidad(roi_a: float, m_a_min: float, m_a_obj: float, cfg: dict) -> float:
    cero = cfg["cero_en_frac_min"] * m_a_min
    u_obj, frac_max = float(cfg["u_objetivo"]), float(cfg["u_max_frac"])
    techo = frac_max * m_a_obj
    if roi_a <= cero:
        return 0.0
    if roi_a <= m_a_obj:
        return u_obj * (roi_a - cero) / max(m_a_obj - cero, 1e-9)
    if roi_a >= techo:
        return 100.0
    return u_obj + (100 - u_obj) * (roi_a - m_a_obj) / max(techo - m_a_obj, 1e-9)


def _u_grupo_riesgo(riesgos: list[RiesgoOut], dims: tuple[str, ...], escalon: float) -> float:
    grupo = [r for r in riesgos if r.dimension in dims]
    peor = max(r.score for r in grupo)
    u = 100.0 * (1 - peor / 25.0)
    if any(r.nivel in ("alto", "critico") for r in grupo):
        u -= escalon
    return max(0.0, u)


def calcular_ico(inp: AnalisisInput, params, ra_res: RAResultado, rent: RentabilidadResultado,
                 icu: ICUResultado, ici: int, escalera: EscaleraPrecios,
                 plazo_meses: float) -> tuple[int, dict[str, float]]:
    pesos: dict = params.seccion("ico.pesos")
    perfil = params.seccion(f"perfiles.{inp.perfil}")
    cfg = params.seccion("ico.utilidad_rentabilidad")
    escalon = float(params.get("ico.escalon_alta"))

    if perfil["tipo"] == "venta":
        anual = lambda m: (1 + m) ** (12.0 / max(plazo_meses, 1)) - 1          # noqa: E731
        u_rent = _u_rentabilidad(rent.roi_anualizado,
                                 anual(float(perfil["m_minimo"])), anual(float(perfil["m_objetivo"])), cfg)
    else:
        y = (rent.y_neta or 0.0) * 100
        y_req = escalera.detalle.get("y_req_pct", 6.0)
        u_rent = _u_rentabilidad(y, 0.6 * y_req, y_req, cfg)

    u_fin = _u_grupo_riesgo(ra_res.dimensiones, ("financiero",), escalon)
    if inp.financiacion.tipo == "cash":
        u_fin = min(100.0, u_fin + float(params.get("ico.bonus_equity_financiero")))

    dom = params.seccion("ico.liquidez_dom")
    dom_dias = icu.dom_venta_dias if perfil["tipo"] == "venta" else icu.dom_alquiler_dias * 3
    u_liq = max(0.0, min(100.0, 100.0 * (dom["zero"] - dom_dias) / (dom["zero"] - dom["full"])))

    utilidades = {
        "rentabilidad": u_rent,
        "juridico": _u_grupo_riesgo(ra_res.dimensiones, ("juridico", "documental", "ocupacion"), escalon),
        "urbanistico": _u_grupo_riesgo(ra_res.dimensiones, ("urbanistico", "tecnico"), escalon),
        "financiero": u_fin,
        "ubicacion": float(icu.icu),
        "revalorizacion": float(icu.potencial_revalorizacion),
        "liquidez": u_liq,
        "informacion": float(ici),
    }
    ico = sum(pesos[k] * u for k, u in utilidades.items()) / 100.0
    umbral = float(params.get("ici.multiplicador_ico_umbral"))
    if ici < umbral:                                           # penalización estructural (§8.5)
        ico *= 0.80 + 0.20 * ici / umbral
    desglose = {k: round(pesos[k] * u / 100.0, 2) for k, u in utilidades.items()}
    return round(ico), desglose


# ─────────────────── CAPA 1+4 · Vetos, techos y semáforo (§8.6) ───────────────────
def procesar_disparos(disparos: list[Disparo]) -> tuple[list[VetoOut], list[str], list[str]]:
    vetos, techos, condiciones = [], [], []
    for d in disparos:
        if "veto" in d.efecto:
            v = d.efecto["veto"]
            vetos.append(VetoOut(codigo=d.codigo, motivo=v["motivo"],
                                 dimension=v.get("dimension"), subsanable_con=v.get("subsanable_con")))
        if "techo_semaforo" in d.efecto:
            techos.append(d.efecto["techo_semaforo"])
        if "condicion" in d.efecto:
            condiciones.append(d.efecto["condicion"])
    return vetos, techos, condiciones


def decidir_semaforo(params, ico: int, ra_res: RAResultado, rent: RentabilidadResultado,
                     ms_valor: float, rvc: float, ici: int, ici_techo: str | None,
                     escalera: EscaleraPrecios, vetos: list[VetoOut], techos: list[str],
                     inp: AnalisisInput) -> tuple[str, list[str]]:
    razones: list[str] = []
    if vetos:
        return "rojo", [f"Veto {v.codigo}: {v.motivo}" for v in vetos]
    if escalera.degenerada:
        return "rojo", ["Escalera de precios degenerada: la estructura de costes consume el valor (§9.3)"]
    if any(r.nivel == "critico" and not r.mitigable for r in ra_res.dimensiones):
        return "rojo", ["Riesgo crítico no mitigable"]

    b_pes = next(e.beneficio for e in rent.escenarios if e.nombre == "pesimista")
    i_base = rent.inversion_total
    hay_alta = any(r.nivel in ("alto", "critico") for r in ra_res.dimensiones)
    hay_critica = any(r.nivel == "critico" for r in ra_res.dimensiones)
    piso = float(params.get(f"perfiles.{inp.perfil}.piso_pesimista_frac_i", 0.0))

    sv, sa, sn = params.seccion("semaforo.verde"), params.seccion("semaforo.amarillo"), params.seccion("semaforo.naranja")
    if (ico >= sv["ico_min"] and not hay_alta and b_pes >= piso * i_base
            and ms_valor >= sv["ms_valor_min"] and rvc >= sv["rvc_min"] and ici >= sv["ici_min"]):
        candidato = "verde"
        razones.append(f"ICO {ico} sin riesgos altos; pesimista positivo; MS {ms_valor:.0%}; RVC {rvc:.2f}")
    elif (ico >= sa["ico_min"] and not hay_critica and b_pes >= sa["pes_piso_frac_i"] * i_base
          and rvc >= sa["rvc_min"] and ici >= sa["ici_min"]):
        candidato = "amarillo"
        razones.append(f"ICO {ico} en banda 60–74 o límites de Verde no alcanzados")
    elif ico >= sn["ico_min"] and rvc >= sn["rvc_min"] and not hay_critica:
        candidato = "naranja"
        razones.append(f"ICO {ico} en banda 45–59 o riesgos altos mitigables con condiciones")
    else:
        motivo = "ICO insuficiente" if ico < sn["ico_min"] else \
            ("RVC por debajo del mínimo" if rvc < sn["rvc_min"] else "riesgo crítico")
        return "rojo", [f"No alcanza Naranja: {motivo} (ICO {ico}, RVC {rvc:.2f})"]

    # Techos: dominancia de críticas mitigables, ICI y reglas de semáforo
    if hay_critica:
        techos = techos + ["naranja"]
        razones.append("Dimensión crítica mitigable ⇒ techo Naranja con condiciones (§7.6)")
    if hay_alta and candidato == "verde":
        techos = techos + ["amarillo"]
    if ici_techo:
        techos = techos + [ici_techo]
        razones.append(f"ICI {ici} impone techo {ici_techo} (§6.2)")
    for t in techos:
        if _ORDEN_SEM[t] > _ORDEN_SEM[candidato]:
            razones.append(f"Techo aplicado: {t}")
            candidato = t
    return candidato, razones


def margen_seguridad(p: float, c_v: float, c_f_p50: float, vs: float) -> float:
    """MS_valor (§9.5): caída de VS soportable antes de entrar en pérdida, a precio P."""
    i_total = p * (1 + c_v) + c_f_p50
    return max(0.0, 1 - i_total / vs) if vs > 0 else 0.0

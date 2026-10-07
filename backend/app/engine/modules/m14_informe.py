"""M14 — Generación del informe y checklist previo a la puja (§12, §13).

Cero cifras nuevas: todo número procede del resultado del pipeline; toda
afirmación, de una regla disparada o de un hecho. La narrativa LLM opcional
(con validador de cifras) se acopla en F2 sin tocar este módulo (P8).
"""
from __future__ import annotations

from app.engine.conservacion import NO_CONSTA
from app.engine.contracts import (AnalisisInput, AnalisisResult, ChecklistItem, ProcedimientoResultado,
                                  DecisionFinal)
# Fase 5G.2: un único formato de importes para M13 y M14 (`app/engine/formato.py`).
from app.engine.formato import eur as _eur
from app.engine.formato import tasa as _tasa
# Fase 5G.4-B: coma decimal y «25,0 %» en todo el texto que lee una persona.
from app.engine.formato import decimal as _dec
from app.engine.formato import pct as _pct
# Fase 5J-2a: el informe nombra los códigos y símbolos del motor con su texto legible.
from app.engine.textos import etiqueta as _et
from app.engine.textos import legible as _leg
from app.engine.procedimiento import bloque_aviso_aprobacion, texto_deposito


def _meses(x: float) -> str:
    """Fase 5J-2b: un plazo entero sin decimales («13»), uno fraccionario con uno («15,5»).
    Con la inmovilización el plazo deja de ser entero y `:.0f` lo redondeaba a par (16)."""
    return _dec(x, 0) if float(x).is_integer() else _dec(x, 1)


_SEM_ICONO = {"verde": "🟢 VERDE", "amarillo": "🟡 AMARILLO",
              "naranja": "🟠 NARANJA", "rojo": "🔴 ROJO"}


# ───────────────────────────── CHECKLIST (§13) ─────────────────────────────
def construir_checklist(inp: AnalisisInput, dec: DecisionFinal, hechos: dict, *,
                        metodo_valoracion: str = "comparables_ajustados",
                       procedimiento: ProcedimientoResultado | None = None) -> list[ChecklistItem]:
    d = inp.documentos
    items: list[ChecklistItem] = []
    n = [0]

    def add(grupo: str, texto: str, bloqueante: bool, estado: str, detalle: str | None = None):
        n[0] += 1
        items.append(ChecklistItem(grupo=grupo, orden=n[0], texto=texto,
                                   bloqueante=bloqueante, estado=estado, detalle=detalle))

    con_comunidad = inp.activo.tipologia in ("vivienda", "garaje", "trastero", "local", "oficina")
    ocupado = inp.ocupacion.estado not in ("vacio",)

    # A. Documental e información
    add("A. Documental", "Nota simple actualizada ≤ 5 días antes del cierre, cotejada con el edicto", True,
        "ok" if d.nota_simple and (d.nota_simple_dias or 99) <= 5 else "pendiente",
        f"Antigüedad declarada: {d.nota_simple_dias} días" if d.nota_simple else "Sin nota simple")
    add("A. Documental", "Certificación de cargas / condiciones de la subasta leídas íntegras", True,
        "ok" if d.cert_cargas else "pendiente")
    add("A. Documental", "ICI ≥ 45 o subsanación documentada de carencias críticas", True,
        "ok" if dec.ici >= 45 else "pendiente", f"ICI actual: {dec.ici}")
    add("A. Documental", "Avalúo/tasación de la subasta revisado y contrastado con VM propio", False,
        "ok" if d.avaluo else "pendiente")
    add("A. Documental", "Referencia catastral conciliada con finca registral; superficies coherentes", False,
        "ok" if d.catastro_conciliado else "pendiente")
    add("A. Documental", "Fotos recientes o visita exterior realizada", False,
        "ok" if (d.fotos_exterior or d.fotos_interior_o_visita) else "pendiente")

    # B. Jurídico
    subsist = float(hechos.get("carga_subsistente_total", 0.0))
    add("B. Jurídico", "Cargas anteriores subsistentes cuantificadas e incorporadas a C_F (o inexistentes)", True,
        "pendiente" if hechos.get("carga_anterior_indeterminada") else "ok", _eur(subsist))
    add("B. Jurídico", "Situación posesoria verificada según árbol §8.7.2", True,
        "ok" if d.posesion_verificada else "pendiente",
        f"Estado declarado: {_et(inp.ocupacion.estado)}")
    add("B. Jurídico", "Arrendamientos: fecha cierta, oponibilidad y retracto analizados",
        False, "ok" if "arrendado" not in inp.ocupacion.estado or d.posesion_verificada else "pendiente"
        if "arrendado" in inp.ocupacion.estado else "no_aplica")
    add("B. Jurídico", "VPO / prohibiciones de disponer / condiciones resolutorias descartadas o valoradas", False,
        "pendiente" if (inp.activo.vpo or hechos.get("prohibicion_disponer")
                        or hechos.get("condicion_resolutoria")) else "ok")
    add("B. Jurídico", "Certificado de deuda de la comunidad solicitado; derramas preguntadas", False,
        ("ok" if d.cert_comunidad else "pendiente") if con_comunidad else "no_aplica")
    add("B. Jurídico", "Procedimiento sin incidentes visibles que amenacen la adjudicación", False, "pendiente")

    # C. Fiscal
    base_min = float(hechos.get("base_fiscal_minima", 0.0))
    add("C. Fiscal", "Tributación de la adquisición determinada (árbol §8.7.3) y aplicada en c_v", True,
        "ok" if base_min > 0 else "pendiente",
        "Régimen calculado por el motor según los datos declarados; base imponible "
        + (f"= {_eur(base_min)} ({hechos.get('base_fiscal_origen', '')})" if base_min > 0 else
           "tomada de la puja por no constar valor de referencia: el impuesto es un mínimo"))
    add("C. Fiscal", "Plusvalía municipal y quién la soporta según condiciones de la subasta", False,
        "ok" if inp.costes.plusvalia_municipal_estimada > 0 else "pendiente")
    add("C. Fiscal", "Vehículo de compra decidido (persona física / sociedad) y coherente", False, "pendiente")

    # D. Económico-financiero
    # Fase 5J-2b (ADR-0024): el depósito exigido por el régimen del procedimiento.
    if procedimiento is not None and procedimiento.procedimiento == "no_aplica":
        detalle_dep = "Según las condiciones del vendedor"
    elif procedimiento is not None:
        detalle_dep = _eur(procedimiento.deposito_eur) if procedimiento.deposito_eur is not None else "No consta en la norma"
    else:
        detalle_dep = _eur(inp.subasta.deposito_pct * inp.subasta.valor_subasta)
    add("D. Económico", "Depósito disponible y transferido en plazo", True, "pendiente", detalle_dep)
    add("D. Económico", "Plan de pago del remate cubierto sin condición suspensiva de financiación", True,
        "ok" if inp.financiacion.tipo == "cash" or inp.financiacion.preaprobada else "pendiente")
    # Cierre de Fase 2: sin comparables no hay ancla de mercado independiente
    # (M03 §6.3), así que la escalera interna NO es una escalera utilizable —
    # aunque calcular_escalera() la siga calculando para el resto del DAG
    # (M11/M13). Este ítem es el único lugar del sistema que AFIRMA "está
    # cargada en la interfaz de puja"; dejarlo en "ok" prometería una
    # recomendación de puja que no existe.
    if metodo_valoracion == "sin_comparables":
        add("D. Económico", "Escalera de precios cargada en la interfaz de puja", True, "pendiente",
            "No determinable sin comparables de mercado independientes: no hay "
            "escalera utilizable para pujar (§6.3).")
    elif dec.precios.degenerada:
        # Fase 5G.2: con la escalera degenerada (§9.3, la marca de M12) no hay
        # límites que cargar; mismo patrón que «sin comparables».
        add("D. Económico", "Escalera de precios cargada en la interfaz de puja", True, "pendiente",
            "Escalera de precios degenerada (§9.3): no hay escalera utilizable para pujar.")
    else:
        add("D. Económico", "Escalera de precios cargada en la interfaz de puja", True, "ok",
            f"Objetivo {_eur(dec.precios.p_objetivo)} · Máx {_eur(dec.precios.p_max)} · Límite {_eur(dec.precios.p_limite)}")
    add("D. Económico", "Capital para C_F (reforma, posesión, tenencia) comprometido por calendario", False, "pendiente")
    add("D. Económico", "Coste de depósitos de otras subastas simultáneas contemplado (cartera §11.3)", False, "pendiente")

    # E. Técnico y operativo
    add("E. Técnico", "Presupuesto de reforma P50/P80 vigente (baremos < 6 meses)", False, "ok")
    add("E. Técnico", "ITE/IEE del edificio consultada; derramas estructurales preguntadas", False,
        ("ok" if d.ite_cee else "pendiente") if inp.activo.tipologia in ("vivienda", "local", "oficina") else "no_aplica")
    add("E. Técnico", "Suministros: estado de altas y boletines estimado", False, "pendiente")
    add("E. Técnico", "Seguro de daños (y de impago si rentista) cotizado para el día 1", False, "pendiente")
    add("E. Técnico", "Plan de toma de posesión escrito", False, "pendiente" if ocupado else "no_aplica")

    # F. Estrategia y ejecución
    add("F. Ejecución", "Semáforo Verde/Amarillo, o Naranja con todas sus condiciones verificadas y firmadas", True,
        "ok" if dec.semaforo in ("verde", "amarillo") else "pendiente",
        "; ".join(dec.condiciones) if dec.condiciones else None)
    add("F. Ejecución", "RVC dentro del umbral del perfil; si 0,90–1,05 aceptación explícita de 'operación de oportunidad'",
        True, "ok" if dec.rvc >= 1.05 else ("pendiente" if dec.rvc >= 0.80 else "pendiente"),
        f"RVC = {_dec(dec.rvc)} · P adjudicación esperado {_eur(dec.p_adj_esperado)}")
    add("F. Ejecución", "Calendario de cierre con extensiones entendido; responsable de puja designado", False, "pendiente")
    add("F. Ejecución", "Regla de retirada acordada (qué información nueva aborta la puja)", False, "pendiente")
    add("F. Ejecución", "Post-adjudicación: lista de primeras 72 h preparada", False, "pendiente")
    # Fase 5J-3 (ADR-0027): la aprobación del remate no es automática. Tras los de §13 y antes
    # del de la 5I-D, que sigue siendo el último: no desplaza ninguna numeración anterior.
    aviso = procedimiento.aviso_aprobacion if procedimiento is not None else None
    if aviso is not None:
        add("F. Ejecución", "Riesgo de aprobación del remate asumido por escrito", aviso.techo_naranja,
            "pendiente", aviso.condicion)
    # Fase 5I-D (ADR-0020): estado de conservación «No consta». AL FINAL para no
    # desplazar la numeración de §13. No bloqueante: en subasta judicial la visita
    # interior casi nunca es posible, y el presupuesto ya usa el estado prudente.
    # Sigue pendiente aunque haya fotos o visita: el informe dice «no consta» hasta
    # que se ELIJA el estado real; las fotos solo permiten hacerlo.
    if inp.activo.estado_conservacion == NO_CONSTA:
        asumido = hechos["activo.estado_conservacion_asumido"]
        con_evidencia = d.fotos_interior_o_visita or inp.reforma.visita_interior
        add("E. Técnico", "Estado de conservación verificado con visita interior o fotos interiores", False,
            "pendiente",
            (f"Hay fotos interiores o visita: elija el estado real en lugar de «No consta» (hoy se asume «{asumido}»)"
             if con_evidencia else f"No consta: se asume «{asumido}» (P5)"))
    return items


# ───────────────────────────── INFORME (§12) ─────────────────────────────
def construir_informe(inp: AnalisisInput, res_parciales: dict, dec: DecisionFinal,
                      checklist: list[ChecklistItem], *, estado_asumido: str | None = None,
                      seccion_procedimiento: str = "",
                      procedimiento: ProcedimientoResultado | None = None) -> str:
    """`seccion_procedimiento` (Fase 5J-1, ADR-0022): subapartado informativo que cierra
    el §8, ya redactado por `app/engine/procedimiento.py`. Vacío ⇒ informe idéntico al
    anterior a la fase."""
    val, icu, ref = res_parciales["valoracion"], res_parciales["icu"], res_parciales["reforma"]
    # Fase 5J-2b (ADR-0024): el §2 cita el depósito exigido por el régimen.
    texto_dep = (texto_deposito(procedimiento) if procedimiento is not None
                 else _pct(inp.subasta.deposito_pct, 0))
    costes, ra, rent = res_parciales["costes"], res_parciales["riesgos"], res_parciales["rentabilidad"]
    puja, ici = res_parciales["puja"], res_parciales["ici"]
    a = inp.activo
    # Fase 5I-D: «No consta» se declara como supuesto, no se presenta como dato.
    if a.estado_conservacion == NO_CONSTA and not estado_asumido:
        raise ValueError("estado «No consta» sin estado asumido: el pipeline debe pasarlo")
    texto_estado = (f"estado de conservación **no consta**: se asume «{estado_asumido}» (P5) hasta "
                    f"verificarlo con visita interior o fotos interiores"
                    if a.estado_conservacion == NO_CONSTA else f"estado {a.estado_conservacion}")

    filas_riesgo = "\n".join(
        f"| {_et(r.dimension)} | {r.probabilidad}×{r.impacto} = {r.score} | {_et(r.nivel)} | "
        f"{_leg('; '.join(r.condiciones)) or '—'} |" for r in ra.dimensiones)
    filas_esc = "\n".join(
        f"| {e.nombre} | {_pct(e.probabilidad, 0)} | {_eur(e.vs)} | {_eur(e.coste_total)} | "
        f"{_eur(e.beneficio)} | {_pct(e.roi)} | {_pct(e.roi_anualizado)} | {_meses(e.plazo_meses)} m |"
        for e in rent.escenarios)
    filas_c50 = "\n".join(f"| {_et(k)} | {_eur(v)} |" for k, v in costes.desglose_p50.items())
    if costes.base_fiscal_minima > 0:
        base_fiscal = (f" Base imponible del impuesto: {_eur(costes.base_fiscal_minima)} "
                       f"({_et(costes.base_fiscal_origen)}), no la puja, cuando esta "
                       f"queda por debajo (art. 10 TRLITPAJD).")
    else:
        base_fiscal = (" **Base imponible del impuesto calculada sobre la puja, como suelo: no consta "
                       "valor de referencia del Catastro ni valor declarado.** La base legal es el mayor "
                       "de los tres, así que el impuesto aquí es un MÍNIMO y el real puede ser mayor. "
                       "Supuesto no verificado, no dato confirmado.")
    bloq = [c for c in checklist if c.bloqueante and c.estado == "pendiente"]
    filas_bloq = "\n".join(f"- [ ] **[B]** {_leg(c.texto)}" + (f" — _{_leg(c.detalle)}_" if c.detalle else "")
                           for c in bloq) or "- (ninguno)"
    # Fase 2: sin comparables no hay ancla de mercado independiente (M03 §6.3,
    # metodo="sin_comparables") y VM/VS son el propio valor de subasta degradado
    # a confianza 0 — no una valoración. No se presentan como cifra central; el
    # valor de subasta, si aparece, queda etiquetado como tal y no como valoración.
    if val.metodo == "sin_comparables":
        seccion_valoracion = (
            "**NO DETERMINABLE: sin comparables de mercado.** M03 no dispone de "
            "ningún comparable independiente (§6.3): no hay ancla de mercado con "
            f"la que contrastar el precio. El **valor de subasta** declarado es "
            f"{_eur(inp.subasta.valor_subasta)} — es el dato de la fuente, **no una "
            "valoración de mercado**, y no debe leerse como tal ni usarse para "
            "decidir una puja."
        )
    else:
        seccion_valoracion = (
            f"Método: {_et(val.metodo)}, con {val.n_comparables} comparables "
            f"(CV {_pct(val.dispersion_cv)}, confianza {_pct(val.confianza, 0)}). "
            f"VM actual {_eur(val.vm)} · VS de salida {_eur(val.vs)} ({_eur(val.vs_m2)}/m²) · "
            f"descuento de prudencia aplicado {_pct(res_parciales['delta_v'])} ⇒ "
            f"**VS prudente {_eur(res_parciales['vs_p'])}**."
        )
    condiciones = "\n".join(f"- {_leg(c)}" for c in dec.condiciones) or "- (ninguna)"
    vetos = "\n".join(f"- **{v.codigo}**: {_leg(v.motivo)}"
                      + (f" · Subsanable con: {_leg(v.subsanable_con)}" if v.subsanable_con else "")
                      for v in dec.vetos) or "- (ninguno)"
    # Fase 5G.2: degenerada (§9.3), el límite no se ofrece como cifra accionable;
    # el valor calculado sigue en `decision.precios.p_limite`.
    fila_limite = ("No utilizable: escalera de precios degenerada (§9.3)" if dec.precios.degenerada
                   else f"{_eur(dec.precios.p_limite)} — infranqueable")
    trazas = "\n".join(f"- `{r.codigo}` v{r.version} ({_et(r.categoria)})" for r in res_parciales["reglas"]) or "- (sin disparos)"
    # Fase 5G.4 (ADR-0016): el coste de capital solo descuenta el precio límite
    # (§9.1). La tasa sale de los parámetros aplicados y el importe de M12; si
    # falta cualquiera de los dos, no se afirma nada.
    cc_anual = res_parciales.get("coste_capital_anual")
    cc_importe = dec.precios.detalle.get("coste_capital")
    nota_coste_capital = (
        f"\n\nEl coste de capital ({_tasa(cc_anual)} anual, coste de oportunidad del capital "
        f"propio) solo se descuenta del precio límite (§9.1); ROI y TIR no lo incluyen. "
        f"Importe aplicado: {_eur(cc_importe)}."
        if cc_anual is not None and cc_importe is not None else "")
    # Fase 5H.1-A (ADR-0017): VAN y diferencial, con los flujos de la TIR. Sin dato, nada.
    van, dif = getattr(rent, "van_coste_capital", None), getattr(rent, "diferencial_tir_coste_capital", None)
    nota_van = (
        f"\n\nVAN al coste de capital ({_tasa(cc_anual)}): {_eur(van)} · "
        f"TIR frente a coste de capital: {_dec(dif, 2, signo=True)} puntos"
        if van is not None and dif is not None and cc_anual is not None else "")
    # Fase 5H.1-C (§9.5, ADR-0019): colchón de plazo. Sin dato, nada.
    colchon, colchon_max = (getattr(dec, "colchon_plazo_meses", None),
                            getattr(dec, "colchon_plazo_meses_p_max", None))
    nota_colchon = (
        f"\n\nColchón de plazo: {_dec(colchon, 1)} meses a precio objetivo"
        + (f" ({_dec(colchon_max, 1)} a precio máximo)" if colchon_max is not None else "")
        + ", hasta beneficio cero por tenencia y coste de capital."
        if colchon is not None else "")

    # Fase 5J-3 (ADR-0027): la franja del letrado, destacada bajo el semáforo.
    aviso = procedimiento.aviso_aprobacion if procedimiento is not None else None
    bloque_aviso = f"\n{bloque_aviso_aprobacion(aviso)}\n" if aviso is not None else ""

    return f"""# Informe de análisis SEIS

## 1 · Página de decisión

# {_SEM_ICONO[dec.semaforo]}
{bloque_aviso}
| Métrica | Valor |
|---|---|
| **ICO** (calidad de la oportunidad) | **{dec.ico} / 100** |
| **RA** (riesgo agregado) | {dec.ra} / 100 ({_et(ra.banda)}) |
| ICI (calidad de la información) | {dec.ici} / 100 |
| ICU (calidad de ubicación) | {dec.icu} / 100 |
| **Precio ideal** | {_eur(dec.precios.p_ideal)} |
| **Precio objetivo** | {_eur(dec.precios.p_objetivo)} |
| **Precio máximo recomendado** | {_eur(dec.precios.p_max)} |
| **Precio límite absoluto** | {fila_limite} |
| ROI base (a P objetivo) | {_pct(rent.roi)} ({_pct(rent.roi_anualizado)} anualizado) |
| TIR anual | {_pct(rent.tir_anual)} |
| Margen de seguridad (caída de VS soportable) | {_pct(dec.margen_seguridad_valor)} |
| Valor esperado (3 escenarios) | {_eur(rent.valor_esperado)} |
| P. adjudicación esperado · RVC | {_eur(dec.p_adj_esperado)} · **{_dec(dec.rvc)}** ({puja.banda_rvc}) |

**Razones principales:** {_leg(" · ".join(dec.razones[:3]))}

**Condiciones (si Naranja/Amarillo):**
{condiciones}

**Vetos:**
{vetos}

## 2 · Activo y subasta
{a.tipologia.capitalize()} de {a.superficie_m2:.0f} m² en {a.municipio or "—"} ({a.provincia or "—"}), {texto_estado}. Subasta {_et(inp.subasta.fuente)}, valor de subasta {_eur(inp.subasta.valor_subasta)}, depósito {texto_dep}. Ocupación declarada: {_et(inp.ocupacion.estado)}.

## 3 · Valoración
{seccion_valoracion}

## 4 · Mercado y ubicación
ICU {icu.icu} (macro {icu.macro_score:.0f} · micro {icu.micro_score:.0f}). Tendencia {_dec(icu.tendencia_5a_pct, 1, signo=True)} %/a · DOM venta {icu.dom_venta_dias:.0f} d · DOM alquiler {icu.dom_alquiler_dias:.0f} d · Potencial de revalorización {icu.potencial_revalorizacion}/100.

## 5 · Plan de obra y costes
Reforma nivel **{ref.nivel}**: {_eur(ref.total_p50)} (P50) / {_eur(ref.total_p80)} (P80), {ref.plazo_obra_meses:.0f} meses de obra. Costes proporcionales al precio: {_pct(costes.c_v, 2)} ({costes.regimen_fiscal.upper()}).{base_fiscal} Plazo total {_meses(costes.plazo_meses_p50)} m (P50) / {_meses(costes.plazo_meses_p80)} m (P80). Contingencia {_pct(costes.contingencia_pct, 0)}.

| Partida de costes fijos (P50) | Importe |
|---|---|
{filas_c50}
| **Total de costes fijos P50 / P80** | **{_eur(costes.c_f_p50)} / {_eur(costes.c_f_p80)}** |

## 6 · Riesgos (matriz P×I, §7)
| Dimensión | P×I | Nivel | Mitigación |
|---|---|---|---|
{filas_riesgo}

Riesgo agregado **RA {dec.ra}** (banda {_et(ra.banda)}{", dominancia: " + _et(ra.dominancia_aplicada) if ra.dominancia_aplicada else ""}).

## 7 · Análisis financiero (a precio objetivo {_eur(dec.precios.p_objetivo)})
| Escenario | Prob. | VS | Coste total | Beneficio | ROI | ROI anual | Plazo |
|---|---|---|---|---|---|---|---|
{filas_esc}{nota_coste_capital}{nota_van}{nota_colchon}

## 8 · Estrategia de puja
Ratio histórico del segmento: {_pct(puja.ratio_base, 0)} sobre valor de subasta.
{chr(10).join("- " + _leg(p) for p in puja.plan)}

**Riesgo de ejecución del proceso:**
{chr(10).join("- " + _leg(p) for p in puja.riesgo_ejecucion)}{seccion_procedimiento}

## 9 · Checklist previo a la puja — bloqueantes pendientes
{filas_bloq}

## 10 · Trazabilidad
Reglas disparadas (versión reglas {dec.version_reglas} · parámetros {dec.version_parametros}):
{trazas}

---
*Informe generado por SEIS. Los parámetros legales y fiscales aplicados son datos versionados que deben validarse con asesoría profesional (§20 de la especificación). La decisión final de puja corresponde al comité de inversión.*
"""

"""M14 — Generación del informe y checklist previo a la puja (§12, §13).

Cero cifras nuevas: todo número procede del resultado del pipeline; toda
afirmación, de una regla disparada o de un hecho. La narrativa LLM opcional
(con validador de cifras) se acopla en F2 sin tocar este módulo (P8).
"""
from __future__ import annotations

from app.engine.contracts import (AnalisisInput, AnalisisResult, ChecklistItem,
                                  DecisionFinal)

_SEM_ICONO = {"verde": "🟢 VERDE", "amarillo": "🟡 AMARILLO",
              "naranja": "🟠 NARANJA", "rojo": "🔴 ROJO"}


def _eur(x: float | None) -> str:
    return f"{x:,.0f} €".replace(",", ".") if x is not None else "—"


# ───────────────────────────── CHECKLIST (§13) ─────────────────────────────
def construir_checklist(inp: AnalisisInput, dec: DecisionFinal, hechos: dict) -> list[ChecklistItem]:
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
        f"Estado declarado: {inp.ocupacion.estado}")
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
    deposito = inp.subasta.deposito_pct * inp.subasta.valor_subasta
    add("D. Económico", "Depósito disponible y transferido en plazo", True, "pendiente", _eur(deposito))
    add("D. Económico", "Plan de pago del remate cubierto sin condición suspensiva de financiación", True,
        "ok" if inp.financiacion.tipo == "cash" or inp.financiacion.preaprobada else "pendiente")
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
        f"RVC = {dec.rvc:.2f} · P adjudicación esperado {_eur(dec.p_adj_esperado)}")
    add("F. Ejecución", "Calendario de cierre con extensiones entendido; responsable de puja designado", False, "pendiente")
    add("F. Ejecución", "Regla de retirada acordada (qué información nueva aborta la puja)", False, "pendiente")
    add("F. Ejecución", "Post-adjudicación: lista de primeras 72 h preparada", False, "pendiente")
    return items


# ───────────────────────────── INFORME (§12) ─────────────────────────────
def construir_informe(inp: AnalisisInput, res_parciales: dict, dec: DecisionFinal,
                      checklist: list[ChecklistItem]) -> str:
    val, icu, ref = res_parciales["valoracion"], res_parciales["icu"], res_parciales["reforma"]
    costes, ra, rent = res_parciales["costes"], res_parciales["riesgos"], res_parciales["rentabilidad"]
    puja, ici = res_parciales["puja"], res_parciales["ici"]
    a = inp.activo

    filas_riesgo = "\n".join(
        f"| {r.dimension} | {r.probabilidad}×{r.impacto} = {r.score} | {r.nivel} | "
        f"{'; '.join(r.condiciones) or '—'} |" for r in ra.dimensiones)
    filas_esc = "\n".join(
        f"| {e.nombre} | {e.probabilidad:.0%} | {_eur(e.vs)} | {_eur(e.coste_total)} | "
        f"{_eur(e.beneficio)} | {e.roi:.1%} | {e.roi_anualizado:.1%} | {e.plazo_meses:.0f} m |"
        for e in rent.escenarios)
    filas_c50 = "\n".join(f"| {k} | {_eur(v)} |" for k, v in costes.desglose_p50.items())
    if costes.base_fiscal_minima > 0:
        base_fiscal = (f" Base imponible del impuesto: {_eur(costes.base_fiscal_minima)} "
                       f"({costes.base_fiscal_origen.replace('_', ' ')}), no la puja, cuando esta "
                       f"queda por debajo (art. 10 TRLITPAJD).")
    else:
        base_fiscal = (" **Base imponible del impuesto calculada sobre la puja, como suelo: no consta "
                       "valor de referencia del Catastro ni valor declarado.** La base legal es el mayor "
                       "de los tres, así que el impuesto aquí es un MÍNIMO y el real puede ser mayor. "
                       "Supuesto no verificado, no dato confirmado.")
    bloq = [c for c in checklist if c.bloqueante and c.estado == "pendiente"]
    filas_bloq = "\n".join(f"- [ ] **[B]** {c.texto}" + (f" — _{c.detalle}_" if c.detalle else "") for c in bloq) or "- (ninguno)"
    condiciones = "\n".join(f"- {c}" for c in dec.condiciones) or "- (ninguna)"
    vetos = "\n".join(f"- **{v.codigo}**: {v.motivo}" + (f" · Subsanable con: {v.subsanable_con}" if v.subsanable_con else "")
                      for v in dec.vetos) or "- (ninguno)"
    trazas = "\n".join(f"- `{r.codigo}` v{r.version} ({r.categoria})" for r in res_parciales["reglas"]) or "- (sin disparos)"

    return f"""# Informe de análisis SEIS

## 1 · Página de decisión

# {_SEM_ICONO[dec.semaforo]}

| Métrica | Valor |
|---|---|
| **ICO** (calidad de la oportunidad) | **{dec.ico} / 100** |
| **RA** (riesgo agregado) | {dec.ra} / 100 ({ra.banda}) |
| ICI (calidad de la información) | {dec.ici} / 100 |
| ICU (calidad de ubicación) | {dec.icu} / 100 |
| **Precio ideal** | {_eur(dec.precios.p_ideal)} |
| **Precio objetivo** | {_eur(dec.precios.p_objetivo)} |
| **Precio máximo recomendado** | {_eur(dec.precios.p_max)} |
| **Precio límite absoluto** | {_eur(dec.precios.p_limite)} — infranqueable |
| ROI base (a P objetivo) | {rent.roi:.1%} ({rent.roi_anualizado:.1%} anualizado) |
| TIR anual | {rent.tir_anual:.1%} |
| Margen de seguridad (caída de VS soportable) | {dec.margen_seguridad_valor:.1%} |
| Valor esperado (3 escenarios) | {_eur(rent.valor_esperado)} |
| P. adjudicación esperado · RVC | {_eur(dec.p_adj_esperado)} · **{dec.rvc:.2f}** ({puja.banda_rvc}) |

**Razones principales:** {" · ".join(dec.razones[:3])}

**Condiciones (si Naranja/Amarillo):**
{condiciones}

**Vetos:**
{vetos}

## 2 · Activo y subasta
{a.tipologia.capitalize()} de {a.superficie_m2:.0f} m² en {a.municipio or "—"} ({a.provincia or "—"}), estado {a.estado_conservacion}. Subasta {inp.subasta.fuente}, valor de subasta {_eur(inp.subasta.valor_subasta)}, depósito {inp.subasta.deposito_pct:.0%}. Ocupación declarada: {inp.ocupacion.estado}.

## 3 · Valoración
Método {val.metodo} con {val.n_comparables} comparables (CV {val.dispersion_cv:.1%}, confianza {val.confianza:.0%}). VM actual {_eur(val.vm)} · VS de salida {_eur(val.vs)} ({_eur(val.vs_m2)}/m²) · δ_v aplicado {res_parciales["delta_v"]:.1%} ⇒ **VS prudente {_eur(res_parciales["vs_p"])}**.

## 4 · Mercado y ubicación
ICU {icu.icu} (macro {icu.macro_score:.0f} · micro {icu.micro_score:.0f}). Tendencia {icu.tendencia_5a_pct:+.1f} %/a · DOM venta {icu.dom_venta_dias:.0f} d · DOM alquiler {icu.dom_alquiler_dias:.0f} d · Potencial de revalorización {icu.potencial_revalorizacion}/100.

## 5 · Plan de obra y costes
Reforma nivel **{ref.nivel}**: {_eur(ref.total_p50)} (P50) / {_eur(ref.total_p80)} (P80), {ref.plazo_obra_meses:.0f} meses de obra. c_v = {costes.c_v:.2%} ({costes.regimen_fiscal.upper()}).{base_fiscal} Plazo total {costes.plazo_meses_p50:.0f} m (P50) / {costes.plazo_meses_p80:.0f} m (P80). Contingencia {costes.contingencia_pct:.0%}.

| Partida C_F (P50) | Importe |
|---|---|
{filas_c50}
| **Total C_F P50 / P80** | **{_eur(costes.c_f_p50)} / {_eur(costes.c_f_p80)}** |

## 6 · Riesgos (matriz P×I, §7)
| Dimensión | P×I | Nivel | Mitigación |
|---|---|---|---|
{filas_riesgo}

Riesgo agregado **RA {dec.ra}** (banda {ra.banda}{", dominancia: " + ra.dominancia_aplicada if ra.dominancia_aplicada else ""}).

## 7 · Análisis financiero (a precio objetivo {_eur(dec.precios.p_objetivo)})
| Escenario | Prob. | VS | Coste total | Beneficio | ROI | ROI anual | Plazo |
|---|---|---|---|---|---|---|---|
{filas_esc}

## 8 · Estrategia de puja
Ratio histórico del segmento: {puja.ratio_base:.0%} sobre valor de subasta.
{chr(10).join("- " + p for p in puja.plan)}

**Riesgo de ejecución del proceso:**
{chr(10).join("- " + p for p in puja.riesgo_ejecucion)}

## 9 · Checklist previo a la puja — bloqueantes pendientes
{filas_bloq}

## 10 · Trazabilidad
Reglas disparadas (versión reglas {dec.version_reglas} · parámetros {dec.version_parametros}):
{trazas}

---
*Informe generado por SEIS. Los parámetros legales y fiscales aplicados son datos versionados que deben validarse con asesoría profesional (§20 de la especificación). La decisión final de puja corresponde al comité de inversión.*
"""

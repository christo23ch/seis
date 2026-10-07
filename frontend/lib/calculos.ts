/**
 * Fase 5K-D — «Ver cálculo»: fórmula, valores sustituidos y resultado de las métricas
 * cuyo desglose viaja en el resultado del motor. Fase 5J-2a: el motor emite ya los
 * operandos que faltaban (margen de P_ideal, estrés y piso del pesimista, tramo fiscal,
 * candidatos del perfil rentista, P_límite bruto, pesos y suelo del RA, ajustes de P_adj,
 * flujos de la TIR y el VAN, operandos del colchón y desglose del plazo).
 *
 * Reglas (no negociables):
 *   · El frontend NO recalcula: el resultado mostrado es siempre el del motor. Aquí
 *     solo se escribe la fórmula y se colocan en ella los valores que trae el resultado.
 *   · Cada fórmula reproduce el código del motor y se verificó recalculándola en
 *     `tests/calculos.test.ts` con resultados reales; la referencia va en `origen`.
 *   · Si falta un dato (resultado anterior a la 5J-2a), no se inventa: `disponible: false`
 *     con el dato que falta.
 *
 * Las fórmulas usan los símbolos del motor (`P_max`, `C_F`…): los pinta `TextoFormulas`.
 */
import { eur, num, pct } from "@/lib/format";
import { IDENTIFICADORES } from "@/lib/formulas";
import { humanizar } from "@/lib/presentacion-valores";
import type { Resultado } from "@/lib/types";

export const NO_DISPONIBLE = "Cálculo no disponible aún";

export interface FilaCalculo { etiqueta: string; valor: string }
export interface Calculo {
  clave: string;
  titulo: string;
  disponible: boolean;
  formula?: string;
  sustitucion?: string;
  resultado?: string;
  filas?: FilaCalculo[];
  nota?: string;
  /** Si no está disponible: qué dato falta en el resultado. */
  falta?: string;
  /** Dónde lo calcula el motor (informativo). */
  origen: string;
}

const etiquetaClave = (k: string) => {
  const t = IDENTIFICADORES[k] ?? humanizar(k);
  return t.charAt(0).toUpperCase() + t.slice(1);
};
const noDisponible = (clave: string, titulo: string, falta: string, origen: string): Calculo =>
  ({ clave, titulo, disponible: false, falta, origen });
/** Los operandos viajan redondeados: rehacer la cuenta a mano puede diferir un poco. */
const REDONDEO = "Valores del resultado, redondeados: rehacer la cuenta a mano puede diferir en unos euros o décimas.";
const sumaTexto = (valores: number[], fmt: (n: number) => string) => valores.map(fmt).join(" + ");
const SIN_DATO_5J2A = "(resultado anterior a la 5J-2a)";

/* ── ICI ──────────────────────────────────────────────────────────────────── */

/** Penalización de un texto del motor «código (−N)»; `null` si no tiene ese formato. */
export function puntosPenalizacion(texto: string): number | null {
  const m = /\(−(\d+(?:[.,]\d+)?)\)\s*$/.exec(texto);
  return m ? Number(m[1].replace(",", ".")) : null;
}

export function calculoIci(ici: Resultado["ici"]): Calculo {
  const filas = Object.entries(ici.desglose).map(([k, v]) => ({ etiqueta: etiquetaClave(k), valor: `${num(v, 1)} puntos` }));
  // 5J-2a: penalizaciones estructuradas; en resultados anteriores, leídas de su texto.
  const penal = ici.penalizaciones_detalle
    ? ici.penalizaciones_detalle.map((p) => p.puntos)
    : ici.penalizaciones.map(puntosPenalizacion);
  if (penal.some((p) => p === null)) {
    return noDisponible("ici", "ICI", "el importe de alguna penalización no se puede leer de su texto", "m02_validacion.py");
  }
  const totalPenal = (penal as number[]).reduce((a, b) => a + b, 0);
  return {
    clave: "ici", titulo: "ICI (calidad de la información)", disponible: true, origen: "m02_validacion.py",
    formula: "ICI = Σ puntos de la documentación − penalizaciones, redondeado y entre 0 y 100",
    sustitucion: `ICI = (${sumaTexto(Object.values(ici.desglose), (n) => num(n, 1))}) − ${num(totalPenal, 1)}`,
    resultado: `${ici.ici} / 100`,
    filas: [...filas, ...(ici.penalizaciones_detalle
      ? ici.penalizaciones_detalle.map((p) => ({ etiqueta: `Penalización: ${etiquetaClave(p.codigo)}`, valor: `−${num(p.puntos, 1)}` }))
      : ici.penalizaciones.map((p) => ({ etiqueta: "Penalización", valor: p })))],
    nota: ici.carencias.length ? `Carencias: ${ici.carencias.map((c) => IDENTIFICADORES[c] ?? c).join("; ")}.` : undefined,
  };
}

/* ── costes, plazo y reforma ──────────────────────────────────────────────── */

export function calculoCf(costes: Resultado["costes"], escenario: "p50" | "p80"): Calculo {
  const desglose = escenario === "p50" ? costes.desglose_p50 : costes.desglose_p80;
  const total = escenario === "p50" ? costes.c_f_p50 : costes.c_f_p80;
  const titulo = `C_F ${escenario.toUpperCase()} (costes fijos)`;
  if (!desglose) return noDisponible(`cf_${escenario}`, titulo, `el desglose de C_F ${escenario.toUpperCase()}`, "m06_costes.py");
  return {
    clave: `cf_${escenario}`, titulo, disponible: true, origen: "m06_costes.py",
    formula: `C_F ${escenario.toUpperCase()} = suma de las partidas`,
    sustitucion: `C_F = ${sumaTexto(Object.values(desglose), eur)}`,
    resultado: eur(total),
    filas: Object.entries(desglose).map(([k, v]) => ({ etiqueta: etiquetaClave(k), valor: eur(v) })),
    nota: escenario === "p80" ? "En P80 la contingencia es 0: se consume en el escenario de estrés (§7.7)." : undefined,
  };
}

export function calculoCv(costes: Resultado["costes"]): Calculo {
  const d = costes.c_v_desglose;
  if (!d) return noDisponible("cv", "c_v (costes proporcionales al precio)", "el desglose de c_v", "m06_costes.py");
  return {
    clave: "cv", titulo: "c_v (costes proporcionales al precio)", disponible: true, origen: "m06_costes.py",
    formula: "c_v = impuesto de la adquisición + aranceles variables",
    sustitucion: `c_v = ${sumaTexto(Object.values(d), (n) => pct(n, 2))}`,
    resultado: pct(costes.c_v, 2),
    filas: Object.entries(d).map(([k, v]) => ({ etiqueta: etiquetaClave(k), valor: pct(v, 2) })),
    nota: `Régimen fiscal: ${costes.regimen_fiscal.toUpperCase()}. ${REDONDEO}`,
  };
}

export function calculoPlazo(costes: Resultado["costes"]): Calculo {
  const d = costes.plazo_desglose;
  const titulo = "Plazo de la operación";
  if (!d) return noDisponible("plazo", titulo, `su composición (ocupación, obra y comercialización) ${SIN_DATO_5J2A}`, "m06_costes.py");
  // 5J-2b (ADR-0026): el cierre → pago del resto → posesión entra en el plazo. Un resultado
  // anterior no trae el término y se explica con la fórmula de entonces.
  const inmov = d.inmovilizacion;
  const p80 = "Plazo P80 = Plazo P50 × multiplicador del escenario pesimista";
  return {
    clave: "plazo", titulo, disponible: true, origen: "m06_costes.py",
    formula: inmov == null
      ? `Plazo P50 = meses de ocupación + meses de obra + meses de comercialización; ${p80}`
      : `Plazo P50 = meses de ocupación + meses de obra + meses de comercialización + meses de inmovilización (cierre → pago del resto); ${p80}`,
    sustitucion: `P50 = ${num(d.ocupacion, 1)} + ${num(d.obra, 1)} + ${num(d.comercializacion, 1)}`
      + (inmov == null ? "" : ` + ${num(inmov, 1)}`)
      + `; P80 = ${num(costes.plazo_meses_p50, 1)} × ${num(d.multiplicador_p80, 2)}`,
    resultado: `${num(costes.plazo_meses_p50, 1)} meses (P50) / ${num(costes.plazo_meses_p80, 1)} meses (P80)`,
    nota: inmov == null ? undefined
      : "Los meses de inmovilización salen del procedimiento; su origen (plazo legal máximo, régimen más largo o estimación sin base legal) y sus avisos están en «Procedimiento y umbrales legales». El P80 se redondea a un decimal.",
  };
}

export function calculoReforma(reforma: Resultado["reforma"]): Calculo {
  const partidas = reforma.partidas;
  if (!partidas || partidas.obra == null || partidas.tecnicos_licencia == null) {
    return noDisponible("reforma", "Reforma", "las partidas de la reforma", "m05_reforma.py");
  }
  // En M05 la obra YA incluye los extras conocidos (`obra_p50 = coste·m²·k + partidas_extra`):
  // se muestran como «de ello», nunca como un sumando más.
  const extras = partidas.extras_conocidos ?? 0;
  return {
    clave: "reforma", titulo: `Reforma (nivel ${reforma.nivel})`, disponible: true, origen: "m05_reforma.py",
    formula: "Reforma P50 = obra (incluidos los extras conocidos) + técnicos y licencia",
    sustitucion: `Reforma = ${eur(partidas.obra)} + ${eur(partidas.tecnicos_licencia)}`,
    resultado: `${eur(reforma.total_p50)} (P80: ${eur(reforma.total_p80)})`,
    filas: [
      { etiqueta: "Obra", valor: eur(partidas.obra) },
      ...(extras ? [{ etiqueta: "de ello, extras conocidos", valor: eur(extras) }] : []),
      { etiqueta: "Técnicos y licencia", valor: eur(partidas.tecnicos_licencia) },
    ],
  };
}

/* ── valoración (comparables) ─────────────────────────────────────────────── */

export function calculoValoracion(val: Resultado["valoracion"], superficie?: number | null): Calculo {
  const titulo = "Valoración por comparables";
  const testigos = val.detalle_comparables;
  if (val.metodo === "sin_comparables") return noDisponible("valoracion", titulo, "comparables: sin ellos no hay valoración de mercado", "m03_valoracion.py");
  if (!testigos?.length) return noDisponible("valoracion", titulo, "el detalle de los comparables usados", "m03_valoracion.py");
  const k = val.k_estado_activo;
  // `vs_capitalizacion` solo viaja cuando la capitalización fue vinculante (M03): entonces
  // VS NO es VS_m2 × m² y esa sustitución sería falsa.
  const capitalizacion = val.vs_capitalizacion;
  const vm = superficie && k != null ? `VM = ${eur(val.vs_m2)}/m² × ${num(k, 2)} × ${num(superficie, 2)} m²` : "";
  const vs = !superficie ? "" : capitalizacion != null
    ? `VS = capitalización ${eur(capitalizacion)} (menor que ${eur(val.vs_m2)}/m² × ${num(superficie, 2)} m²)`
    : `VS = ${eur(val.vs_m2)}/m² × ${num(superficie, 2)} m²`;
  return {
    clave: "valoracion", titulo, disponible: true, origen: "m03_valoracion.py",
    formula: capitalizacion != null
      ? "VS_m2 = mediana ponderada de los €/m² normalizados · VS = mín(VS_m2 × m², capitalización) · VM = VS_m2 × k_estado × m²"
      : "VS_m2 = mediana ponderada de los €/m² normalizados · VS = VS_m2 × m² · VM = VS_m2 × k_estado × m²",
    sustitucion: [vs, vm].filter(Boolean).join(" · ") || undefined,
    resultado: `VS_m2 ${eur(val.vs_m2)}/m² · VS ${eur(val.vs)} · VM ${eur(val.vm)}`,
    filas: testigos.map((t, i) => ({
      etiqueta: `Comparable ${i + 1}`,
      valor: `${eur(t.precio_ajustado_m2)}/m² ajustado → ${eur(t.normalizado_m2)}/m² normalizado · peso ${num(t.peso, 2)}`,
    })),
    nota: [
      `CV ${pct(val.dispersion_cv)}, confianza ${pct(val.confianza, 0)}.`,
      superficie ? "" : "La superficie no viaja en el resultado: la sustitución de VS y VM necesita la entrada del análisis.",
      capitalizacion != null ? `Perfil rentista: VS es el menor entre comparables y capitalización (${eur(capitalizacion)}).` : "",
    ].filter(Boolean).join(" "),
  };
}

/* ── escalera de precios: fórmula según el tramo fiscal ───────────────────── */

type Tramo = "unico" | "bajo" | "alto" | "frontera";
const hayBaseMinima = (c: Resultado["costes"]) => (c.base_fiscal_minima ?? 0) > 0 && (c.tipo_base_minima ?? 0) > 0;

/** Tramo con que se resolvió un precio; sin el dato (resultado anterior a la 5J-2a) solo
 * se sabe si no había base mínima (un solo tramo). `null` ⇒ no se puede sustituir. */
function tramoDe(res: Resultado, clave: string): Tramo | null {
  const t = res.decision.precios.tramos_fiscales?.[clave];
  if (t === "unico" || t === "bajo" || t === "alto" || t === "frontera") return t;
  return hayBaseMinima(res.costes) ? null : "unico";
}

/**
 * P = (A − fijos − extra) / (1 + c_v_ef), invertida por `fiscal.resolver_con_tramo`:
 *   · único / alto: extra 0 y c_v_ef = c_v;
 *   · bajo (la puja queda por debajo de la base mínima B): el impuesto de tipo t se paga
 *     sobre B, así que t sale de c_v y entra como fijo t·B;
 *   · frontera: P = B.
 */
function precio(res: Resultado, args: {
  clave: string; titulo: string; tramoClave: string; aSimbolo: string; aValor: string;
  fijos: "C_F P50" | "C_F P80"; resultado: string; nota?: string; origen: string;
}): Calculo {
  const c = res.costes;
  const tramo = tramoDe(res, args.tramoClave);
  if (tramo === null) return noDisponible(args.clave, args.titulo, `el tramo fiscal resuelto ${SIN_DATO_5J2A}`, args.origen);
  const fijos = args.fijos === "C_F P50" ? c.c_f_p50 : c.c_f_p80;
  const t = c.tipo_base_minima ?? 0, b = c.base_fiscal_minima ?? 0;
  const base = { clave: args.clave, titulo: args.titulo, disponible: true, origen: args.origen, resultado: args.resultado };
  if (tramo === "frontera") {
    return { ...base, formula: `${args.titulo} = B (frontera entre los dos tramos fiscales)`, sustitucion: `${args.titulo} = ${eur(b)}`,
             nota: args.nota };
  }
  const bajo = tramo === "bajo";
  return {
    ...base,
    formula: `${args.titulo} = (${args.aSimbolo} − ${args.fijos}${bajo ? " − t × B" : ""}) / (1 + c_v${bajo ? " − t" : ""})`,
    sustitucion: `${args.titulo} = (${args.aValor} − ${eur(fijos)}${bajo ? ` − ${num(t, 4)} × ${eur(b)}` : ""}) `
      + `/ (1 + ${num(c.c_v, 4)}${bajo ? ` − ${num(t, 4)}` : ""})`,
    nota: [args.nota, bajo ? `Tramo bajo: la puja queda por debajo de la base imponible mínima (B = ${eur(b)}), `
      + `así que el impuesto (t = ${pct(t, 2)}) se paga sobre B.` : "", REDONDEO].filter(Boolean).join(" "),
  };
}

export function calculosEscalera(res: Resultado): Calculo[] {
  const d = res.decision.precios.detalle ?? {};
  const origen = "m12_decision.py (calcular_escalera) y fiscal.py";
  const out = d.y_req_pct != null ? escaleraRentista(res, origen) : escaleraVenta(res, origen);
  out.push(calculoLimite(res, origen), ...calculosPuja(res));
  return out;
}

function escaleraVenta(res: Resultado, origen: string): Calculo[] {
  const d = res.decision.precios.detalle ?? {};
  const p = res.decision.precios;
  const vsp = eur(res.vs_prudente);
  const out: Calculo[] = [];
  out.push(d.m_excepcional_ajustado != null
    ? precio(res, { clave: "p_ideal", titulo: "P_ideal", tramoClave: "p_ideal", aSimbolo: "VS_p / (1 + m_excepcional)",
        aValor: `${vsp} / (1 + ${num(d.m_excepcional_ajustado, 4)})`, fijos: "C_F P50", resultado: eur(p.p_ideal), origen })
    : noDisponible("p_ideal", "P_ideal", `el margen excepcional ${SIN_DATO_5J2A}`, origen));
  out.push(d.m_objetivo_ajustado != null
    ? precio(res, { clave: "p_objetivo", titulo: "P_objetivo", tramoClave: "p_objetivo", aSimbolo: "VS_p / (1 + m_objetivo)",
        aValor: `${vsp} / (1 + ${num(d.m_objetivo_ajustado, 4)})`, fijos: "C_F P50", resultado: eur(p.p_objetivo), origen })
    : noDisponible("p_objetivo", "P_objetivo", "el margen objetivo ajustado", origen));
  if (d.p_por_margen_min == null || d.p_por_pesimista == null || d.m_minimo_ajustado == null) {
    out.push(noDisponible("p_max", "P_max", "P por margen mínimo y P por escenario pesimista", origen));
    return out;
  }
  out.push({
    clave: "p_max", titulo: "P_max", disponible: true, origen,
    formula: "P_max = mín(P por margen mínimo, P por escenario pesimista)",
    sustitucion: `P_max = mín(${eur(d.p_por_margen_min)}, ${eur(d.p_por_pesimista)})`,
    resultado: eur(p.p_max),
  });
  out.push(precio(res, { clave: "p_margen_min", titulo: "P por margen mínimo", tramoClave: "p_por_margen_min",
    aSimbolo: "VS_p / (1 + m_minimo)", aValor: `${vsp} / (1 + ${num(d.m_minimo_ajustado, 4)})`, fijos: "C_F P50",
    resultado: eur(d.p_por_margen_min), origen }));
  out.push(d.stress_mercado != null && d.piso_pesimista != null
    ? precio(res, { clave: "p_pesimista", titulo: "P por escenario pesimista", tramoClave: "p_por_pesimista",
        aSimbolo: "VS_pes / (1 + piso)", aValor: `${eur(d.vs_pesimista)} / (1 + ${num(d.piso_pesimista, 4)})`,
        fijos: "C_F P80", resultado: eur(d.p_por_pesimista), origen,
        nota: `VS_pes = VS_p × (1 − estrés) = ${vsp} × (1 − ${num(d.stress_mercado, 4)}) = ${eur(d.vs_pesimista)}.` })
    : noDisponible("p_pesimista", "P por escenario pesimista", `el estrés de mercado y el piso pesimista ${SIN_DATO_5J2A}`, origen));
  return out;
}

function escaleraRentista(res: Resultado, origen: string): Calculo[] {
  const d = res.decision.precios.detalle ?? {};
  const p = res.decision.precios;
  const rna = eur(d.rna);
  const porY = (clave: string, tramoClave: string, titulo: string, y: number, resultado: string): Calculo =>
    precio(res, { clave, titulo, tramoClave, aSimbolo: "RNA / y", aValor: `${rna} / ${pct(y / 100, 2)}`,
                  fijos: "C_F P50", resultado, origen,
                  nota: `y = rentabilidad exigida ${pct(d.y_req_pct / 100, 2)}${y === d.y_req_pct ? "" : ` + ${num(y - d.y_req_pct, 1)} puntos`}.` });
  const out = [
    porY("p_ideal", "p_ideal", "P_ideal", d.y_req_pct + 1, eur(p.p_ideal)),
    porY("p_objetivo", "p_objetivo", "P_objetivo", d.y_req_pct + 0.5, eur(p.p_objetivo)),
  ];
  const candidatos: [string, number | undefined][] = [
    ["por rentabilidad exigida", d.p_por_rentabilidad], ["por DSCR estresado", d.p_por_dscr],
    ["por cash-on-cash mínimo", d.p_por_cash_on_cash]];
  const presentes = candidatos.filter((c): c is [string, number] => c[1] != null);
  out.push(presentes.length ? {
    clave: "p_max", titulo: "P_max", disponible: true, origen,
    formula: "P_max = mín(P por rentabilidad exigida, P por DSCR estresado, P por cash-on-cash), los dos últimos solo con hipoteca",
    sustitucion: `P_max = mín(${presentes.map((c) => eur(c[1])).join(", ")})`,
    resultado: eur(p.p_max),
    filas: presentes.map(([etiqueta, v]) => ({ etiqueta: `P ${etiqueta}`, valor: eur(v) })),
  } : noDisponible("p_max", "P_max", `los candidatos del perfil rentista ${SIN_DATO_5J2A}`, origen));
  out.push(porY("p_rentabilidad", "p_por_rentabilidad", "P por rentabilidad exigida", d.y_req_pct, eur(d.p_por_rentabilidad)));
  return out;
}

function calculoLimite(res: Resultado, origen: string): Calculo {
  const d = res.decision.precios.detalle ?? {};
  const c = res.costes;
  const p = res.decision.precios;
  if (d.coste_capital == null || d.coste_capital_anual == null || d.capital_propio == null) {
    return noDisponible("p_limite", "P_limite", "el coste de capital y el capital propio (resultado anterior a la 5G.4)", origen);
  }
  const resultado = p.degenerada ? "No utilizable (escalera degenerada)" : eur(p.p_limite);
  const coste = `coste de capital = ${pct(d.coste_capital_anual, 2)} × ${eur(d.capital_propio)} × ${num(c.plazo_meses_p80, 1)} / 12 = ${eur(d.coste_capital)}`;
  const rentista = d.p_limite_rentista != null && d.p_limite_rentista > 0
    ? ` En el perfil rentista, P_limite = mín(el anterior, P por rentabilidad suelo = ${eur(d.p_limite_rentista)}).` : "";
  if (d.p_limite_bruto == null && hayBaseMinima(c)) {
    return noDisponible("p_limite", "P_limite", `el tramo fiscal resuelto ${SIN_DATO_5J2A}`, origen);
  }
  if (d.p_limite_bruto == null) {
    return { clave: "p_limite", titulo: "P_limite", disponible: true, origen, resultado,
      formula: "P_limite = (VS_p − C_F P80) / (1 + c_v) − coste de capital; coste de capital = tasa anual × capital propio × plazo P80 / 12",
      sustitucion: `P_limite = (${eur(res.vs_prudente)} − ${eur(c.c_f_p80)}) / (1 + ${num(c.c_v, 4)}) − ${eur(d.coste_capital)}; ${coste}`,
      nota: `${REDONDEO}${rentista}` };
  }
  const bruto = precio(res, { clave: "p_limite_bruto", titulo: "P_limite bruto", tramoClave: "p_limite", aSimbolo: "VS_p",
    aValor: eur(res.vs_prudente), fijos: "C_F P80", resultado: eur(d.p_limite_bruto), origen });
  return {
    clave: "p_limite", titulo: "P_limite", disponible: true, origen, resultado,
    formula: `P_limite = P_limite bruto − coste de capital; ${bruto.formula ?? "P_limite bruto"}`,
    sustitucion: `P_limite = ${eur(d.p_limite_bruto)} − ${eur(d.coste_capital)}; ${bruto.sustitucion ?? ""}; ${coste}`,
    nota: [bruto.nota, rentista.trim()].filter(Boolean).join(" "),
  };
}

function calculosPuja(res: Resultado): Calculo[] {
  const pu = res.puja;
  const p = res.decision.precios;
  const origen = "m13_puja.py";
  const vt = res.procedimiento?.valor_subasta;
  const padj: Calculo = pu.ratio_segmento != null && pu.ajustes_ratio ? {
    clave: "p_adj", titulo: "P_adj (precio de adjudicación esperado)", disponible: true, origen,
    formula: "ratio = ratio del segmento + ajustes, acotado entre 0,10 y 1,10; P_adj = valor de subasta × ratio",
    sustitucion: `ratio = ${num(pu.ratio_segmento, 3)}${pu.ajustes_ratio.map((a) => ` ${a.ajuste < 0 ? "−" : "+"} ${num(Math.abs(a.ajuste), 3)}`).join("")}`
      + `${pu.ratio_acotado ? " (acotado)" : ""} = ${num(pu.ratio_base, 3)}`
      + (vt != null ? `; P_adj = ${eur(vt)} × ${num(pu.ratio_base, 3)}` : ""),
    resultado: eur(res.decision.p_adj_esperado),
    filas: pu.ajustes_ratio.map((a) => ({ etiqueta: a.concepto, valor: `${a.ajuste < 0 ? "−" : "+"}${num(Math.abs(a.ajuste) * 100, 1)} puntos` })),
    nota: pu.ajustes_ratio.length ? undefined : "Sin ajustes: ni subastas previas desiertas ni valor de subasta inferior al 60 % del de mercado.",
  } : noDisponible("p_adj", "P_adj (precio de adjudicación esperado)", `los ajustes del ratio ${SIN_DATO_5J2A}`, origen);
  return [padj, {
    clave: "rvc", titulo: "RVC (viabilidad competitiva)", disponible: true, origen,
    formula: "RVC = P_max / P_adj",
    sustitucion: `RVC = ${eur(p.p_max)} / ${eur(res.decision.p_adj_esperado)}`,
    resultado: num(res.decision.rvc, 2),
  }];
}

/* ── métricas de decisión ─────────────────────────────────────────────────── */

export function calculosMetricas(res: Resultado): Calculo[] {
  const r = res.rentabilidad;
  const c = res.costes;
  const origen11 = "m11_rentabilidad.py";
  const bajoBase = hayBaseMinima(c) && r.precio_evaluado != null && r.precio_evaluado < (c.base_fiscal_minima ?? 0);
  return [
    {
      clave: "roi", titulo: "ROI (base)", disponible: true, origen: origen11,
      formula: "ROI = beneficio / inversión total, a P_objetivo",
      sustitucion: `ROI = ${eur(r.beneficio)} / ${eur(r.inversion_total)}`,
      resultado: pct(r.roi),
    },
    {
      clave: "inversion", titulo: "Inversión total a P_objetivo", disponible: true, origen: "fiscal.py (inversion)",
      // El motor evalúa en P_eval = máx(P_objetivo, 1) (pipeline.py), que viaja como `precio_evaluado`; por
      // debajo de la base mínima B suma el sobrecoste t × (B − P) del impuesto.
      formula: `I = P_eval × (1 + c_v) + C_F P50${bajoBase ? " + t × (B − P_eval)" : ""}, con P_eval = máx(P_objetivo, 1 €)`,
      sustitucion: r.precio_evaluado != null
        ? `I = ${eur(r.precio_evaluado)} × (1 + ${num(c.c_v, 4)}) + ${eur(c.c_f_p50)}`
          + (bajoBase ? ` + ${num(c.tipo_base_minima ?? 0, 4)} × (${eur(c.base_fiscal_minima ?? 0)} − ${eur(r.precio_evaluado)})` : "")
        : undefined,
      resultado: eur(r.inversion_total),
    },
    {
      clave: "margen", titulo: "Margen de seguridad", disponible: true, origen: "m12_decision.py (margen_seguridad)",
      formula: "MS_valor = máx(0, 1 − inversión total / VS)",
      sustitucion: `MS_valor = 1 − ${eur(r.inversion_total)} / ${eur(res.valoracion.vs)}`,
      resultado: pct(res.decision.margen_seguridad_valor),
    },
    calculoTir(res), calculoVan(res), calculoColchon(res),
  ];
}

const filasFlujos = (f: number[]): FilaCalculo[] =>
  f.map((x, t) => ({ etiqueta: t === 0 ? "Mes 0 (compra)" : t === f.length - 1 ? `Mes ${t} (venta)` : `Mes ${t}`, valor: eur(x) }));

function calculoTir(res: Resultado): Calculo {
  const r = res.rentabilidad;
  if (!r.flujos_base) return noDisponible("tir", "TIR anual", `los flujos con que se calcula ${SIN_DATO_5J2A}`, "m11_rentabilidad.py");
  return {
    clave: "tir", titulo: "TIR anual", disponible: true, origen: "m11_rentabilidad.py (_tir_anual)",
    formula: "Tasa mensual r tal que Σ F_t / (1 + r)^t = 0 (t = 0 … n meses, escenario base); TIR anual = (1 + r)^12 − 1",
    sustitucion: `F_t: ${r.flujos_base.length} flujos mensuales, del mes 0 al ${r.flujos_base.length - 1} (detalle abajo)`,
    resultado: pct(r.tir_anual),
    filas: filasFlujos(r.flujos_base),
  };
}

function calculoVan(res: Resultado): Calculo {
  const r = res.rentabilidad;
  if (!r.flujos_base || r.tasa_van == null || r.van_coste_capital == null) {
    return noDisponible("van", "VAN al coste de capital", `los flujos descontados ${SIN_DATO_5J2A}`, "m11_rentabilidad.py");
  }
  return {
    clave: "van", titulo: "VAN al coste de capital", disponible: true, origen: "m11_rentabilidad.py (_van)",
    formula: "VAN = Σ F_t / (1 + i)^t, con i = (1 + tasa anual)^(1/12) − 1 y los mismos flujos que la TIR",
    sustitucion: `tasa anual = ${pct(r.tasa_van, 2)}; F_t: los mismos flujos que la TIR, del mes 0 al ${r.flujos_base.length - 1}`,
    resultado: eur(r.van_coste_capital),
  };
}

function calculoColchon(res: Resultado): Calculo {
  const c = res.decision.colchon_detalle;
  if (res.decision.precios.degenerada) {
    return noDisponible("colchon", "Colchón de plazo", "un precio utilizable: con la escalera degenerada (§9.3) el motor no lo calcula", "m11_rentabilidad.py");
  }
  if (c && res.decision.colchon_plazo_meses == null) {
    return noDisponible("colchon", "Colchón de plazo", "un coste mensual que agote el beneficio: sin él el colchón no tiene límite", "m11_rentabilidad.py");
  }
  if (!c || res.decision.colchon_plazo_meses == null) {
    return noDisponible("colchon", "Colchón de plazo", `el beneficio de partida y el coste mensual ${SIN_DATO_5J2A}`, "m11_rentabilidad.py");
  }
  return {
    clave: "colchon", titulo: "Colchón de plazo (a P_objetivo)", disponible: true, origen: "m11_rentabilidad.py (colchon_plazo)",
    formula: "Colchón = máx(0, beneficio) / (tenencia + intereses + coste de capital), todo mensual; beneficio = VS_p − inversión total",
    sustitucion: `Colchón = ${eur(Math.max(0, c.beneficio))} / (${eur(c.tenencia_mensual)} + ${eur(c.intereses_mensuales)} + ${eur(c.coste_capital_mensual)})`,
    resultado: `${num(res.decision.colchon_plazo_meses, 1)} meses`,
  };
}

/* ── riesgos ──────────────────────────────────────────────────────────────── */

export function calculoRiesgos(riesgos: Resultado["riesgos"]): Calculo {
  const evidencias = (d: Resultado["riesgos"]["dimensiones"][number]) =>
    (d.evidencias_detalle ?? d.evidencias.map((e) => ({ dato: e, valor: null })))
      .map((e) => (e.valor == null ? etiquetaClave(e.dato) : `${etiquetaClave(e.dato)}: ${e.valor}`));
  const filas = riesgos.dimensiones.map((d) => ({
    etiqueta: humanizar(d.dimension),
    valor: `${d.probabilidad} × ${d.impacto} = ${d.score} (${d.nivel})`
      + (riesgos.pesos ? ` · peso ${num(riesgos.pesos[d.dimension] ?? 0, 2)}` : "")
      + (d.evidencias.length ? ` · evidencias: ${evidencias(d).join("; ")}` : ""),
  }));
  const base = {
    clave: "riesgos", titulo: "Riesgo por dimensión y riesgo agregado", disponible: true,
    origen: "m07-m10 y m12_decision.py (agregar_ra)", filas,
    resultado: `RA ${riesgos.ra} (base ${num(riesgos.ra_base, 2)}${riesgos.dominancia_aplicada ? `, dominancia ${riesgos.dominancia_aplicada}` : ""})`,
  };
  if (!riesgos.pesos) {
    return { ...base, formula: "Puntuación = probabilidad × impacto; nivel según los tramos T3",
             nota: `${NO_DISPONIBLE} para el RA: los pesos de agregación y el suelo por dominancia no viajan en este resultado ${SIN_DATO_5J2A}.` };
  }
  const terminos = riesgos.dimensiones.map((d) => `${num(riesgos.pesos![d.dimension] ?? 0, 2)} × ${d.score}`);
  return {
    ...base,
    formula: "RA base = Σ peso × (P × I) / 25 × 100; RA = máx(RA base, suelo de la dominancia), redondeado y como mucho 100",
    sustitucion: `RA base = (${terminos.join(" + ")}) / 25 × 100 = ${num(riesgos.ra_base, 2)}`
      + (riesgos.suelo_dominancia != null ? `; RA = máx(${num(riesgos.ra_base, 2)}, ${num(riesgos.suelo_dominancia, 0)})` : ""),
  };
}

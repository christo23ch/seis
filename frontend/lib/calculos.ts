/**
 * Fase 5K-D — «Ver cálculo»: fórmula, valores sustituidos y resultado de las métricas
 * cuyo desglose YA viaja en el resultado del motor.
 *
 * Reglas (no negociables):
 *   · El frontend NO recalcula: el resultado mostrado es siempre el del motor. Aquí
 *     solo se escribe la fórmula y se colocan en ella los valores que trae el resultado.
 *   · Cada fórmula reproduce el código del motor y se verificó con el caso §19
 *     (`tests/calculos.test.ts`); la referencia va en `origen`.
 *   · Si falta un dato, no se inventa: `disponible: false` con el dato que falta. La
 *     lista consolidada está en `docs/DEUDA_PRESENTACION_MOTOR.md`.
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
const sumaTexto = (valores: number[], fmt: (n: number) => string) => valores.map(fmt).join(" + ");

/* ── ICI ──────────────────────────────────────────────────────────────────── */

/** Penalización de un texto del motor «código (−N)»; `null` si no tiene ese formato. */
export function puntosPenalizacion(texto: string): number | null {
  const m = /\(−(\d+(?:[.,]\d+)?)\)\s*$/.exec(texto);
  return m ? Number(m[1].replace(",", ".")) : null;
}

export function calculoIci(ici: Resultado["ici"]): Calculo {
  const filas = Object.entries(ici.desglose).map(([k, v]) => ({ etiqueta: etiquetaClave(k), valor: `${num(v, 1)} puntos` }));
  const penal = ici.penalizaciones.map(puntosPenalizacion);
  if (penal.some((p) => p === null)) {
    return noDisponible("ici", "ICI", "el importe de alguna penalización no se puede leer de su texto", "m02_validacion.py");
  }
  const totalPenal = (penal as number[]).reduce((a, b) => a + b, 0);
  return {
    clave: "ici", titulo: "ICI (calidad de la información)", disponible: true, origen: "m02_validacion.py",
    formula: "ICI = Σ puntos de la documentación − penalizaciones, redondeado y entre 0 y 100",
    sustitucion: `ICI = (${sumaTexto(Object.values(ici.desglose), (n) => num(n, 1))}) − ${num(totalPenal, 1)}`,
    resultado: `${ici.ici} / 100`,
    filas: [...filas, ...ici.penalizaciones.map((p) => ({ etiqueta: "Penalización", valor: p }))],
    nota: ici.carencias.length ? `Carencias: ${ici.carencias.map((c) => IDENTIFICADORES[c] ?? c).join("; ")}.` : undefined,
  };
}

/* ── costes y reforma ─────────────────────────────────────────────────────── */

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
    nota: `Régimen fiscal: ${costes.regimen_fiscal.toUpperCase()}.`,
  };
}

export function calculoReforma(reforma: Resultado["reforma"]): Calculo {
  const partidas = reforma.partidas;
  if (!partidas) return noDisponible("reforma", "Reforma", "las partidas de la reforma", "m05_reforma.py");
  return {
    clave: "reforma", titulo: `Reforma (nivel ${reforma.nivel})`, disponible: true, origen: "m05_reforma.py",
    formula: "Reforma P50 = obra + técnicos y licencia + extras conocidos",
    sustitucion: `Reforma = ${sumaTexto(Object.values(partidas), eur)}`,
    resultado: `${eur(reforma.total_p50)} (P80: ${eur(reforma.total_p80)})`,
    filas: Object.entries(partidas).map(([k, v]) => ({ etiqueta: etiquetaClave(k), valor: eur(v) })),
  };
}

/* ── valoración (comparables) ─────────────────────────────────────────────── */

export function calculoValoracion(val: Resultado["valoracion"], superficie?: number | null): Calculo {
  const titulo = "Valoración por comparables";
  const testigos = val.detalle_comparables;
  if (val.metodo === "sin_comparables") return noDisponible("valoracion", titulo, "comparables: sin ellos no hay valoración de mercado", "m03_valoracion.py");
  if (!testigos?.length) return noDisponible("valoracion", titulo, "el detalle de los comparables usados", "m03_valoracion.py");
  const k = val.k_estado_activo;
  const capitalizacion = val.vs_capitalizacion;
  return {
    clave: "valoracion", titulo, disponible: true, origen: "m03_valoracion.py",
    formula: "VS_m2 = mediana ponderada de los €/m² normalizados · VS = VS_m2 × m² · VM = VS_m2 × k_estado × m²",
    sustitucion: superficie
      ? `VS = ${eur(val.vs_m2)}/m² × ${num(superficie, 2)} m²` + (k != null ? ` · VM = ${eur(val.vs_m2)}/m² × ${num(k, 2)} × ${num(superficie, 2)} m²` : "")
      : undefined,
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

/* ── escalera de precios ──────────────────────────────────────────────────── */

export function calculosEscalera(res: Resultado): Calculo[] {
  const d = res.decision.precios.detalle ?? {};
  const c = res.costes;
  const origen = "m12_decision.py (calcular_escalera) y fiscal.py";
  const pid = "P_ideal";
  if (d.y_req_pct != null) {
    return [noDisponible("escalera", "Escalera de precios (perfil rentista)",
      "los candidatos de P_max de la rama rentista (rentabilidad exigida, DSCR, cash-on-cash)", origen)];
  }
  const dosTramos = (c.base_fiscal_minima ?? 0) > 0 && (c.tipo_base_minima ?? 0) > 0;
  if (dosTramos) {
    return [noDisponible("escalera", "Escalera de precios",
      "el tramo fiscal resuelto: con base imponible mínima la fórmula tiene dos tramos y el resultado no dice cuál se usó", origen)];
  }
  const vsp = eur(res.vs_prudente), cf50 = eur(c.c_f_p50), cf80 = eur(c.c_f_p80), cv = num(c.c_v, 4);
  const p = res.decision.precios;
  const out: Calculo[] = [
    noDisponible("p_ideal", pid, "el margen excepcional (m_objetivo × m_exc_mult)", origen),
  ];
  out.push(d.m_objetivo_ajustado != null ? {
    clave: "p_objetivo", titulo: "P_objetivo", disponible: true, origen,
    formula: "P_objetivo = (VS_p / (1 + m_objetivo) − C_F P50) / (1 + c_v)",
    sustitucion: `P_objetivo = (${vsp} / (1 + ${num(d.m_objetivo_ajustado, 4)}) − ${cf50}) / (1 + ${cv})`,
    resultado: eur(p.p_objetivo),
  } : noDisponible("p_objetivo", "P_objetivo", "el margen objetivo ajustado", origen));
  out.push(d.p_por_margen_min != null && d.p_por_pesimista != null && d.m_minimo_ajustado != null ? {
    clave: "p_max", titulo: "P_max", disponible: true, origen,
    formula: "P_max = mín(P por margen mínimo, P por escenario pesimista); P por margen mínimo = (VS_p / (1 + m_minimo) − C_F P50) / (1 + c_v)",
    sustitucion: `P_max = mín(${eur(d.p_por_margen_min)}, ${eur(d.p_por_pesimista)}); `
      + `margen mínimo: (${vsp} / (1 + ${num(d.m_minimo_ajustado, 4)}) − ${cf50}) / (1 + ${cv})`,
    resultado: eur(p.p_max),
    nota: `El escenario pesimista parte de VS_pes = ${eur(d.vs_pesimista)}; su fórmula completa necesita el piso pesimista del perfil, que no viaja en el resultado.`,
  } : noDisponible("p_max", "P_max", "P por margen mínimo y P por escenario pesimista", origen));
  out.push(d.coste_capital != null && d.coste_capital_anual != null && d.capital_propio != null ? {
    clave: "p_limite", titulo: "P_limite", disponible: true, origen,
    formula: "P_limite = (VS_p − C_F P80) / (1 + c_v) − coste de capital; coste de capital = tasa anual × capital propio × plazo P80 / 12",
    sustitucion: `P_limite = (${vsp} − ${cf80}) / (1 + ${cv}) − ${eur(d.coste_capital)}; `
      + `coste de capital = ${pct(d.coste_capital_anual, 2)} × ${eur(d.capital_propio)} × ${num(c.plazo_meses_p80, 1)} / 12`,
    resultado: p.degenerada ? "No utilizable (escalera degenerada)" : eur(p.p_limite),
  } : noDisponible("p_limite", "P_limite", "el coste de capital y el capital propio (resultado anterior a la 5G.4)", origen));
  out.push({
    clave: "rvc", titulo: "RVC (viabilidad competitiva)", disponible: true, origen: "m13_puja.py",
    formula: "RVC = P_max / P_adj",
    sustitucion: `RVC = ${eur(p.p_max)} / ${eur(res.decision.p_adj_esperado)}`,
    resultado: num(res.decision.rvc, 2),
    nota: `P_adj = valor de subasta × ratio del segmento (${pct(res.puja.ratio_base, 0)}) con sus ajustes; los ajustes aplicados no viajan en el resultado.`,
  });
  return out;
}

/* ── métricas de decisión ─────────────────────────────────────────────────── */

export function calculosMetricas(res: Resultado): Calculo[] {
  const r = res.rentabilidad;
  const origen11 = "m11_rentabilidad.py";
  const dosTramos = (res.costes.base_fiscal_minima ?? 0) > 0 && (res.costes.tipo_base_minima ?? 0) > 0;
  return [
    {
      clave: "roi", titulo: "ROI (base)", disponible: true, origen: origen11,
      formula: "ROI = beneficio / inversión total, a P_objetivo",
      sustitucion: `ROI = ${eur(r.beneficio)} / ${eur(r.inversion_total)}`,
      resultado: pct(r.roi),
    },
    dosTramos ? noDisponible("inversion", "Inversión total", "el tramo fiscal resuelto (dos tramos)", "fiscal.py") : {
      clave: "inversion", titulo: "Inversión total a P_objetivo", disponible: true, origen: "fiscal.py (inversion)",
      formula: "I = P_objetivo × (1 + c_v) + C_F P50",
      sustitucion: `I = ${eur(res.decision.precios.p_objetivo)} × (1 + ${num(res.costes.c_v, 4)}) + ${eur(res.costes.c_f_p50)}`,
      resultado: eur(r.inversion_total),
    },
    {
      clave: "margen", titulo: "Margen de seguridad", disponible: true, origen: "m12_decision.py (margen_seguridad)",
      formula: "MS_valor = 1 − inversión total / VS",
      sustitucion: `MS_valor = 1 − ${eur(r.inversion_total)} / ${eur(res.valoracion.vs)}`,
      resultado: pct(res.decision.margen_seguridad_valor),
    },
    noDisponible("tir", "TIR anual", "los flujos y fechas con que se calcula", origen11),
    noDisponible("van", "VAN al coste de capital", "los flujos descontados", origen11),
    noDisponible("colchon", "Colchón de plazo", "el beneficio de partida y el coste mensual con que se divide", origen11),
  ];
}

/* ── riesgos ──────────────────────────────────────────────────────────────── */

export function calculoRiesgos(riesgos: Resultado["riesgos"]): Calculo {
  return {
    clave: "riesgos", titulo: "Riesgo por dimensión", disponible: true, origen: "m07-m10 y m12_decision.py (agregar_ra)",
    formula: "Puntuación = probabilidad × impacto; nivel según los tramos T3",
    filas: riesgos.dimensiones.map((d) => ({
      etiqueta: humanizar(d.dimension),
      valor: `${d.probabilidad} × ${d.impacto} = ${d.score} (${d.nivel})`
        + (d.evidencias.length ? ` · evidencias: ${d.evidencias.join("; ")}` : ""),
    })),
    resultado: `RA ${riesgos.ra} (base ${num(riesgos.ra_base, 2)}${riesgos.dominancia_aplicada ? `, dominancia ${riesgos.dominancia_aplicada}` : ""})`,
    nota: `${NO_DISPONIBLE} para el RA: los pesos de agregación y el suelo por dominancia son parámetros T3 que no viajan en el resultado.`,
  };
}

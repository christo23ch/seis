import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { calculoCf, calculoCv, calculoIci, calculoPlazo, calculoReforma, calculoRiesgos, calculoValoracion,
         calculosEscalera, calculosMetricas, puntosPenalizacion, type Calculo } from "@/lib/calculos";
import type { Resultado } from "@/lib/types";

/** Resultados REALES del motor (`tests/datos/LEEME.md`): §19, rentista con hipoteca y dos tramos fiscales. */
const leer = (n: string) => JSON.parse(readFileSync(join(__dirname, "datos", `resultado_${n}.json`), "utf-8")) as Resultado;
const RES = leer("caso19"), RENT = leer("rentista"), DOS = leer("dos_tramos");
const SUPERFICIE_19 = 82;
const por = (cs: Calculo[], clave: string) => cs.find((c) => c.clave === clave)!;
const npv = (f: number[], r: number) => f.reduce((s, x, t) => s + x / (1 + r) ** t, 0);

/* Las fórmulas mostradas deben ser las del motor: se recalculan AQUÍ (en el test, nunca
   en la app) con los valores que trae el resultado y se comparan con su cifra. */
describe("las fórmulas reproducen el resultado del motor (§19)", () => {
  const c = RES.costes, d = RES.decision.precios.detalle;

  it("C_F P50 y P80 = suma de partidas; c_v = suma de componentes; reforma = obra + técnicos", () => {
    const suma = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
    expect(suma(c.desglose_p50)).toBeCloseTo(c.c_f_p50, 2);
    expect(suma(c.desglose_p80!)).toBeCloseTo(c.c_f_p80, 2);
    expect(suma(c.c_v_desglose!)).toBeCloseTo(c.c_v, 6);
    expect(RES.reforma.partidas!.obra + RES.reforma.partidas!.tecnicos_licencia).toBeCloseTo(RES.reforma.total_p50, 2);
  });

  it("ICI = Σ puntos − penalizaciones", () => {
    expect(Math.round(Object.values(RES.ici.desglose).reduce((a, b) => a + b, 0))).toBe(RES.ici.ici);
  });

  it("VS = VS_m2 × m² y VM = VS_m2 × k_estado × m²", () => {
    expect(RES.valoracion.vs_m2 * SUPERFICIE_19).toBeCloseTo(RES.valoracion.vs, 0);
    expect(RES.valoracion.vs_m2 * RES.valoracion.k_estado_activo! * SUPERFICIE_19).toBeCloseTo(RES.valoracion.vm, 0);
  });

  it("P_ideal, P_objetivo y P por margen mínimo (un solo tramo)", () => {
    const p = (m: number) => (RES.vs_prudente / (1 + m) - c.c_f_p50) / (1 + c.c_v);
    expect(Math.abs(p(d.m_excepcional_ajustado) - RES.decision.precios.p_ideal)).toBeLessThan(1.5);   // VS_p redondeado
    expect(Math.abs(p(d.m_objetivo_ajustado) - RES.decision.precios.p_objetivo)).toBeLessThan(1.5);
    expect(Math.abs(p(d.m_minimo_ajustado) - d.p_por_margen_min)).toBeLessThan(1.5);
  });

  it("P pesimista con estrés y piso; P_max = mín de los dos", () => {
    expect(RES.vs_prudente * (1 - d.stress_mercado)).toBeCloseTo(d.vs_pesimista, -1);
    expect((d.vs_pesimista / (1 + d.piso_pesimista) - c.c_f_p80) / (1 + c.c_v)).toBeCloseTo(d.p_por_pesimista, 0);
    expect(Math.round(Math.min(d.p_por_margen_min, d.p_por_pesimista))).toBe(RES.decision.precios.p_max);
  });

  it("P_limite = P_limite bruto − coste de capital", () => {
    expect(Math.abs((RES.vs_prudente - c.c_f_p80) / (1 + c.c_v) - d.p_limite_bruto)).toBeLessThan(1.5);
    expect(d.coste_capital_anual * d.capital_propio * (c.plazo_meses_p80 / 12)).toBeCloseTo(d.coste_capital, 1);
    expect(Math.round(d.p_limite_bruto - d.coste_capital)).toBe(RES.decision.precios.p_limite);
  });

  it("P_adj con el ratio del segmento y sus ajustes; RVC", () => {
    const pu = RES.puja;
    const ratio = Math.max(0.1, Math.min(1.1, pu.ratio_segmento! + pu.ajustes_ratio!.reduce((s, a) => s + a.ajuste, 0)));
    expect(ratio).toBeCloseTo(pu.ratio_base, 3);
    expect(RES.procedimiento!.valor_subasta * pu.ratio_base).toBeCloseTo(RES.decision.p_adj_esperado, 0);
    expect(RES.decision.precios.p_max / RES.decision.p_adj_esperado).toBeCloseTo(RES.decision.rvc, 2);
  });

  it("RA base = Σ peso × P×I / 25 × 100; RA = máx(base, suelo)", () => {
    const ra = RES.riesgos;
    const base = ra.dimensiones.reduce((s, x) => s + ra.pesos![x.dimension] * x.score / 25 * 100, 0);
    expect(base).toBeCloseTo(ra.ra_base, 1);
    expect(Math.round(Math.min(100, Math.max(ra.ra_base, ra.suelo_dominancia ?? 0)))).toBe(ra.ra);
  });

  it("TIR y VAN con los flujos emitidos", () => {
    const r = RES.rentabilidad, f = r.flujos_base!;
    expect(Math.abs(npv(f, (1 + r.tir_anual) ** (1 / 12) - 1))).toBeLessThan(50);   // TIR redondeada a 4 decimales
    expect(npv(f, (1 + r.tasa_van!) ** (1 / 12) - 1)).toBeCloseTo(r.van_coste_capital!, 0);
  });

  it("colchón = máx(0, beneficio) / coste mensual; plazo = ocupación + obra + comercialización + inmovilización", () => {
    const k = RES.decision.colchon_detalle!;
    expect(Math.round(Math.max(0, k.beneficio) / (k.tenencia_mensual + k.intereses_mensuales + k.coste_capital_mensual) * 10) / 10)
      .toBe(RES.decision.colchon_plazo_meses);
    const pd = c.plazo_desglose!;
    // 5J-2b (ADR-0026): el cierre → pago del resto entra en el plazo; el P80 sale redondeado a un decimal.
    expect(pd.inmovilizacion).toBe(2.5);
    expect(pd.ocupacion + pd.obra + pd.comercializacion + pd.inmovilizacion!).toBe(c.plazo_meses_p50);
    expect(Math.round(c.plazo_meses_p50 * pd.multiplicador_p80 * 10) / 10).toBe(c.plazo_meses_p80);
  });

  it("ROI, inversión total y margen de seguridad", () => {
    const r = RES.rentabilidad;
    expect(r.beneficio / r.inversion_total).toBeCloseTo(r.roi, 3);
    expect(r.precio_evaluado! * (1 + c.c_v) + c.c_f_p50).toBeCloseTo(r.inversion_total, 0);
    expect(Math.max(0, 1 - r.inversion_total / RES.valoracion.vs)).toBeCloseTo(RES.decision.margen_seguridad_valor, 3);
  });
});

describe("las fórmulas reproducen el resultado del motor (dos tramos fiscales y perfil rentista)", () => {
  it("tramo bajo: P = (A − C_F − t·B) / (1 + c_v − t), e I suma t·(B − P)", () => {
    const c = DOS.costes, d = DOS.decision.precios.detalle, t = c.tipo_base_minima!, b = c.base_fiscal_minima!;
    expect(DOS.decision.precios.tramos_fiscales!.p_objetivo).toBe("bajo");
    const pObj = (DOS.vs_prudente / (1 + d.m_objetivo_ajustado) - c.c_f_p50 - t * b) / (1 + c.c_v - t);
    expect(Math.abs(pObj - DOS.decision.precios.p_objetivo)).toBeLessThan(1.5);
    const r = DOS.rentabilidad;
    expect(r.precio_evaluado! * (1 + c.c_v) + c.c_f_p50 + t * (b - r.precio_evaluado!)).toBeCloseTo(r.inversion_total, 0);
  });

  it("rentista: P = (RNA / y − C_F P50) / (1 + c_v) y P_max = mín de los candidatos", () => {
    const c = RENT.costes, d = RENT.decision.precios.detalle;
    const p = (y: number) => (d.rna / (y / 100) - c.c_f_p50) / (1 + c.c_v);
    expect(Math.abs(p(d.y_req_pct + 0.5) - RENT.decision.precios.p_objetivo)).toBeLessThan(1.5);
    expect(Math.abs(p(d.y_req_pct) - d.p_por_rentabilidad)).toBeLessThan(1.5);
    expect(Math.round(Math.min(d.p_por_rentabilidad, d.p_por_dscr, d.p_por_cash_on_cash))).toBe(RENT.decision.precios.p_max);
    const general = d.p_limite_bruto - d.coste_capital;
    expect(Math.round(Math.min(general, d.p_limite_rentista))).toBe(RENT.decision.precios.p_limite);
  });
});

describe("lo que muestra «Ver cálculo» (§19)", () => {
  it("C_F P50: fórmula, sustitución con las partidas y resultado del motor", () => {
    const cf = calculoCf(RES.costes, "p50");
    expect(cf.disponible).toBe(true);
    expect(cf.sustitucion).toMatch(/^C_F = 50\.053\s€ \+ 6\.500\s€ \+/);
    expect(cf.resultado).toMatch(/^78\.144\s€$/);
    expect(cf.filas!.map((f) => f.etiqueta)).toContain("Ocupación y desalojo");
  });

  it("c_v, reforma y plazo", () => {
    expect(calculoCv(RES.costes)).toMatchObject({ sustitucion: "c_v = 6,00 % + 0,40 %" });
    expect(calculoReforma(RES.reforma).resultado).toMatch(/^50\.053\s€ \(P80: 61\.064\s€\)$/);
    expect(calculoPlazo(RES.costes)).toMatchObject({ disponible: true, sustitucion: "P50 = 7 + 3 + 3 + 2,5; P80 = 15,5 × 1,4" });
    expect(calculoPlazo(RES.costes).formula).toContain("+ meses de inmovilización (cierre → pago del resto)");
  });

  it("ICI con sus carencias legibles", () => {
    const ici = calculoIci(RES.ici);
    expect(ici.resultado).toBe("63 / 100");
    expect(ici.nota).toContain("posesión verificada");
  });

  it("valoración: con superficie sustituye VS y VM; sin ella lo dice", () => {
    expect(calculoValoracion(RES.valoracion, SUPERFICIE_19).sustitucion).toMatch(/× 82 m²/);
    expect(calculoValoracion(RES.valoracion, null).nota).toContain("La superficie no viaja en el resultado");
  });

  it("escalera: todo disponible, P_ideal incluido, con su tramo y sus operandos", () => {
    const e = calculosEscalera(RES);
    for (const c of e) expect(c.disponible, c.clave).toBe(true);
    expect(por(e, "p_ideal").sustitucion).toContain("(1 + 0,3375)");
    // 5J-2b (ADR-0026): el plazo suma la inmovilización ⇒ más C_F y más coste de capital.
    expect(por(e, "p_max").sustitucion).toMatch(/^P_max = mín\(68\.533\s€, 67\.941\s€\)$/);
    expect(por(e, "p_pesimista").nota).toContain("VS_pes = VS_p × (1 − estrés)");
    expect(por(e, "p_limite").sustitucion).toMatch(/^P_limite = 82\.892\s€ − 4\.363\s€;/);
    expect(por(e, "p_adj").sustitucion).toMatch(/^ratio = 0,42 = 0,42; P_adj = 152\.000\s€ × 0,42$/);
    expect(por(e, "rvc").resultado).toBe("1,06");
  });

  it("métricas: TIR, VAN y colchón ya disponibles", () => {
    const m = calculosMetricas(RES);
    for (const c of m) expect(c.disponible, c.clave).toBe(true);
    expect(por(m, "tir").filas![0].etiqueta).toBe("Mes 0 (compra)");
    expect(por(m, "van").sustitucion).toContain("1,50 %");
    expect(por(m, "colchon").resultado).toBe("84,8 meses");
  });

  it("riesgos: pesos, P × I y evidencias estructuradas; RA con su suelo", () => {
    const r = calculoRiesgos(RES.riesgos);
    expect(r.filas!.find((f) => f.etiqueta === "Documental")!.valor).toBe("2 × 3 = 6 (medio) · peso 0,08 · evidencias: ICI: 63");
    expect(r.sustitucion).toMatch(/; RA = máx\(25,36, 40\)$/);
  });

  it("dos tramos y rentista: la escalera se sustituye con la fórmula de su tramo", () => {
    const dos = calculosEscalera(DOS);
    expect(por(dos, "p_objetivo").formula).toBe("P_objetivo = (VS_p / (1 + m_objetivo) − C_F P50 − t × B) / (1 + c_v − t)");
    expect(por(dos, "p_objetivo").nota).toContain("Tramo bajo");
    const rent = calculosEscalera(RENT);
    expect(por(rent, "p_max").filas!.map((f) => f.etiqueta)).toEqual(
      ["P por rentabilidad exigida", "P por DSCR estresado", "P por cash-on-cash mínimo"]);
    expect(por(rent, "p_objetivo").formula).toBe("P_objetivo = (RNA / y − C_F P50) / (1 + c_v)");
  });
});

describe("resultados anteriores a la 5J-2a: nunca se inventa", () => {
  const viejo = (r: Resultado): Resultado => ({
    ...r,
    decision: { ...r.decision, colchon_detalle: undefined,
      precios: { ...r.decision.precios, tramos_fiscales: undefined, detalle: Object.fromEntries(
        Object.entries(r.decision.precios.detalle).filter(([k]) => !["m_excepcional_ajustado", "stress_mercado",
          "piso_pesimista", "p_limite_bruto"].includes(k))) } },
    riesgos: { ...r.riesgos, pesos: undefined, suelo_dominancia: undefined },
    puja: { ...r.puja, ratio_segmento: undefined, ajustes_ratio: undefined },
    rentabilidad: { ...r.rentabilidad, flujos_base: undefined, tasa_van: undefined },
    costes: { ...r.costes, plazo_desglose: undefined },
  });

  it("§19 antiguo: lo nuevo dice «no disponible» y lo de antes sigue igual", () => {
    const e = calculosEscalera(viejo(RES)), m = calculosMetricas(viejo(RES));
    for (const k of ["p_ideal", "p_pesimista", "p_adj"]) expect(por(e, k).disponible, k).toBe(false);
    for (const k of ["p_objetivo", "p_max", "p_limite", "rvc"]) expect(por(e, k).disponible, k).toBe(true);
    for (const k of ["tir", "van", "colchon"]) expect(por(m, k).disponible, k).toBe(false);
    expect(calculoPlazo(viejo(RES).costes).disponible).toBe(false);
    expect(calculoRiesgos(viejo(RES).riesgos).nota).toContain("Cálculo no disponible aún para el RA");
  });

  it("un resultado de la 5J-2a, sin la inmovilización, se explica con la fórmula de entonces", () => {
    const { inmovilizacion: _, ...pd } = RES.costes.plazo_desglose!;
    const c = calculoPlazo({ ...RES.costes, plazo_meses_p50: 13, plazo_meses_p80: 18.2, plazo_desglose: pd });
    expect(c.sustitucion).toBe("P50 = 7 + 3 + 3; P80 = 13 × 1,4");
    expect(c.formula).not.toContain("inmovilización");
    expect(c.nota).toBeUndefined();
  });

  it("dos tramos sin el tramo resuelto ⇒ no se sustituye ningún precio, P_limite tampoco", () => {
    const e = calculosEscalera(viejo(DOS));
    for (const k of ["p_objetivo", "p_margen_min", "p_limite"]) expect(por(e, k).disponible, k).toBe(false);
  });

  it("colchón con escalera degenerada: dice por qué no hay cálculo, no «resultado anterior»", () => {
    const deg = { ...RES, decision: { ...RES.decision, colchon_detalle: null, colchon_plazo_meses: null,
                                      precios: { ...RES.decision.precios, degenerada: true } } } as Resultado;
    const c = por(calculosMetricas(deg), "colchon");
    expect(c.disponible).toBe(false);
    expect(c.falta).toContain("escalera degenerada");
  });

  it("lee el importe de una penalización del texto del motor", () => {
    expect(puntosPenalizacion("superficie_inconsistente (−10)")).toBe(10);
    expect(puntosPenalizacion("sin formato")).toBeNull();
  });
});

describe("correcciones de la revisión de código (5K)", () => {
  it("reforma con extras: la obra ya los incluye y no se suman dos veces (M05)", () => {
    const reforma = { ...RES.reforma, total_p50: 55502.8,
      partidas: { obra: 50920, tecnicos_licencia: 4582.8, extras_conocidos: 5000 } };
    const c = calculoReforma(reforma);
    expect(c.sustitucion).toMatch(/^Reforma = 50\.920\s€ \+ 4\.583\s€$/);
    expect(c.filas!.map((f) => f.etiqueta)).toEqual(["Obra", "de ello, extras conocidos", "Técnicos y licencia"]);
  });

  it("valoración con capitalización vinculante: VS no se presenta como VS_m2 × m²", () => {
    const c = calculoValoracion({ ...RES.valoracion, vs: 150000, vs_capitalizacion: 150000 }, SUPERFICIE_19);
    expect(c.formula).toContain("mín(VS_m2 × m², capitalización)");
    expect(c.sustitucion).toMatch(/^VS = capitalización 150\.000\s€ \(menor que/);
  });

  it("inversión total con P_eval y margen de seguridad acotado a 0", () => {
    const m = calculosMetricas(RES);
    expect(por(m, "inversion").formula).toContain("P_eval = máx(P_objetivo, 1 €)");
    expect(por(m, "margen").formula).toBe("MS_valor = máx(0, 1 − inversión total / VS)");
  });
});

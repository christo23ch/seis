import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { calculoCf, calculoCv, calculoIci, calculoReforma, calculoRiesgos, calculoValoracion, calculosEscalera,
         calculosMetricas, puntosPenalizacion, type Calculo } from "@/lib/calculos";
import type { Resultado } from "@/lib/types";

/** Resultado REAL del caso §19 (`tests/datos/LEEME.md`). */
const RES = JSON.parse(readFileSync(join(__dirname, "datos", "resultado_caso19.json"), "utf-8")) as Resultado;
const SUPERFICIE_19 = 82;
const por = (cs: Calculo[], clave: string) => cs.find((c) => c.clave === clave)!;

/* Las fórmulas mostradas deben ser las del motor: se recalculan AQUÍ (en el test, nunca
   en la app) con los valores que trae el resultado y se comparan con su cifra. */
describe("las fórmulas reproducen el resultado del motor (§19)", () => {
  const c = RES.costes, d = RES.decision.precios.detalle;

  it("C_F P50 y P80 = suma de partidas; c_v = suma de componentes", () => {
    const suma = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
    expect(suma(c.desglose_p50)).toBeCloseTo(c.c_f_p50, 2);
    expect(suma(c.desglose_p80!)).toBeCloseTo(c.c_f_p80, 2);
    expect(suma(c.c_v_desglose!)).toBeCloseTo(c.c_v, 6);
    expect(suma(RES.reforma.partidas!)).toBeCloseTo(RES.reforma.total_p50, 2);
  });

  it("ICI = Σ puntos − penalizaciones", () => {
    expect(Math.round(Object.values(RES.ici.desglose).reduce((a, b) => a + b, 0))).toBe(RES.ici.ici);
  });

  it("VS = VS_m2 × m² y VM = VS_m2 × k_estado × m²", () => {
    expect(RES.valoracion.vs_m2 * SUPERFICIE_19).toBeCloseTo(RES.valoracion.vs, 0);
    expect(RES.valoracion.vs_m2 * RES.valoracion.k_estado_activo! * SUPERFICIE_19).toBeCloseTo(RES.valoracion.vm, 0);
  });

  it("P_objetivo, P por margen mínimo, P_max, P_limite y coste de capital (un solo tramo fiscal)", () => {
    const pObj = (RES.vs_prudente / (1 + d.m_objetivo_ajustado) - c.c_f_p50) / (1 + c.c_v);
    const pMin = (RES.vs_prudente / (1 + d.m_minimo_ajustado) - c.c_f_p50) / (1 + c.c_v);
    const cc = d.coste_capital_anual * d.capital_propio * (c.plazo_meses_p80 / 12);
    const pLim = (RES.vs_prudente - c.c_f_p80) / (1 + c.c_v) - d.coste_capital;
    expect(Math.abs(pObj - RES.decision.precios.p_objetivo)).toBeLessThan(1.5);   // VS_p viaja redondeado
    expect(Math.abs(pMin - d.p_por_margen_min)).toBeLessThan(1.5);
    expect(Math.min(d.p_por_margen_min, d.p_por_pesimista)).toBeCloseTo(RES.decision.precios.p_max, -1);
    expect(cc).toBeCloseTo(d.coste_capital, 1);
    expect(Math.abs(pLim - RES.decision.precios.p_limite)).toBeLessThan(1.5);
  });

  it("RVC, ROI, inversión total y margen de seguridad", () => {
    const r = RES.rentabilidad;
    expect(RES.decision.precios.p_max / RES.decision.p_adj_esperado).toBeCloseTo(RES.decision.rvc, 2);
    expect(r.beneficio / r.inversion_total).toBeCloseTo(r.roi, 3);
    expect(RES.decision.precios.p_objetivo * (1 + c.c_v) + c.c_f_p50).toBeCloseTo(r.inversion_total, 0);
    expect(1 - r.inversion_total / RES.valoracion.vs).toBeCloseTo(RES.decision.margen_seguridad_valor, 3);
  });
});

describe("lo que muestra «Ver cálculo» (§19)", () => {
  it("C_F P50: fórmula, sustitución con las partidas y resultado del motor", () => {
    const cf = calculoCf(RES.costes, "p50");
    expect(cf.disponible).toBe(true);
    expect(cf.sustitucion).toMatch(/^C_F = 50\.053\s€ \+ 6\.500\s€ \+/);
    expect(cf.resultado).toMatch(/^77\.544\s€$/);
    expect(cf.filas!.map((f) => f.etiqueta)).toContain("Ocupación y desalojo");
  });

  it("c_v y reforma", () => {
    expect(calculoCv(RES.costes)).toMatchObject({ sustitucion: "c_v = 6,00 % + 0,40 %", resultado: "6,40 %" });
    expect(calculoReforma(RES.reforma).resultado).toMatch(/^50\.053\s€ \(P80: 61\.064\s€\)$/);
  });

  it("ICI con sus carencias legibles", () => {
    const ici = calculoIci(RES.ici);
    expect(ici.resultado).toBe("63 / 100");
    expect(ici.nota).toContain("posesión verificada");
  });

  it("valoración: con superficie sustituye VS y VM; sin ella lo dice", () => {
    expect(calculoValoracion(RES.valoracion, SUPERFICIE_19).sustitucion).toMatch(/× 82 m²/);
    const sin = calculoValoracion(RES.valoracion, null);
    expect(sin.sustitucion).toBeUndefined();
    expect(sin.nota).toContain("La superficie no viaja en el resultado");
    expect(calculoValoracion(RES.valoracion).filas).toHaveLength(7);
  });

  it("escalera: P_ideal no disponible (falta su margen); el resto con sustitución", () => {
    const e = calculosEscalera(RES);
    expect(por(e, "p_ideal")).toMatchObject({ disponible: false });
    expect(por(e, "p_ideal").falta).toContain("m_exc_mult");
    expect(por(e, "p_objetivo").sustitucion).toContain("0,25");
    expect(por(e, "p_max").sustitucion).toMatch(/^P_max = mín\(69\.097\s€, 68\.731\s€\)/);
    expect(por(e, "p_limite").sustitucion).toContain("1,50 % × 160.837");
    expect(por(e, "rvc").resultado).toBe("1,08");
  });

  it("métricas: ROI, inversión y margen disponibles; TIR, VAN y colchón no", () => {
    const m = calculosMetricas(RES);
    expect(por(m, "roi").resultado).toBe("25,0 %");
    expect(por(m, "margen").resultado).toBe("24,8 %");
    for (const k of ["tir", "van", "colchon"]) expect(por(m, k).disponible).toBe(false);
  });

  it("riesgos: P × I por dimensión con evidencias; el RA declara lo que falta", () => {
    const r = calculoRiesgos(RES.riesgos);
    expect(r.filas!.find((f) => f.etiqueta === "Documental")!.valor).toBe("2 × 3 = 6 (medio) · evidencias: ICI=63");
    expect(r.nota).toContain("Cálculo no disponible aún para el RA");
  });
});

describe("datos ausentes: nunca se inventa", () => {
  it("resultado antiguo sin desgloses ⇒ no disponible, nombrando lo que falta", () => {
    const viejo = { ...RES, costes: { ...RES.costes, c_v_desglose: undefined, desglose_p80: undefined },
                    reforma: { ...RES.reforma, partidas: undefined } } as Resultado;
    expect(calculoCv(viejo.costes)).toMatchObject({ disponible: false, falta: "el desglose de c_v" });
    expect(calculoCf(viejo.costes, "p80").disponible).toBe(false);
    expect(calculoReforma(viejo.reforma).disponible).toBe(false);
  });

  it("con base imponible mínima (dos tramos) la escalera no se sustituye", () => {
    const dos = { ...RES, costes: { ...RES.costes, base_fiscal_minima: 100000, tipo_base_minima: 0.06 } } as Resultado;
    expect(calculosEscalera(dos)).toEqual([expect.objectContaining({ disponible: false })]);
  });

  it("perfil rentista: la escalera no se sustituye", () => {
    const rent = { ...RES, decision: { ...RES.decision, precios: { ...RES.decision.precios,
      detalle: { ...RES.decision.precios.detalle, y_req_pct: 7 } } } } as Resultado;
    expect(calculosEscalera(rent)[0]).toMatchObject({ disponible: false });
  });

  it("lee el importe de una penalización del texto del motor", () => {
    expect(puntosPenalizacion("superficie_inconsistente (−10)")).toBe(10);
    expect(puntosPenalizacion("sin formato")).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import { MENSAJES, esquemaAnalisis, prepararEnvio, valoresIniciales, type EntradaFormulario } from "@/lib/schema";

/** Valores iniciales con SOLO los obligatorios rellenados, como los escribe una persona. */
function soloObligatorios(): EntradaFormulario {
  const v = structuredClone(valoresIniciales);
  return {
    ...v,
    subasta: { ...v.subasta, valor_subasta: "152.000" },
    activo: { ...v.activo, superficie_m2: "82,5", municipio: "Madrid" },
    comparables: [{ ...v.comparables[0], precio_m2: "2.293" }],
  };
}

/** Todas las hojas del objeto, con su ruta, para buscar valores prohibidos. */
function hojas(nodo: unknown, ruta = ""): [string, unknown][] {
  if (nodo !== null && typeof nodo === "object") {
    return Object.entries(nodo).flatMap(([k, v]) => hojas(v, ruta ? `${ruta}.${k}` : k));
  }
  return [[ruta, nodo]];
}

describe("prepararEnvio: alta con solo los obligatorios", () => {
  it("valida y no envía ninguna cadena vacía (causa del 422 de la prueba manual)", () => {
    const r = esquemaAnalisis.safeParse(soloObligatorios());
    expect(r.success).toBe(true);
    const cuerpo = prepararEnvio(r.data!);
    const vacias = hojas(cuerpo).filter(([, v]) => v === "" || v === null || Number.isNaN(v));
    expect(vacias).toEqual([]);
  });

  it("convierte a número con coma decimal y punto de miles", () => {
    const cuerpo = prepararEnvio(esquemaAnalisis.parse(soloObligatorios())) as any;
    expect(cuerpo.subasta.valor_subasta).toBe(152000);
    expect(cuerpo.activo.superficie_m2).toBe(82.5);
    expect(cuerpo.comparables[0].precio_m2).toBe(2293);
  });

  it("omite los opcionales vacíos en lugar de enviarlos", () => {
    const cuerpo = prepararEnvio(esquemaAnalisis.parse(soloObligatorios())) as any;
    for (const ruta of ["activo.anio_construccion", "activo.lat", "activo.lng", "subasta.puja_minima",
      "subasta.horas_hasta_cierre", "zona.precio_m2_p85", "reforma.coste_m2_override",
      "costes.valor_referencia_catastral", "costes.valor_declarado", "costes.atrasos_comunidad_ibi",
      "costes.adquisicion_fija_override", "costes.tenencia_mensual", "costes.itp_tipo_override",
      "reforma.nivel_override", "ocupacion.renta_mensual"]) {
      const [grupo, campo] = ruta.split(".");
      expect(cuerpo[grupo], ruta).toBeDefined();
      expect(campo in cuerpo[grupo], ruta).toBe(false);
    }
  });

  it("pasa los porcentajes a fracción y respeta el porcentaje vacío", () => {
    const v = soloObligatorios();
    const cuerpo = prepararEnvio(esquemaAnalisis.parse(v)) as any;
    expect(cuerpo.subasta.deposito_pct).toBeCloseTo(0.05);
    const sinDeposito = prepararEnvio(esquemaAnalisis.parse({ ...v, subasta: { ...v.subasta, deposito_pct: "" } })) as any;
    expect("deposito_pct" in sinDeposito.subasta).toBe(false);
  });

  it("omite las cargas con importe indeterminado sin romper la carga", () => {
    const v = soloObligatorios();
    v.cargas = [{ tipo: "embargo", importe: "", es_anterior: true, se_purga: false, verificada: false,
                  prohibicion_disponer: false, condicion_resolutoria: false }];
    const cuerpo = prepararEnvio(esquemaAnalisis.parse(v)) as any;
    expect(cuerpo.cargas).toHaveLength(1);
    expect("importe" in cuerpo.cargas[0]).toBe(false);
    expect(cuerpo.cargas[0].es_anterior).toBe(true);
  });
});

describe("esquemaAnalisis: mensajes en español", () => {
  const errores = (v: EntradaFormulario) => {
    const r = esquemaAnalisis.safeParse(v);
    return r.success ? {} : Object.fromEntries(r.error.issues.map((i) => [i.path.join("."), i.message]));
  };

  it("marca como obligatorios los que faltan", () => {
    const e = errores(valoresIniciales);
    expect(e["subasta.valor_subasta"]).toBe(MENSAJES.obligatorio);
    expect(e["activo.superficie_m2"]).toBe(MENSAJES.obligatorio);
    expect(e["activo.municipio"]).toBe(MENSAJES.obligatorio);
    expect(e["comparables.0.precio_m2"]).toBe(MENSAJES.obligatorio);
  });

  it("rechaza texto que no es un número", () => {
    const v = soloObligatorios();
    expect(errores({ ...v, activo: { ...v.activo, anio_construccion: "hace mucho" } })["activo.anio_construccion"])
      .toBe(MENSAJES.numero);
  });

  it("en tasas y coeficientes el punto es decimal: «3.500» de interés es 3,5", () => {
    const v = soloObligatorios();
    const r = esquemaAnalisis.parse({ ...v, financiacion: { ...v.financiacion, interes_anual_pct: "3.500" },
                                      reforma: { ...v.reforma, k_provincia: "1.050" } });
    expect(r.financiacion.interes_anual_pct).toBe(3.5);
    expect(r.reforma.k_provincia).toBe(1.05);
  });

  it("rechaza la antigüedad negativa de un comparable (punto 3 de la prueba manual)", () => {
    const v = soloObligatorios();
    v.comparables = [{ ...v.comparables[0], meses_antiguedad: "-1" }];
    expect(errores(v)["comparables.0.meses_antiguedad"]).toBe(MENSAJES.noNegativo);
  });
});

import { describe, expect, it } from "vitest";
import { MENSAJES, depositoFraccion, descartarOcultos, esquemaAnalisis, estaOculta, rutasOcultas, prepararEnvio, valoresIniciales, type EntradaFormulario } from "@/lib/schema";

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

describe("depósito como importe o porcentaje (5I-C)", () => {
  const conDeposito = (subasta: Partial<EntradaFormulario["subasta"]>) => {
    const v = soloObligatorios();
    return { ...v, subasta: { ...v.subasta, ...subasta } };
  };

  it("convierte el importe a fracción del valor de subasta en un solo sitio", () => {
    expect(depositoFraccion({ deposito_modo: "importe", deposito_importe: 7600, deposito_pct: undefined, valor_subasta: 152000 }))
      .toBeCloseTo(0.05, 12);
    expect(depositoFraccion({ deposito_modo: "porcentaje", deposito_importe: 7600, deposito_pct: 3, valor_subasta: 152000 }))
      .toBeCloseTo(0.03, 12);
    expect(depositoFraccion({ deposito_modo: "importe", deposito_importe: undefined, deposito_pct: 5, valor_subasta: 152000 }))
      .toBeUndefined();
  });

  it("con importe envía deposito_pct (lo que lee el motor) y el importe escrito", () => {
    const cuerpo = prepararEnvio(esquemaAnalisis.parse(conDeposito({ deposito_modo: "importe", deposito_importe: "7.600" }))) as any;
    expect(cuerpo.subasta.deposito_pct).toBeCloseTo(0.05, 12);
    expect(cuerpo.subasta.deposito_importe).toBe(7600);
    expect("deposito_modo" in cuerpo.subasta).toBe(false);
  });

  it("con porcentaje no envía importe aunque quedara uno escrito", () => {
    const cuerpo = prepararEnvio(esquemaAnalisis.parse(conDeposito({ deposito_modo: "porcentaje", deposito_importe: "7.600" }))) as any;
    expect(cuerpo.subasta.deposito_pct).toBeCloseTo(0.05, 12);
    expect("deposito_importe" in cuerpo.subasta).toBe(false);
  });

  it("valida el importe: obligatorio en ese modo, mayor que cero y no mayor que el valor de subasta", () => {
    const err = (s: Partial<EntradaFormulario["subasta"]>) => {
      const r = esquemaAnalisis.safeParse(conDeposito(s));
      return r.success ? undefined : r.error.issues.find((i) => i.path.join(".") === "subasta.deposito_importe")?.message;
    };
    expect(err({ deposito_modo: "importe", deposito_importe: "" })).toBe(MENSAJES.obligatorio);
    expect(err({ deposito_modo: "importe", deposito_importe: "0" })).toBe(MENSAJES.positivo);
    expect(err({ deposito_modo: "importe", deposito_importe: "152.001" })).toBe("No puede superar el valor de subasta");
    expect(err({ deposito_modo: "importe", deposito_importe: "152.000" })).toBeUndefined();
    expect(err({ deposito_modo: "porcentaje", deposito_importe: "" })).toBeUndefined();
  });
});

describe("descartarOcultos: lo que no se ve no se valida ni se envía, y lo que se ve se conserva", () => {
  it("vacía los campos cuya condición no se cumple", () => {
    const v = soloObligatorios();
    const r = descartarOcultos({
      ...v,
      activo: { ...v.activo, vpo: false, vpo_precio_max_legal: "abc" },
      ocupacion: { estado: "vacio", renta_mensual: "-5" },
      financiacion: { ...v.financiacion, tipo: "cash", ltv: "xx" },
      documentos: { ...v.documentos, nota_simple: false, nota_simple_dias: "zz" },
      subasta: { ...v.subasta, deposito_modo: "porcentaje", deposito_importe: "0" },
    });
    expect(r.activo.vpo_precio_max_legal).toBe("");
    expect(r.ocupacion.renta_mensual).toBe("");
    expect(r.financiacion.ltv).toBe("");
    expect(r.documentos.nota_simple_dias).toBe("");
    expect(r.subasta.deposito_importe).toBe("");
    expect(r.rentista).toBeUndefined();                  // perfil no rentista
    expect(esquemaAnalisis.safeParse(r).success).toBe(true);
  });

  it("conserva los campos visibles aunque su paso no esté en pantalla", () => {
    const v = soloObligatorios();
    const r = descartarOcultos({
      ...v,
      perfil: "rentista",
      activo: { ...v.activo, vpo: true, vpo_precio_max_legal: "90.000" },
      ocupacion: { estado: "arrendado_anterior", renta_mensual: "650" },
      financiacion: { ...v.financiacion, tipo: "hipoteca", ltv: "70", interes_anual_pct: "3,2" },
      documentos: { ...v.documentos, nota_simple: true, nota_simple_dias: "3" },
      subasta: { ...v.subasta, deposito_modo: "importe", deposito_importe: "7.600" },
      rentista: { ...v.rentista!, renta_mensual_estimada: "900" },
    });
    const cuerpo = prepararEnvio(esquemaAnalisis.parse(r)) as any;
    expect(cuerpo.activo.vpo_precio_max_legal).toBe(90000);
    expect(cuerpo.ocupacion.renta_mensual).toBe(650);
    expect(cuerpo.financiacion.ltv).toBeCloseTo(0.7);
    expect(cuerpo.financiacion.interes_anual_pct).toBe(3.2);
    expect(cuerpo.documentos.nota_simple_dias).toBe(3);
    expect(cuerpo.subasta.deposito_importe).toBe(7600);
    expect(cuerpo.rentista.renta_mensual_estimada).toBe(900);
  });
});

describe("rutasOcultas: única fuente de los campos ocultos por su condición", () => {
  it("lista exactamente lo que descartarOcultos vacía", () => {
    const v = soloObligatorios();
    expect(rutasOcultas(v).sort()).toEqual([
      "activo.vpo_precio_max_legal", "documentos.nota_simple_dias", "financiacion.interes_anual_pct",
      "financiacion.ltv", "ocupacion.renta_mensual", "rentista", "subasta.deposito_importe",
    ]);
    const visibles = { ...v, perfil: "rentista", subasta: { ...v.subasta, deposito_modo: "importe" as const },
                       activo: { ...v.activo, vpo: true }, ocupacion: { ...v.ocupacion, estado: "renta_antigua" },
                       financiacion: { ...v.financiacion, tipo: "hipoteca" as const },
                       documentos: { ...v.documentos, nota_simple: true } };
    expect(rutasOcultas(visibles)).toEqual(["subasta.deposito_pct"]);
  });

  it("estaOculta reconoce la ruta y sus hijas", () => {
    const ocultas = rutasOcultas(soloObligatorios());
    expect(estaOculta("rentista.vacancia_pct", ocultas)).toBe(true);
    expect(estaOculta("activo.vpo_precio_max_legal", ocultas)).toBe(true);
    expect(estaOculta("activo.superficie_m2", ocultas)).toBe(false);
  });
});

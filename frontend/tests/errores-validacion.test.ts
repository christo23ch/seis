import { describe, expect, it } from "vitest";
import { primerPasoConError, rutasConError, traducir422 } from "@/lib/errores-validacion";
import { pasoDeRuta } from "@/lib/schema";

const existe = (ruta: string) =>
  ["activo.anio_construccion", "activo.lat", "subasta.valor_subasta", "cargas.0.importe",
   "comparables.1.precio_m2", "activo.superficie_m2"].includes(ruta);

describe("traducir422: errores de validación del backend → campos del formulario", () => {
  it("lleva cada «loc» a su campo, en español y sin el texto de Pydantic", () => {
    const r = traducir422([
      { type: "int_parsing", loc: ["body", "activo", "anio_construccion"], msg: "Input should be a valid integer, unable to parse string as an integer" },
      { type: "float_parsing", loc: ["body", "activo", "lat"], msg: "Input should be a valid number, unable to parse string as a number" },
      { type: "float_parsing", loc: ["body", "cargas", 0, "importe"], msg: "Input should be a valid number" },
    ], existe);
    expect(r.campos).toEqual({
      "activo.anio_construccion": "Introduzca un número entero",
      "activo.lat": "Introduzca un número",
      "cargas.0.importe": "Introduzca un número",
    });
    expect(r.generales).toEqual([]);
  });

  it("traduce obligatorios y límites con su cifra en formato español", () => {
    const r = traducir422([
      { type: "missing", loc: ["body", "subasta", "valor_subasta"], msg: "Field required" },
      { type: "greater_than", loc: ["body", "activo", "superficie_m2"], msg: "Input should be greater than 0", ctx: { gt: 0 } },
      { type: "greater_than_equal", loc: ["body", "comparables", 1, "precio_m2"], msg: "x", ctx: { ge: 1.5 } },
    ], existe);
    expect(r.campos["subasta.valor_subasta"]).toBe("Campo obligatorio");
    expect(r.campos["activo.superficie_m2"]).toBe("Debe ser mayor que 0");
    expect(r.campos["comparables.1.precio_m2"]).toBe("No puede ser menor que 1,5");
  });

  it("un «loc» sin campo en el formulario da un mensaje general legible", () => {
    const r = traducir422([
      { type: "literal_error", loc: ["body", "activo", "atributos", "banos"], msg: "Input should be 'a' or 'b'" },
      { type: "value_error", loc: ["body"], msg: "Value error, algo" },
    ], existe);
    expect(r.campos).toEqual({});
    expect(r.generales).toEqual([
      "Activo › atributos › banos: valor no válido",
      "Datos del análisis: valor no válido",
    ]);
  });

  it("los límites de un porcentaje se dan en %, como se escriben, no en fracción", () => {
    const r = traducir422([
      { type: "less_than_equal", loc: ["body", "financiacion", "ltv"], msg: "", ctx: { le: 0.8 } },
    ], (ruta) => ruta === "financiacion.ltv", new Set(["financiacion.ltv"]));
    expect(r.campos["financiacion.ltv"]).toBe("No puede ser mayor que 80");
  });

  it("si el campo tiene varios errores, se queda con el primero", () => {
    const r = traducir422([
      { type: "missing", loc: ["body", "activo", "lat"], msg: "" },
      { type: "float_parsing", loc: ["body", "activo", "lat"], msg: "" },
    ], existe);
    expect(r.campos["activo.lat"]).toBe("Campo obligatorio");
  });

  it("tolera un detalle que no es una lista (error propio del backend)", () => {
    expect(traducir422("Análisis no encontrado", existe)).toEqual({ campos: {}, generales: ["Análisis no encontrado"] });
    expect(traducir422(undefined, existe)).toEqual({ campos: {}, generales: [] });
  });
});

describe("rutasConError y pasoDeRuta: llevar al primer campo pendiente", () => {
  it("aplana el objeto de errores de react-hook-form, listas incluidas", () => {
    const errores = {
      subasta: { valor_subasta: { type: "invalid_type", message: "Campo obligatorio" } },
      comparables: [undefined, { precio_m2: { message: "Campo obligatorio" } }],
      activo: { municipio: { message: "Campo obligatorio", ref: {} } },
    };
    expect(rutasConError(errores)).toEqual(["subasta.valor_subasta", "comparables.1.precio_m2", "activo.municipio"]);
  });

  it("recoge el error raíz de una lista («Añada al menos un comparable»)", () => {
    expect(rutasConError({ comparables: { message: "Añada al menos un comparable", root: undefined } }))
      .toEqual(["comparables"]);
    expect(rutasConError({ comparables: { root: { message: "Añada al menos un comparable" } } }))
      .toEqual(["comparables"]);
  });

  it("sitúa cada ruta en su paso del asistente", () => {
    expect(pasoDeRuta("subasta.valor_subasta")).toBe(0);
    expect(pasoDeRuta("activo.superficie_m2")).toBe(1);
    expect(pasoDeRuta("cargas.0.importe")).toBe(2);
    expect(pasoDeRuta("activo.municipio")).toBe(4);
    expect(pasoDeRuta("comparables.1.precio_m2")).toBe(5);
    expect(pasoDeRuta("costes.tenencia_mensual")).toBe(6);
    expect(pasoDeRuta("documentos.nota_simple_dias")).toBe(9);
    expect(pasoDeRuta("no.existe")).toBeUndefined();
  });

  it("el primer paso con errores es el de menor índice, no el primero de la lista", () => {
    expect(primerPasoConError(["costes.tenencia_mensual", "activo.superficie_m2"])).toBe(1);
    expect(primerPasoConError([])).toBeUndefined();
  });
});

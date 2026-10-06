import { describe, expect, it } from "vitest";
import { aNumero, limpiarVacios } from "@/lib/formulario";

describe("aNumero: conversor numérico único del formulario", () => {
  it("acepta coma decimal", () => {
    expect(aNumero("0,5")).toBe(0.5);
    expect(aNumero("3,75")).toBe(3.75);
    expect(aNumero("-3,7038")).toBe(-3.7038);
  });

  it("acepta punto decimal (coordenadas, valores pegados)", () => {
    expect(aNumero("40.4168")).toBe(40.4168);
    expect(aNumero("0.5")).toBe(0.5);
  });

  it("entiende el punto de miles del español", () => {
    expect(aNumero("150.000")).toBe(150000);
    expect(aNumero("1.250.000")).toBe(1250000);
    expect(aNumero("7.600,50")).toBe(7600.5);
  });

  it("en los campos decimales (tasas, coeficientes, coordenadas) el punto es siempre decimal", () => {
    const decimal = { puntoDeMiles: false };
    expect(aNumero("0.125", decimal)).toBe(0.125);
    expect(aNumero("3.500", decimal)).toBe(3.5);
    expect(aNumero("-3.703", decimal)).toBe(-3.703);
    expect(aNumero("1,05", decimal)).toBe(1.05);
  });

  it("rechaza mezclas ambiguas en vez de adivinar", () => {
    expect(aNumero("1,234.56")).toBeNaN();
    expect(aNumero("1.23.4")).toBeNaN();
    expect(aNumero("12.34,5")).toBeNaN();
  });

  it("acepta el signo menos tipográfico que pegan los móviles y los procesadores de texto", () => {
    expect(aNumero("−3,7038")).toBe(-3.7038);
  });

  it("ignora espacios de los extremos, el espacio de miles y el euro o el porcentaje final", () => {
    expect(aNumero(" 150 000 € ")).toBe(150000);
    expect(aNumero("5 %")).toBe(5);
    expect(aNumero("1 250 000,5")).toBe(1250000.5);
  });

  it("no pega cifras separadas por espacios o símbolos sueltos", () => {
    expect(aNumero("1 5")).toBeNaN();
    expect(aNumero("5€5")).toBeNaN();
  });

  it("acepta el decimal sin cero inicial", () => {
    expect(aNumero(",5")).toBe(0.5);
    expect(aNumero(".5")).toBe(0.5);
    expect(aNumero("-,5")).toBe(-0.5);
  });

  it("devuelve undefined si el campo está vacío", () => {
    expect(aNumero("")).toBeUndefined();
    expect(aNumero("   ")).toBeUndefined();
    expect(aNumero(undefined)).toBeUndefined();
    expect(aNumero(null)).toBeUndefined();
  });

  it("devuelve NaN si el texto no es un número, para que la validación lo diga", () => {
    expect(aNumero("abc")).toBeNaN();
    expect(aNumero("1,2,3")).toBeNaN();
    expect(aNumero("12a")).toBeNaN();
  });

  it("deja pasar los números tal cual", () => {
    expect(aNumero(42)).toBe(42);
    expect(aNumero(0)).toBe(0);
  });
});

describe("limpiarVacios: normalizador único del envío", () => {
  it("omite cadenas vacías, null, undefined y NaN en cualquier nivel", () => {
    const entrada = {
      activo: { anio_construccion: "", lat: undefined, lng: null, superficie_m2: 82, municipio: "Madrid" },
      subasta: { puja_minima: Number.NaN, valor_subasta: 152000 },
      cargas: [{ tipo: "embargo", importe: "" }],
    };
    expect(limpiarVacios(entrada)).toEqual({
      activo: { superficie_m2: 82, municipio: "Madrid" },
      subasta: { valor_subasta: 152000 },
      cargas: [{ tipo: "embargo" }],
    });
  });

  it("conserva ceros, falsos y listas vacías: son datos, no ausencias", () => {
    const entrada = { a: 0, b: false, c: [], d: { e: 0 } };
    expect(limpiarVacios(entrada)).toEqual(entrada);
  });

  it("recorta los espacios de los textos y omite los que quedan vacíos", () => {
    expect(limpiarVacios({ x: "  Madrid ", y: "   " })).toEqual({ x: "Madrid" });
  });

  it("no modifica el objeto de entrada", () => {
    const entrada = { a: "", b: { c: "" } };
    limpiarVacios(entrada);
    expect(entrada).toEqual({ a: "", b: { c: "" } });
  });
});

import { describe, expect, it } from "vitest";
import { PROVINCIAS } from "@/lib/provincias";
import { coordenadaDeProvincia, coordenadasAlCambiarProvincia, esCoordenadaDeProvincia } from "@/lib/coordenadas";

/** Cajas generosas: península y Baleares, Canarias, Ceuta y Melilla. */
const EN_ESPANA = ({ lat, lng }: { lat: number; lng: number }) =>
  (lat >= 35.9 && lat <= 43.9 && lng >= -9.4 && lng <= 4.4)        // península y Baleares
  || (lat >= 27.5 && lat <= 29.5 && lng >= -18.3 && lng <= -13.3)  // Canarias
  || (lat >= 35.8 && lat <= 35.95 && lng >= -5.4 && lng <= -5.25)  // Ceuta
  || (lat >= 35.25 && lat <= 35.33 && lng >= -3.0 && lng <= -2.9); // Melilla

describe("tabla de provincias (5I-E)", () => {
  it("tiene las 52: una por código INE del 01 al 52, sin repetir nombre", () => {
    expect(PROVINCIAS).toHaveLength(52);
    const codigos = PROVINCIAS.map((p) => p.codigoIne).sort();
    expect(codigos).toEqual(Array.from({ length: 52 }, (_, i) => String(i + 1).padStart(2, "0")));
    expect(new Set(PROVINCIAS.map((p) => p.provincia)).size).toBe(52);
  });

  it("todas las coordenadas caen en España", () => {
    const fuera = PROVINCIAS.filter((p) => !EN_ESPANA(p));
    expect(fuera).toEqual([]);
  });

  it("las islas están en su archipiélago y las capitales donde se esperan", () => {
    const de = (n: string) => coordenadaDeProvincia(n)!;
    expect(de("Las Palmas").lng).toBeLessThan(-13);
    expect(de("Santa Cruz de Tenerife").lng).toBeLessThan(-15);
    expect(de("Illes Balears").lng).toBeGreaterThan(2);
    // Madrid, Puerta del Sol ≈ 40,417 −3,703: el centroide del casco cae a pocos km.
    expect(Math.abs(de("Madrid").lat - 40.417)).toBeLessThan(0.1);
    expect(Math.abs(de("Madrid").lng + 3.703)).toBeLessThan(0.1);
  });
});

describe("autocompletado de lat/lng al elegir provincia (5I-E)", () => {
  const madrid = coordenadaDeProvincia("Madrid")!;
  const teruel = coordenadaDeProvincia("Teruel")!;
  const texto = (c: { lat: number; lng: number }) =>
    ({ lat: String(c.lat).replace(".", ","), lng: String(c.lng).replace(".", ",") });

  it("rellena lat/lng vacías con la coordenada de la provincia", () => {
    expect(coordenadasAlCambiarProvincia({ lat: "", lng: "" }, "Madrid")).toEqual({ lat: madrid.lat, lng: madrid.lng });
  });

  it("no pisa una coordenada ya escrita, ni siquiera una sola", () => {
    expect(coordenadasAlCambiarProvincia({ lat: "40,1", lng: "-3,9" }, "Teruel")).toBeNull();
    expect(coordenadasAlCambiarProvincia({ lat: "40,1", lng: "" }, "Teruel")).toBeNull();
  });

  it("si la que hay es la aproximada de otra provincia, la cambia por la nueva", () => {
    expect(coordenadasAlCambiarProvincia(texto(madrid), "Teruel")).toEqual({ lat: teruel.lat, lng: teruel.lng });
  });

  it("al quitar la provincia, se quita también su coordenada aproximada (no queda como exacta)", () => {
    expect(coordenadasAlCambiarProvincia(texto(madrid), "")).toBe("vaciar");
    expect(coordenadasAlCambiarProvincia({ lat: "40,1", lng: "-3,9" }, "")).toBeNull();
    expect(coordenadasAlCambiarProvincia({ lat: "", lng: "" }, "")).toBeNull();
  });

  it("Madrid → «Seleccione…» → Teruel acaba con la de Teruel, no con la de Madrid", () => {
    expect(coordenadasAlCambiarProvincia(texto(madrid), "")).toBe("vaciar");
    expect(coordenadasAlCambiarProvincia({ lat: "", lng: "" }, "Teruel")).toEqual({ lat: teruel.lat, lng: teruel.lng });
  });

  it("una provincia desconocida no inventa coordenadas", () => {
    expect(coordenadasAlCambiarProvincia({ lat: "", lng: "" }, "Atlántida")).toBeNull();
  });

  it("reconoce la coordenada aproximada mientras no se cambie", () => {
    expect(esCoordenadaDeProvincia({ lat: madrid.lat, lng: madrid.lng }, "Madrid")).toBe(true);
    expect(esCoordenadaDeProvincia({ lat: "40,4249", lng: "-3,6645" }, "Madrid")).toBe(true);
    expect(esCoordenadaDeProvincia({ lat: "40,42", lng: "-3,6645" }, "Madrid")).toBe(false);
    expect(esCoordenadaDeProvincia({ lat: "", lng: "" }, "Madrid")).toBe(false);
  });
});

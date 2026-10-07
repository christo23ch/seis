import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { pesosIcoDeArbol, pesosIcoDeCatalogo } from "@/lib/ico";
import type { ParametrosSimulables } from "@/lib/types";

const editable = (clave: string, vigente: unknown, original: unknown) =>
  ({ clave, valor_vigente: vigente, valor_original: original });
const catalogo = (editables: ReturnType<typeof editable>[]) =>
  ({ editables, no_editables: [], derivados: [] }) as unknown as ParametrosSimulables;

describe("pesos del ICO desde el catálogo (5K-E)", () => {
  const cat = catalogo([
    editable("ico.pesos.rentabilidad", 30, 25), editable("ico.pesos.juridico", 15, 15),
    editable("perfiles.flip_integral.m_objetivo", 0.25, 0.25),
  ]);

  it("original para la configuración original de un análisis; vigente para el asistente", () => {
    expect(pesosIcoDeCatalogo(cat, "original")).toEqual({ rentabilidad: 25, juridico: 15 });
    expect(pesosIcoDeCatalogo(cat, "vigente")).toEqual({ rentabilidad: 30, juridico: 15 });
  });

  it("sin snapshot del análisis (anterior a 0014) no se supone ningún peso", () => {
    const sinSnapshot = catalogo([editable("ico.pesos.rentabilidad", 25, null)]);
    expect(pesosIcoDeCatalogo(sinSnapshot, "original")).toBeNull();
    expect(pesosIcoDeCatalogo(undefined, "vigente")).toBeNull();
    expect(pesosIcoDeCatalogo(catalogo([]), "vigente")).toBeNull();
  });

  it("de los parámetros aplicados de una simulación", () => {
    expect(pesosIcoDeArbol({ ico: { pesos: { rentabilidad: 20, juridico: 18 } } })).toEqual({ rentabilidad: 20, juridico: 18 });
    expect(pesosIcoDeArbol({ ico: {} })).toBeNull();
    expect(pesosIcoDeArbol(null)).toBeNull();
    expect(pesosIcoDeArbol({ ico: { pesos: { rentabilidad: "x" } } })).toBeNull();
  });

  it("el componente ya no lleva pesos escritos a mano (regresión de resultado.tsx:196)", () => {
    const fuente = readFileSync(join(__dirname, "..", "components", "resultado.tsx"), "utf-8");
    expect(fuente).not.toMatch(/rentabilidad:\s*25/);
    expect(fuente).not.toMatch(/\?\?\s*15\b/);
  });
});

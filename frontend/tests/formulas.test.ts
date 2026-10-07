import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { segmentarTexto, textoLegible } from "@/lib/formulas";
import { analizarMarkdown, textoPlano, type Bloque } from "@/lib/markdown";

const INFORME = readFileSync(join(__dirname, "datos", "informe_caso19.md"), "utf-8");

describe("segmentarTexto: fórmulas de la especificación", () => {
  it.each([
    ["P_max", "P", "máx"], ["P_ideal", "P", "ideal"], ["P_objetivo", "P", "objetivo"], ["P_limite", "P", "límite"],
    ["P_adj", "P", "adj"], ["C_F", "C", "F"], ["c_v", "c", "v"], ["δ_v", "δ", "v"], ["VS_p", "VS", "p"],
    ["MS_valor", "MS", "valor"], ["VS_m2", "VS", "m²"],
  ])("%s → %s con subíndice %s", (token, base, sub) => {
    expect(segmentarTexto(token)).toEqual([{ tipo: "formula", base, sub, original: token }]);
  });

  it("dentro de una frase, sin tocar el resto", () => {
    expect(segmentarTexto("Rojo competitivo: P_max queda por debajo")).toEqual([
      { tipo: "texto", texto: "Rojo competitivo: " },
      { tipo: "formula", base: "P", sub: "máx", original: "P_max" },
      { tipo: "texto", texto: " queda por debajo" },
    ]);
    expect(textoLegible("pujar solo P_ideal 'por si acaso'")).toBe("pujar solo P ideal 'por si acaso'");
  });
});

describe("segmentarTexto: identificadores internos", () => {
  it("con nombre legible", () => {
    expect(textoLegible("Subasta judicial_boe, ocupacion_desalojo")).toBe(
      "Subasta judicial (Portal de Subastas del BOE), Ocupación y desalojo");
    expect(textoLegible("Subsanar: posesion_verificada; Subsanar: fotos_interior_o_visita")).toBe(
      "Subsanar: posesión verificada; Subsanar: fotos interiores o visita");
    expect(textoLegible("dominancia: una_alta")).toBe("dominancia: una dimensión alta");
  });

  it("una clave desconocida en minúscula se lee con espacios; con mayúsculas no se toca", () => {
    expect(textoLegible("valor otra_clave_nueva")).toBe("valor otra clave nueva");
    expect(textoLegible("Foo_Bar")).toBe("Foo_Bar");
  });

  it("no toca texto sin barra baja, cifras ni códigos de regla", () => {
    for (const t of ["VETO-COMP-01 v2026.07", "152.000 €", "Precio máximo", "P adj. 63.840 €"]) {
      expect(segmentarTexto(t)).toEqual([{ tipo: "texto", texto: t }]);
    }
  });
});

describe("informe real del caso §19", () => {
  it("tras segmentar, no queda ningún identificador con barra baja visible", () => {
    const bloques = analizarMarkdown(INFORME);
    const lineas = bloques.flatMap((b: Bloque) => {
      switch (b.tipo) {
        case "titulo": return [b.contenido];
        case "parrafo": return b.lineas;
        case "lista": return b.items.map((i) => i.contenido);
        case "tabla": return [...(b.cabecera ?? []), ...b.filas.flat()];
        default: return [];
      }
    });
    // Los códigos en línea (`VETO-…`) no se segmentan: se excluyen como hace el componente.
    const visibles = lineas.map((l) => textoLegible(textoPlano(l.filter((n) => n.tipo !== "codigo"))));
    expect(visibles.filter((t) => /[\p{L}\p{N}]_[\p{L}\p{N}]/u.test(t))).toEqual([]);
  });
});

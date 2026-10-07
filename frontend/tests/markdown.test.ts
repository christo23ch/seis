import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { analizarEnLinea, analizarMarkdown, textoPlano, type Bloque, type Inline } from "@/lib/markdown";

/** Informe REAL del caso §19, generado con el motor (`tests/datos/LEEME.md`). */
const INFORME = readFileSync(join(__dirname, "datos", "informe_caso19.md"), "utf-8");

describe("analizarEnLinea", () => {
  it("negrita, cursiva con _ y con *, y código", () => {
    expect(analizarEnLinea("a **b** _c_ *d* `e`")).toEqual([
      { tipo: "texto", texto: "a " }, { tipo: "negrita", hijos: [{ tipo: "texto", texto: "b" }] },
      { tipo: "texto", texto: " " }, { tipo: "cursiva", hijos: [{ tipo: "texto", texto: "c" }] },
      { tipo: "texto", texto: " " }, { tipo: "cursiva", hijos: [{ tipo: "texto", texto: "d" }] },
      { tipo: "texto", texto: " " }, { tipo: "codigo", texto: "e" },
    ]);
  });

  it("no toma por cursiva la barra baja de un identificador o una fórmula", () => {
    for (const t of ["C_F (P50)", "δ_v aplicado", "Subasta judicial_boe", "c_v = 6,40 %", "dominancia: una_alta"]) {
      expect(analizarEnLinea(t)).toEqual([{ tipo: "texto", texto: t }]);
    }
  });

  it("anida la negrita dentro de la cursiva y al revés", () => {
    const n = analizarEnLinea("_hay **x** aquí_");
    expect(n).toHaveLength(1);
    expect(n[0].tipo).toBe("cursiva");
    expect(textoPlano(n)).toBe("hay x aquí");
  });

  it("deja tal cual lo que no cierra", () => {
    expect(analizarEnLinea("**sin cerrar y 3 * 4")).toEqual([{ tipo: "texto", texto: "**sin cerrar y 3 * 4" }]);
  });
});

describe("analizarMarkdown: bloques", () => {
  it("títulos, párrafos, listas, casillas, separador y tabla con cabecera", () => {
    const b = analizarMarkdown("# Uno\n\n## Dos\ntexto\nsegunda\n\n- a\n- [ ] b\n- [x] c\n---\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |");
    expect(b.map((x) => x.tipo)).toEqual(["titulo", "titulo", "parrafo", "lista", "separador", "tabla"]);
    expect((b[2] as Extract<Bloque, { tipo: "parrafo" }>).lineas).toHaveLength(2);
    expect((b[3] as Extract<Bloque, { tipo: "lista" }>).items.map((i) => i.casilla)).toEqual([null, false, true]);
    const t = b[5] as Extract<Bloque, { tipo: "tabla" }>;
    expect(t.cabecera!.map(textoPlano)).toEqual(["A", "B"]);
    expect(t.filas.map((f) => f.map(textoPlano))).toEqual([["1", "2"], ["3", "4"]]);
  });

  it("una tabla sin fila separadora no tiene cabecera", () => {
    const [t] = analizarMarkdown("| a | b |\n| c | d |") as Extract<Bloque, { tipo: "tabla" }>[];
    expect(t.cabecera).toBeNull();
    expect(t.filas).toHaveLength(2);
  });

  it("normaliza los finales de línea de Windows", () => {
    expect(analizarMarkdown("# T\r\n\r\ntexto").map((x) => x.tipo)).toEqual(["titulo", "parrafo"]);
  });
});

/* ── barrido del informe real del §19 ─────────────────────────────────────── */

function textos(bloques: Bloque[]): string[] {
  const enLinea = (n: Inline[]) => textoPlano(n);
  return bloques.flatMap((b) => {
    switch (b.tipo) {
      case "titulo": return [enLinea(b.contenido)];
      case "parrafo": return b.lineas.map(enLinea);
      case "lista": return b.items.map((i) => enLinea(i.contenido));
      case "tabla": return [...(b.cabecera ?? []).map(enLinea), ...b.filas.flat().map(enLinea)];
      case "separador": return [];
    }
  });
}

describe("informe real del caso §19", () => {
  const bloques = analizarMarkdown(INFORME);
  const visible = textos(bloques).join("\n");

  it("no queda ninguna marca de Markdown en crudo", () => {
    expect(visible).not.toMatch(/\*\*/);
    expect(visible).not.toMatch(/\|\s*-{3,}/);
    expect(visible).not.toMatch(/^#{1,3}\s/m);
    expect(visible).not.toMatch(/^- \[ \]/m);
  });

  it("reconoce las secciones, las tablas y los bloqueantes del checklist", () => {
    const titulos = bloques.filter((b) => b.tipo === "titulo").map((b) => textoPlano((b as any).contenido));
    expect(titulos[0]).toBe("Informe de análisis SEIS");
    expect(titulos).toContain("1 · Página de decisión");
    expect(titulos).toContain("10 · Trazabilidad");
    // Decisión, costes, riesgos, escenarios y la del procedimiento (5J-1).
    expect(bloques.filter((b) => b.tipo === "tabla")).toHaveLength(5);
    const casillas = bloques.flatMap((b) => (b.tipo === "lista" ? b.items : [])).filter((i) => i.casilla === false);
    expect(casillas.length).toBeGreaterThan(0);
  });

  it("no pierde ni reordena texto: sin marcas ni espacios, original y visible son idénticos", () => {
    // Fuera las marcas de Markdown y los espacios; lo demás debe coincidir carácter a carácter.
    const desnudo = (s: string) => s.replace(/[*`|#_\-[\]\s]/g, "");
    expect(desnudo(visible)).toBe(desnudo(INFORME));
  });

  it("desde la 5J-2a el motor redacta los nombres: ni símbolos con barra baja ni claves internas", () => {
    expect(visible).toContain("Partida de costes fijos (P50)");
    expect(visible).toContain("descuento de prudencia aplicado");
    expect(visible).not.toMatch(/[^\W_]_[^\W_]/u);
  });
});

describe("correcciones de la revisión de código (5K)", () => {
  it("una fila de «-» en el cuerpo de una tabla es un dato, no un separador", () => {
    const [t] = analizarMarkdown("| A | B |\n|---|---|\n| - | - |\n| 1 | 2 |") as Extract<Bloque, { tipo: "tabla" }>[];
    expect(t.filas.map((f) => f.map(textoPlano))).toEqual([["-", "-"], ["1", "2"]]);
  });
});

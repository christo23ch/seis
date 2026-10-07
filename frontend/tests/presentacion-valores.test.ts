import { describe, expect, it } from "vitest";
import { indexarCatalogo } from "@/lib/catalogo";
import { ETIQUETAS_ENTRADA, SECCIONES_ENTRADA } from "@/lib/etiquetas-entrada";
import { NO_CONSTA, construirArbol, contarValores, formatearValor, humanizar, rutaGenerica, valorEnRuta, type Nodo } from "@/lib/presentacion-valores";
import type { ParametrosSimulables } from "@/lib/types";

const hoja = (nodos: Nodo[], ruta: string): Extract<Nodo, { tipo: "hoja" }> => {
  for (const n of nodos) {
    if (n.ruta === ruta && n.tipo === "hoja") return n;
    if (n.tipo === "grupo") { try { return hoja(n.hijos, ruta); } catch { /* sigue buscando */ } }
  }
  throw new Error(`sin hoja ${ruta}`);
};

describe("humanizar", () => {
  it("separa, pone tildes y abreviaturas, y capitaliza", () => {
    expect(humanizar("deposito_pct")).toBe("Depósito %");
    expect(humanizar("tendencia_5a_pct")).toBe("Tendencia 5 años %");
    expect(humanizar("itp_por_ccaa")).toBe("ITP por CC. AA.");
    expect(humanizar("conservacion")).toBe("Conservación");
  });
});

describe("formatearValor", () => {
  it("ausente es «No consta», nunca 0", () => {
    for (const v of [null, undefined, ""]) expect(formatearValor(v)).toBe(NO_CONSTA);
  });
  it("booleanos, números en español, fracciones como porcentaje y listas", () => {
    expect(formatearValor(true)).toBe("Sí");
    expect(formatearValor(false)).toBe("No");
    expect(formatearValor(152000)).toBe("152.000");
    expect(formatearValor(0.016)).toBe("0,016");
    expect(formatearValor(0.05, { fraccion: true })).toBe("5 %");
    expect(formatearValor(0.064, { fraccion: true })).toBe("6,4 %");
    expect(formatearValor([])).toBe("Ninguno");
    expect(formatearValor(["a", "b"])).toBe("a; b");
  });
  it("valores de lista cerrada con su texto, y claves internas sin barra baja", () => {
    expect(formatearValor("no_consta", { valores: { no_consta: "No consta" } })).toBe("No consta");
    expect(formatearValor("arrendado_anterior")).toBe("arrendado anterior");
    expect(formatearValor("Madrid")).toBe("Madrid");
  });
});

describe("construirArbol", () => {
  it("usa el diccionario por ruta genérica y la unidad", () => {
    const nodos = construirArbol({ subasta: { valor_subasta: 152000, deposito_pct: 0.05, cantidad_reclamada: null } },
      { etiquetas: ETIQUETAS_ENTRADA });
    expect(hoja(nodos, "subasta.valor_subasta")).toMatchObject({ etiqueta: "Valor de subasta", valor: "152.000", unidad: "€" });
    expect(hoja(nodos, "subasta.deposito_pct")).toMatchObject({ etiqueta: "Depósito", valor: "5 %" });
    // Un dato ausente no lleva unidad: «No consta €» no tendría sentido.
    expect(hoja(nodos, "subasta.cantidad_reclamada")).toMatchObject({ valor: NO_CONSTA, unidad: undefined });
  });

  it("listas de objetos iguales como tabla; listas de comparables con su ruta genérica", () => {
    const [t] = construirArbol({ rvc_bandas: [{ min: 1.05, banda: "alcanzable" }, { min: 0.9, banda: "ajustado" }] });
    expect(t).toMatchObject({ tipo: "tabla", columnas: ["Min", "Banda"], filas: [["1,05", "alcanzable"], ["0,9", "ajustado"]] });
    const [c] = construirArbol({ comparables: [{ precio_m2: 2293, estado: "reformado", origen: "testigo", meses_antiguedad: 0 }] },
      { etiquetas: ETIQUETAS_ENTRADA });
    expect(c).toMatchObject({ tipo: "tabla", columnas: ["Precio (€/m²)", "Estado", "Origen", "Antigüedad (meses)"] });
    expect(rutaGenerica("comparables.3.precio_m2")).toBe("comparables[].precio_m2");
  });

  it("el catálogo manda sobre el diccionario y deduce las fracciones de su unidad", () => {
    const catalogo = new Map([["capital.coste_capital_anual", { nombre: "Coste de capital anual", unidad: "fracción anual (0–1)" }]]);
    const nodos = construirArbol({ capital: { coste_capital_anual: 0.015 } }, { catalogo });
    expect(hoja(nodos, "capital.coste_capital_anual")).toMatchObject({ etiqueta: "Coste de capital anual", valor: "1,5 %" });
  });

  it("un dato legal de la 5J-1 es una sola fila con artículo y estado", () => {
    const nodos = construirArbol({ deposito_pct: { valor: 0.2, articulo: "LEC, art. 669, apdo. 1", estado: "confirmado" },
                                   plazo_pago_dias: { valor: 5, unidad: "habiles", articulo: "RGRSS, art. 120", estado: "sin_confirmar" } });
    expect(hoja(nodos, "deposito_pct")).toMatchObject({ valor: "20 %", detalle: "LEC, art. 669, apdo. 1 · confirmado" });
    expect(hoja(nodos, "plazo_pago_dias")).toMatchObject({ valor: "5", unidad: "días hábiles", detalle: "RGRSS, art. 120 · sin confirmar" });
  });

  it("cuenta los valores de una sección plegada", () => {
    expect(contarValores(construirArbol({ a: 1, b: { c: 2, d: 3 }, e: [{ x: 1 }, { x: 2 }] }))).toBe(5);
  });
});

describe("entrada del asistente", () => {
  it("cada sección es de claves distintas y cubre las de primer nivel de la entrada", () => {
    const claves = SECCIONES_ENTRADA.flatMap((s) => s.claves);
    expect(new Set(claves).size).toBe(claves.length);
    for (const k of ["perfil", "subasta", "activo", "cargas", "ocupacion", "urbanistico", "comparables", "zona",
                     "costes", "reforma", "financiacion", "rentista", "documentos"]) expect(claves).toContain(k);
  });
});

describe("valorEnRuta e indexarCatalogo", () => {
  it("lee rutas con puntos y devuelve undefined si no existen", () => {
    const arbol = { tenencia: { mensual_defecto: 240 } };
    expect(valorEnRuta(arbol, "tenencia.mensual_defecto")).toBe(240);
    expect(valorEnRuta(arbol, "tenencia.no_existe")).toBeUndefined();
    expect(valorEnRuta(arbol, "")).toBeUndefined();
  });

  it("indexa editables y no editables por clave", () => {
    const c = {
      editables: [{ clave: "a.b", nombre_legible: "A B", unidad: "días" }],
      no_editables: [{ clave: "c", nombre_legible: "C", unidad: "" }],
    } as unknown as ParametrosSimulables;
    const m = indexarCatalogo(c);
    expect(m.get("a.b")).toEqual({ nombre: "A B", unidad: "días" });
    expect(m.get("c")).toEqual({ nombre: "C", unidad: undefined });
    expect(indexarCatalogo(undefined).size).toBe(0);
  });
});

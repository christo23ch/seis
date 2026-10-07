/**
 * Fase 5K-B — presentación legible de árboles de valores (entrada de un análisis,
 * árbol T3 vigente). Funciones puras: no calculan nada, solo dan nombre y formato.
 *
 * Etiquetas, por orden de preferencia:
 *   1. el catálogo de parámetros (nombre legible y unidad, el mismo que usan las
 *      Simulaciones), si se conoce la clave;
 *   2. un diccionario explícito (p. ej. el de la entrada, `lib/etiquetas-entrada.ts`);
 *   3. la clave humanizada («deposito_pct» → «Depósito %»).
 *
 * Un valor ausente se muestra como «No consta», nunca como 0 (P4).
 */
import { num } from "@/lib/format";

export const NO_CONSTA = "No consta";

export interface Etiqueta {
  etiqueta: string;
  unidad?: string;
  /** El valor viaja en tanto por uno y se muestra como porcentaje (0,05 → «5 %»). */
  fraccion?: boolean;
  /** Textos legibles de los valores de una lista cerrada («si» → «Sí»). */
  valores?: Record<string, string>;
}

export type Nodo =
  | { tipo: "grupo"; ruta: string; etiqueta: string; hijos: Nodo[] }
  | { tipo: "hoja"; ruta: string; etiqueta: string; valor: string; unidad?: string; detalle?: string }
  | { tipo: "tabla"; ruta: string; etiqueta: string; columnas: string[]; filas: string[][] };

/* ── nombres ──────────────────────────────────────────────────────────────── */

const PALABRAS: Record<string, string> = {
  pct: "%", pp: "pp", eur: "€", m2: "m²", vt: "VT", vm: "VM", vs: "VS", ccaa: "CC. AA.", itp: "ITP",
  iva: "IVA", ajd: "AJD", ibi: "IBI", ici: "ICI", ico: "ICO", icu: "ICU", ra: "RA", rvc: "RVC", tir: "TIR",
  roi: "ROI", dscr: "DSCR", ltv: "LTV", vpo: "VPO", boe: "BOE", aeat: "AEAT", tgss: "TGSS", dom: "DOM",
  cv: "CV", ite: "ITE", cee: "CEE", lec: "LEC", "5a": "5 años",
  deposito: "depósito", minimo: "mínimo", maximo: "máximo", minima: "mínima", maxima: "máxima",
  numero: "número", regimen: "régimen", regimenes: "regímenes", ubicacion: "ubicación",
  informacion: "información", valoracion: "valoración", juridico: "jurídico", urbanistico: "urbanístico",
  tecnico: "técnico", ocupacion: "ocupación", revalorizacion: "revalorización",
  comercializacion: "comercialización", plusvalia: "plusvalía", financiacion: "financiación",
  adjudicacion: "adjudicación", conservacion: "conservación", tasacion: "tasación",
  inmovilizacion: "inmovilización", aprobacion: "aprobación", articulo: "artículo", critico: "crítico",
  dias: "días", anio: "año", analisis: "análisis", anos: "años", catalogo: "catálogo", publico: "público",
  economico: "económico", region: "región", periodo: "período", ultimo: "último", tecnicos: "técnicos",
  limite: "límite", indice: "índice", poblacion: "población", condicion: "condición",
  prohibicion: "prohibición", demolicion: "demolición", ordenacion: "ordenación", urbanizacion: "urbanización",
  transformacion: "transformación", educacion: "educación", gestion: "gestión",
  habil: "hábil", habiles: "hábiles",
};

/** «deposito_pct» → «Depósito %»; «tendencia_5a_pct» → «Tendencia 5 años %». */
export function humanizar(clave: string): string {
  const palabras = clave.split(/[_\s]+/).filter(Boolean).map((p) => PALABRAS[p.toLowerCase()] ?? p.toLowerCase());
  const frase = palabras.join(" ");
  return frase.charAt(0).toUpperCase() + frase.slice(1);
}

/** Ruta sin índices de lista: «comparables.2.precio_m2» → «comparables[].precio_m2». */
export const rutaGenerica = (ruta: string) => ruta.replace(/\.\d+(?=\.|$)/g, "[]");

/* ── valores ──────────────────────────────────────────────────────────────── */

export function formatearNumero(n: number, fraccion = false): string {
  if (!Number.isFinite(n)) return String(n);
  if (fraccion) return `${num(n * 100, 2)} %`;
  return num(n, 4);
}

export function formatearValor(v: unknown, e?: Pick<Etiqueta, "fraccion" | "valores">): string {
  if (v === null || v === undefined || v === "") return NO_CONSTA;
  if (typeof v === "boolean") return v ? "Sí" : "No";
  if (typeof v === "number") return formatearNumero(v, e?.fraccion);
  if (typeof v === "string") return e?.valores?.[v] ?? (/^[a-z0-9]+(_[a-z0-9]+)+$/.test(v) ? v.replace(/_/g, " ") : v);
  if (Array.isArray(v)) return v.length === 0 ? "Ninguno" : v.map((x) => formatearValor(x, e)).join("; ");
  return JSON.stringify(v);
}

const esObjeto = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const esEscalar = (v: unknown) => v === null || ["string", "number", "boolean"].includes(typeof v);

/** Dato legal de la 5J-1 (`{valor, articulo, estado[, nota]}`): una sola fila. */
const esDatoLegal = (v: Record<string, unknown>) => "valor" in v && "articulo" in v && "estado" in v;

/* ── árbol ────────────────────────────────────────────────────────────────── */

export interface OpcionesArbol {
  /** Catálogo de parámetros por clave exacta (nombre legible y unidad). */
  catalogo?: ReadonlyMap<string, { nombre: string; unidad?: string }>;
  /** Diccionario por ruta genérica (`rutaGenerica`). */
  etiquetas?: Readonly<Record<string, Etiqueta>>;
}

function etiquetaDe(ruta: string, clave: string, o: OpcionesArbol): Etiqueta {
  const cat = o.catalogo?.get(ruta);
  const dic = o.etiquetas?.[rutaGenerica(ruta)];
  if (cat) return { ...dic, etiqueta: cat.nombre, unidad: cat.unidad ?? dic?.unidad,
                    fraccion: dic?.fraccion ?? /fracci[oó]n/i.test(cat.unidad ?? "") };
  return dic ?? { etiqueta: /^\d+$/.test(clave) ? `${Number(clave) + 1}.º` : humanizar(clave) };
}

/** Árbol JSON → nodos para pintar. `ruta` es la del propio valor («» en la raíz). */
export function construirArbol(valor: unknown, o: OpcionesArbol = {}, ruta = ""): Nodo[] {
  if (!esObjeto(valor)) return [];
  return Object.entries(valor).map(([clave, v]) => nodo(clave, v, ruta ? `${ruta}.${clave}` : clave, o));
}

function nodo(clave: string, v: unknown, ruta: string, o: OpcionesArbol): Nodo {
  const e = etiquetaDe(ruta, clave, o);
  if (esObjeto(v) && esDatoLegal(v)) {
    const estado = v.estado === "confirmado" ? "confirmado" : "sin confirmar";
    const fraccion = e.fraccion ?? clave.endsWith("_pct");
    const unidad = v.unidad === "habiles" ? "días hábiles" : v.unidad === "naturales" ? "días naturales" : e.unidad;
    return { tipo: "hoja", ruta, etiqueta: e.etiqueta, unidad,
             valor: formatearValor(v.valor, { fraccion }),
             detalle: [String(v.articulo), estado, v.nota ? String(v.nota) : ""].filter(Boolean).join(" · ") };
  }
  if (esObjeto(v)) {
    const entradas = Object.keys(v);
    if (entradas.length === 0) return { tipo: "hoja", ruta, etiqueta: e.etiqueta, valor: "Ninguno" };
    return { tipo: "grupo", ruta, etiqueta: e.etiqueta, hijos: construirArbol(v, o, ruta) };
  }
  if (Array.isArray(v) && v.length > 0 && v.every(esObjeto)) {
    const claves = Object.keys(v[0] as object);
    const uniforme = v.every((x) => Object.keys(x as object).join() === claves.join())
      && v.every((x) => Object.values(x as object).every(esEscalar));
    if (uniforme) {
      const cols = claves.map((c) => etiquetaDe(`${ruta}.0.${c}`, c, o));
      return { tipo: "tabla", ruta, etiqueta: e.etiqueta, columnas: cols.map((c) => c.etiqueta + (c.unidad ? ` (${c.unidad})` : "")),
               filas: v.map((x) => claves.map((c, i) => formatearValor((x as Record<string, unknown>)[c], cols[i]))) };
    }
    return { tipo: "grupo", ruta, etiqueta: e.etiqueta, hijos: v.map((x, i) => nodo(String(i), x, `${ruta}.${i}`, o)) };
  }
  return { tipo: "hoja", ruta, etiqueta: e.etiqueta, valor: formatearValor(v, e), unidad: v == null ? undefined : e.unidad };
}

/** Número de valores (hojas y filas) bajo unos nodos: el resumen de una sección plegada. */
export function contarValores(nodos: Nodo[]): number {
  return nodos.reduce((n, x) => n + (x.tipo === "grupo" ? contarValores(x.hijos) : x.tipo === "tabla" ? x.filas.length : 1), 0);
}

/** Valor de una ruta con puntos dentro de un árbol, o `undefined` si no existe. */
export function valorEnRuta(arbol: unknown, ruta: string): unknown {
  if (!ruta.trim()) return undefined;
  return ruta.split(".").reduce<unknown>((nodo, k) => (esObjeto(nodo) && k in nodo ? nodo[k] : undefined), arbol);
}

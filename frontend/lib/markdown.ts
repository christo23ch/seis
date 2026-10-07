/**
 * Fase 5K-A — analizador del Markdown del informe (M14).
 *
 * Por qué uno propio y no una biblioteca (decisión del responsable, 5K): el texto lo
 * genera el motor de SEIS y usa un subconjunto pequeño y cerrado —títulos `#`, `##`
 * y `###`, negrita `**`, cursiva `_…_` y `*…*`, código `` `…` ``, listas `- `, casillas
 * `- [ ]`, tablas y `---`—. Un analizador de ~150 líneas, puro y con tests sobre el
 * informe real del §19, cubre todo eso sin dependencias nuevas.
 *
 * Seguridad: devuelve NODOS, nunca HTML. El componente los pinta como texto de React,
 * que escapa todo; no hay `dangerouslySetInnerHTML` y no hay superficie XSS.
 *
 * Lo que no está en el subconjunto se muestra como texto tal cual: no se pierde nada.
 */

export type Inline =
  | { tipo: "texto"; texto: string }
  | { tipo: "negrita"; hijos: Inline[] }
  | { tipo: "cursiva"; hijos: Inline[] }
  | { tipo: "codigo"; texto: string };

export interface ItemLista { casilla: boolean | null; contenido: Inline[] }

export type Bloque =
  | { tipo: "titulo"; nivel: 1 | 2 | 3; contenido: Inline[] }
  | { tipo: "parrafo"; lineas: Inline[][] }
  | { tipo: "lista"; items: ItemLista[] }
  | { tipo: "tabla"; cabecera: Inline[][] | null; filas: Inline[][][] }
  | { tipo: "separador" };

/* ── en línea ─────────────────────────────────────────────────────────────── */

// Una «_» solo abre o cierra cursiva si no está pegada a una letra o cifra: así
// `C_F`, `δ_v` o `judicial_boe` siguen siendo texto (las fórmulas son del bloque C).
const PATRONES: { tipo: "codigo" | "negrita" | "cursiva"; re: RegExp }[] = [
  { tipo: "codigo", re: /`([^`]+)`/u },
  { tipo: "negrita", re: /\*\*(.+?)\*\*/u },
  { tipo: "cursiva", re: /(?<![\p{L}\p{N}_])_(?=\S)(.+?)(?<=\S)_(?![\p{L}\p{N}_])/u },
  { tipo: "cursiva", re: /(?<![*\p{L}\p{N}])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![*\p{L}\p{N}])/u },
];

export function analizarEnLinea(texto: string): Inline[] {
  const salida: Inline[] = [];
  let resto = texto;
  while (resto.length > 0) {
    let mejor: { tipo: (typeof PATRONES)[number]["tipo"]; m: RegExpExecArray } | null = null;
    for (const p of PATRONES) {
      const m = p.re.exec(resto);
      if (m && (mejor === null || m.index < mejor.m.index)) mejor = { tipo: p.tipo, m };
    }
    if (mejor === null) { salida.push({ tipo: "texto", texto: resto }); break; }
    const { tipo, m } = mejor;
    if (m.index > 0) salida.push({ tipo: "texto", texto: resto.slice(0, m.index) });
    salida.push(tipo === "codigo" ? { tipo, texto: m[1] } : { tipo, hijos: analizarEnLinea(m[1]) });
    resto = resto.slice(m.index + m[0].length);
  }
  return salida;
}

/** Texto plano de unos nodos en línea (para etiquetas accesibles y tests). */
export const textoPlano = (nodos: Inline[]): string =>
  nodos.map((n) => (n.tipo === "texto" || n.tipo === "codigo" ? n.texto : textoPlano(n.hijos))).join("");

/* ── bloques ──────────────────────────────────────────────────────────────── */

const TITULO = /^(#{1,3})\s+(.*)$/;
const CASILLA = /^\s*-\s+\[( |x|X)\]\s+(.*)$/;
const VINETA = /^\s*-\s+(.*)$/;
const SEPARADOR = /^-{3,}\s*$/;
const esFilaTabla = (l: string) => l.trimStart().startsWith("|");
const celdas = (l: string) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
const esSeparadorTabla = (cs: string[]) => cs.length > 0 && cs.every((c) => /^:?-{1,}:?$/.test(c));

export function analizarMarkdown(md: string): Bloque[] {
  const lineas = md.replace(/\r\n?/g, "\n").split("\n");
  const bloques: Bloque[] = [];
  let parrafo: Inline[][] = [];
  const cerrarParrafo = () => { if (parrafo.length) { bloques.push({ tipo: "parrafo", lineas: parrafo }); parrafo = []; } };

  for (let i = 0; i < lineas.length; i++) {
    const l = lineas[i];
    if (l.trim() === "") { cerrarParrafo(); continue; }

    const titulo = TITULO.exec(l);
    if (titulo) {
      cerrarParrafo();
      bloques.push({ tipo: "titulo", nivel: titulo[1].length as 1 | 2 | 3, contenido: analizarEnLinea(titulo[2]) });
      continue;
    }
    if (SEPARADOR.test(l)) { cerrarParrafo(); bloques.push({ tipo: "separador" }); continue; }

    if (esFilaTabla(l)) {
      cerrarParrafo();
      const filas: string[][] = [];
      while (i < lineas.length && esFilaTabla(lineas[i])) filas.push(celdas(lineas[i++]));
      i--;
      const conCabecera = filas.length > 1 && esSeparadorTabla(filas[1]);
      // Solo la SEGUNDA fila es separador: una fila de «-» en el cuerpo es un dato.
      const cuerpo = conCabecera ? filas.slice(2) : filas;
      bloques.push({
        tipo: "tabla",
        cabecera: conCabecera ? filas[0].map(analizarEnLinea) : null,
        filas: cuerpo.map((f) => f.map(analizarEnLinea)),
      });
      continue;
    }

    if (VINETA.test(l)) {
      cerrarParrafo();
      const items: ItemLista[] = [];
      while (i < lineas.length && VINETA.test(lineas[i])) {
        const c = CASILLA.exec(lineas[i]);
        items.push(c ? { casilla: c[1].toLowerCase() === "x", contenido: analizarEnLinea(c[2]) }
                     : { casilla: null, contenido: analizarEnLinea(VINETA.exec(lineas[i])![1]) });
        i++;
      }
      i--;
      bloques.push({ tipo: "lista", items });
      continue;
    }

    parrafo.push(analizarEnLinea(l));
  }
  cerrarParrafo();
  return bloques;
}

/**
 * Fase 5K-C — fórmulas e identificadores del motor, legibles AL MOSTRARLOS.
 *
 * El motor escribe los símbolos de la especificación con barra baja (`P_max`, `C_F`,
 * `δ_v`…) y, en algunos textos, claves internas (`ocupacion_desalojo`, `judicial_boe`,
 * `una_alta`…). Aquí no se cambia el texto en origen —el informe oficial está congelado
 * y lo vigilan los tests del motor—: se segmenta para pintarlo con subíndices o con su
 * nombre legible. Función pura; la usan el Markdown del informe y los textos sueltos.
 *
 * Fórmulas: lista blanca de símbolos, no una regla general, para no confundir una clave
 * («judicial_boe») con una fórmula («J con subíndice boe»).
 */

export type Segmento =
  | { tipo: "texto"; texto: string }
  | { tipo: "formula"; base: string; sub: string; original: string }
  | { tipo: "identificador"; texto: string; original: string };

/** Símbolos de la especificación: base → subíndices admitidos. */
const FORMULAS: Record<string, string[]> = {
  P: ["ideal", "objetivo", "max", "limite", "límite", "adj", "eval"],
  C: ["F", "V"],
  c: ["v"],
  "δ": ["v"],
  VS: ["p", "pes", "m2", "m", "prudente"],
  VM: ["m2"],
  VT: ["m2"],
  MS: ["valor"],
  k: ["estado", "provincia"],
  DSCR: ["estresado"],
  Y: ["neta", "req", "zona"],
  m: ["objetivo", "minimo", "mínimo", "excepcional"],
  F: ["t"],
};
const SUB_LEGIBLE: Record<string, string> = { max: "máx", limite: "límite", minimo: "mín", "mínimo": "mín", m2: "m²" };

/** Claves internas que el motor deja en sus textos, con su nombre legible. */
export const IDENTIFICADORES: Record<string, string> = {
  // Partidas de C_F (M06)
  ocupacion_desalojo: "Ocupación y desalojo", atrasos_comunidad_ibi: "Atrasos de comunidad e IBI",
  adquisicion_fija: "Costes fijos de adquisición", cargas_subsistentes: "Cargas subsistentes",
  plusvalia_municipal: "Plusvalía municipal",
  // Fuente y método
  judicial_boe: "judicial (Portal de Subastas del BOE)", comparables_ajustados: "comparables ajustados",
  sin_comparables: "sin comparables",
  // Documentación (carencias del ICI)
  nota_simple: "nota simple", cert_cargas: "certificación de cargas", posesion_verificada: "posesión verificada",
  fotos_interior_o_visita: "fotos interiores o visita", fotos_exterior: "fotos exteriores",
  cert_comunidad: "certificado de la comunidad", recibo_ibi: "recibo del IBI", ite_cee: "ITE y certificado energético",
  catastro_conciliado: "Catastro conciliado", comparables_ok: "comparables suficientes",
  // Dominancia y bandas del riesgo agregado
  una_alta: "una dimensión alta", dos_altas: "dos dimensiones altas",
  critica_mitigable: "una dimensión crítica mitigable", critica_no_mitigable: "una dimensión crítica no mitigable",
  muy_alto: "muy alto",
  // Ocupación
  arrendado_posterior: "arrendado (contrato posterior)", arrendado_anterior: "arrendado (contrato anterior)",
  renta_antigua: "renta antigua",
};

// Token candidato: letras (latinas o griegas) y cifras unidas por «_», sin letra ni
// cifra pegada a los lados.
const TOKEN = /(?<![\p{L}\p{N}_])([\p{L}][\p{L}\p{N}]*(?:_[\p{L}\p{N}]+)+)(?![\p{L}\p{N}_])/gu;

function clasificar(token: string): Segmento | null {
  const partes = token.split("_");
  if (partes.length === 2 && FORMULAS[partes[0]]?.includes(partes[1])) {
    return { tipo: "formula", base: partes[0], sub: SUB_LEGIBLE[partes[1]] ?? partes[1], original: token };
  }
  if (IDENTIFICADORES[token]) return { tipo: "identificador", texto: IDENTIFICADORES[token], original: token };
  // Último recurso, solo para claves internas en minúscula y SIN cifras: la barra baja se
  // lee como espacio. Con cifras («nota_simple_2024») puede ser un nombre de fichero.
  if (token === token.toLowerCase() && !/\d/.test(token)) return { tipo: "identificador", texto: partes.join(" "), original: token };
  return null;
}

/** Pegado a «@ / \» el token es parte de un correo o una ruta; seguido de «.» o «:» y más
 * texto, de un fichero o una URL: no se toca. Un punto final de frase sí se admite. */
const PEGADO_ANTES = /[@/\\.:]/;
const PEGADO_DESPUES = /[@/\\]/;

export function segmentarTexto(texto: string): Segmento[] {
  const salida: Segmento[] = [];
  let ultimo = 0;
  for (const m of texto.matchAll(TOKEN)) {
    const fin = m.index! + m[0].length;
    const antes = texto[m.index! - 1] ?? "", despues = texto[fin] ?? "", tras = texto[fin + 1] ?? "";
    if (PEGADO_ANTES.test(antes) || PEGADO_DESPUES.test(despues) || (/[.:]/.test(despues) && /[^\s]/.test(tras))) continue;
    const seg = clasificar(m[1]);
    if (!seg) continue;
    if (m.index! > ultimo) salida.push({ tipo: "texto", texto: texto.slice(ultimo, m.index) });
    salida.push(seg);
    ultimo = m.index! + m[0].length;
  }
  if (ultimo < texto.length) salida.push({ tipo: "texto", texto: texto.slice(ultimo) });
  return salida;
}

/** Texto legible sin marcas (para atributos y lectores de pantalla): «P_max» → «P máx». */
export const textoLegible = (texto: string): string =>
  segmentarTexto(texto).map((s) => (s.tipo === "texto" ? s.texto : s.tipo === "formula" ? `${s.base} ${s.sub}` : s.texto)).join("");

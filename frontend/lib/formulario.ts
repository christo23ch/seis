/**
 * Fase 5I — utilidades puras del formulario de alta (sin React, con tests en
 * `tests/formulario.test.ts`).
 *
 * Dos funciones y un solo sitio para cada una, para que ningún campo tenga su
 * propio parche:
 *   · `aNumero`: el ÚNICO conversor de texto a número del formulario. Acepta la
 *     coma decimal del español («0,5») y el punto de miles («150.000»).
 *   · `limpiarVacios`: el ÚNICO normalizador del envío. Un campo opcional vacío
 *     se OMITE: el contrato del backend (`AnalisisInput`) lo trata entonces como
 *     ausente (None o su valor por defecto), que es lo que significa vacío.
 *     Antes se enviaba `""` y Pydantic respondía 422 «unable to parse string».
 */

/** Punto de miles a la española: 1 a 3 cifras y grupos de exactamente 3. */
const MILES_CON_PUNTO = /^-?\d{1,3}(\.\d{3})+$/;
/** Con coma decimal: entero sin puntos, o con puntos de miles bien agrupados. */
const CON_COMA = /^-?(\d+|\d{1,3}(\.\d{3})+),\d+$/;
/** Espacio como separador de miles, con decimales opcionales: «1 250 000,5». */
const ESPACIO_DE_MILES = /^-?\d{1,3}(\s\d{3})+([,.]\d+)?$/;
/** Número ya normalizado: signo opcional, entero y decimales opcionales. */
const NUMERO_CANONICO = /^-?\d+(\.\d+)?$/;

export interface OpcionesNumero {
  /**
   * `true` (por defecto) en importes, superficies, días…: «150.000» es 150000.
   * `false` en tasas, coeficientes y coordenadas, donde un punto es siempre
   * decimal: «3.500» de interés es 3,5 y no 3500, y «-3.703» de longitud no
   * puede leerse como −3703.
   */
  puntoDeMiles?: boolean;
}

/**
 * Convierte lo que escribe una persona en un número.
 *
 * - Vacío (o solo espacios), `null` o `undefined` ⇒ `undefined` (campo sin dato).
 * - Texto que no es un número, o una mezcla ambigua («1,234.56») ⇒ `NaN`, para
 *   que la validación lo rechace con «Introduzca un número» en vez de adivinar
 *   o convertirlo en 0 en silencio.
 *
 * Reglas, en este orden:
 *   1. Se quitan los espacios de los extremos y un «€» o «%» final; el menos
 *      tipográfico «−» se lee como «-»; un espacio interior solo vale como
 *      separador de miles («1 250 000»); «,5» se lee «0,5».
 *   2. Con coma: la coma es el decimal y los puntos solo pueden ser miles bien
 *      agrupados («7.600,50»).
 *   3. Sin coma, con grupos de tres tras el punto («150.000») y `puntoDeMiles`:
 *      los puntos son miles. Es la lectura española; «1.500» es 1500, no 1,5.
 *   4. En otro caso el punto es decimal («40.4168», «0.5»).
 */
export function aNumero(valor: unknown, { puntoDeMiles = true }: OpcionesNumero = {}): number | undefined {
  if (valor === null || valor === undefined) return undefined;
  if (typeof valor === "number") return valor;
  if (typeof valor !== "string") return Number.NaN;

  // Símbolos solo al final, y espacios solo en los extremos o como separador de
  // miles («1 250 000»): «1 5» o «5€5» no son números, no se pegan sus cifras.
  let limpio = valor.trim().replace(/−/g, "-").replace(/\s*[€%]$/, "");
  if (limpio === "") return undefined;
  if (/\s/.test(limpio)) {
    if (!ESPACIO_DE_MILES.test(limpio)) return Number.NaN;
    limpio = limpio.replace(/\s/g, "");
  }
  limpio = limpio.replace(/^(-?)([,.])/, "$10$2");          // «,5» → «0,5»

  let canonico: string;
  if (limpio.includes(",")) {
    if (!CON_COMA.test(limpio)) return Number.NaN;
    canonico = limpio.replace(/\./g, "").replace(",", ".");
  } else if (puntoDeMiles && MILES_CON_PUNTO.test(limpio)) canonico = limpio.replace(/\./g, "");
  else canonico = limpio;

  return NUMERO_CANONICO.test(canonico) ? Number(canonico) : Number.NaN;
}

function esVacio(valor: unknown): boolean {
  return valor === undefined || valor === null || valor === ""
    || (typeof valor === "number" && Number.isNaN(valor))
    || (typeof valor === "string" && valor.trim() === "");
}

/**
 * Copia profunda del payload sin los valores vacíos (`""`, `null`, `undefined`,
 * `NaN`), en cualquier nivel. Conserva `0`, `false` y las listas vacías: son
 * datos declarados, no ausencias. Recorta los espacios de los textos. No
 * modifica la entrada.
 */
export function limpiarVacios<T>(valor: T): T {
  if (Array.isArray(valor)) {
    return valor.filter((x) => !esVacio(x)).map((x) => limpiarVacios(x)) as T;
  }
  if (typeof valor === "string") return valor.trim() as T;
  if (valor === null || typeof valor !== "object") return valor;

  const salida: Record<string, unknown> = {};
  for (const [clave, v] of Object.entries(valor as Record<string, unknown>)) {
    if (!esVacio(v)) salida[clave] = limpiarVacios(v);
  }
  return salida as T;
}

/**
 * Fase 5I-B — traductor de los 422 de validación del backend (FastAPI + Pydantic v2)
 * a mensajes por campo del formulario de alta.
 *
 * Antes, `api.ts` resumía el 422 en una línea con el texto en inglés de Pydantic
 * («activo.anio_construccion: Input should be a valid integer, unable to parse
 * string…»), que es lo que vio la prueba manual. Ahora cada `loc` se lleva al
 * campo que le corresponde con un mensaje en español; si el `loc` no tiene campo
 * en el formulario, se da un mensaje general legible.
 *
 * Puro y sin React: lo prueba `tests/errores-validacion.test.ts`.
 */

import { pasoDeRuta } from "@/lib/schema";

/** Un error de validación tal como lo devuelve FastAPI en `detail`. */
interface ErrorPydantic {
  type?: string;
  loc?: (string | number)[];
  msg?: string;
  ctx?: Record<string, unknown>;
}

export interface Traduccion {
  /** Ruta del campo (`activo.lat`, `cargas.0.importe`) → mensaje en español. */
  campos: Record<string, string>;
  /** Errores sin campo en el formulario, ya legibles. */
  generales: string[];
}

const cifra = (v: unknown) =>
  typeof v === "number" ? new Intl.NumberFormat("es-ES", { maximumFractionDigits: 4 }).format(v) : String(v);

function mensaje(e: ErrorPydantic, enPorcentaje: boolean): string {
  // El formulario divide por 100 algunos porcentajes al enviarlos (`aPayload`): el
  // límite del backend viene en fracción y se devuelve a las unidades escritas.
  const ctx = Object.fromEntries(Object.entries(e.ctx ?? {}).map(([k, v]) =>
    [k, enPorcentaje && typeof v === "number" ? Math.round(v * 100 * 1e6) / 1e6 : v]));
  switch (e.type) {
    case "missing": return "Campo obligatorio";
    case "int_parsing": case "int_type": case "int_from_float": return "Introduzca un número entero";
    case "float_parsing": case "float_type": case "decimal_parsing": return "Introduzca un número";
    case "bool_parsing": case "bool_type": return "Indique sí o no";
    case "greater_than": return `Debe ser mayor que ${cifra(ctx.gt)}`;
    case "greater_than_equal": return `No puede ser menor que ${cifra(ctx.ge)}`;
    case "less_than": return `Debe ser menor que ${cifra(ctx.lt)}`;
    case "less_than_equal": return `No puede ser mayor que ${cifra(ctx.le)}`;
    case "string_too_long": return "Texto demasiado largo";
    case "date_parsing": case "date_from_datetime_parsing": return "Introduzca una fecha válida";
    default: return "valor no válido";
  }
}

/** Nombre legible de una ruta sin campo: «Activo › atributos › banos». */
function rutaLegible(partes: (string | number)[]): string {
  if (partes.length === 0) return "Datos del análisis";
  const [primera, ...resto] = partes.map(String);
  return [primera.charAt(0).toUpperCase() + primera.slice(1).replace(/_/g, " "), ...resto].join(" › ");
}

/**
 * @param detail   `detail` de la respuesta 422 (lista de errores de Pydantic).
 * @param existeCampo  dice si una ruta corresponde a un campo del formulario.
 * @param enFraccion  rutas que el formulario envía divididas por 100.
 */
export function traducir422(detail: unknown, existeCampo: (ruta: string) => boolean,
                            enFraccion: ReadonlySet<string> = new Set()): Traduccion {
  const salida: Traduccion = { campos: {}, generales: [] };
  if (typeof detail === "string") return { campos: {}, generales: [detail] };
  if (!Array.isArray(detail)) return salida;

  for (const bruto of detail as ErrorPydantic[]) {
    const loc = Array.isArray(bruto?.loc) ? bruto.loc : [];
    const partes = loc[0] === "body" ? loc.slice(1) : loc;
    const ruta = partes.join(".");
    const texto = mensaje(bruto ?? {}, enFraccion.has(ruta));
    if (ruta && existeCampo(ruta)) {
      if (!(ruta in salida.campos)) salida.campos[ruta] = texto.charAt(0).toUpperCase() + texto.slice(1);
    } else {
      salida.generales.push(`${rutaLegible(partes)}: ${texto}`);
    }
  }
  return salida;
}

/** Claves propias de un error de react-hook-form, que no son campos. */
const CLAVES_DE_ERROR = new Set(["message", "type", "types", "ref", "root"]);

/**
 * Rutas de los campos con error en el objeto `formState.errors` de
 * react-hook-form, en el orden en que aparecen. Un error de lista entera (p. ej.
 * «Añada al menos un comparable», en `message` o en `root`) cuenta como la ruta
 * de la lista.
 */
export function rutasConError(errores: unknown, prefijo = ""): string[] {
  if (errores === null || typeof errores !== "object") return [];
  const nodo = errores as Record<string, unknown>;
  const propio = typeof nodo.message === "string"
    || (typeof nodo.root === "object" && nodo.root !== null
        && typeof (nodo.root as Record<string, unknown>).message === "string");
  const hijos = Object.entries(nodo)
    .filter(([k]) => !CLAVES_DE_ERROR.has(k))
    .flatMap(([k, v]) => rutasConError(v, prefijo ? `${prefijo}.${k}` : k));
  return propio && prefijo ? [prefijo, ...hijos] : hijos;
}

/** Índice del primer paso del asistente que contiene alguna de las rutas. */
export function primerPasoConError(rutas: string[]): number | undefined {
  const pasos = rutas.map(pasoDeRuta).filter((p): p is number => p !== undefined);
  return pasos.length ? Math.min(...pasos) : undefined;
}

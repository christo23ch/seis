/**
 * Fase 5I-E — coordenadas aproximadas desde la provincia (lógica pura, con tests
 * en `tests/provincias.test.ts`).
 *
 * Al elegir la provincia, si lat/lng están vacías se rellenan con la de su
 * capital (`lib/provincias.ts`, CartoCiudad/IGN). Se marcan «aproximada
 * (provincia)» mientras coincidan con esa coordenada. Nunca pisan una escrita a
 * mano. El motor no usa lat/lng (solo el mapa): una coordenada aproximada no
 * cambia ningún cálculo.
 */
import { aNumero } from "@/lib/formulario";
import { PROVINCIAS, type Provincia } from "@/lib/provincias";

export interface Coordenada { lat: number; lng: number; }

export const coordenadaDeProvincia = (provincia: string | undefined): Provincia | undefined =>
  PROVINCIAS.find((p) => p.provincia === provincia);

const leer = (v: unknown) => aNumero(v, { puntoDeMiles: false });

/** ¿lat/lng son exactamente la coordenada de referencia de la provincia? */
export function esCoordenadaDeProvincia(actual: { lat: unknown; lng: unknown }, provincia: string | undefined): boolean {
  const p = coordenadaDeProvincia(provincia);
  return !!p && leer(actual.lat) === p.lat && leer(actual.lng) === p.lng;
}

/** ¿Son lat/lng la coordenada aproximada de ALGUNA provincia? Decide sin estado:
 * no hace falta recordar cuál se eligió antes (un `useRef` se quedaba desfasado
 * al pasar por «Seleccione…» o al reiniciar el formulario). */
export const esAproximadaDeAlgunaProvincia = (actual: { lat: unknown; lng: unknown }) =>
  PROVINCIAS.some((p) => esCoordenadaDeProvincia(actual, p.provincia));

/**
 * Qué hacer con lat/lng al cambiar de provincia:
 *   · vacías, o la aproximada de alguna provincia (nadie las escribió) ⇒ la de la
 *     nueva provincia;
 *   · si la nueva no es una provincia (p. ej. «Seleccione…») y había una
 *     aproximada ⇒ `"vaciar"`: dejarla haría pasar por exacta una coordenada que
 *     ya no se marca como aproximada;
 *   · cualquier otra cosa (escrita a mano, aunque sea una sola) ⇒ `null`, no se toca.
 */
export function coordenadasAlCambiarProvincia(
  actual: { lat: unknown; lng: unknown }, nueva: string,
): Coordenada | "vaciar" | null {
  const vacias = leer(actual.lat) === undefined && leer(actual.lng) === undefined;
  const aproximada = esAproximadaDeAlgunaProvincia(actual);
  const destino = coordenadaDeProvincia(nueva);
  if (!destino) return aproximada ? "vaciar" : null;
  if (!vacias && !aproximada) return null;
  return { lat: destino.lat, lng: destino.lng };
}

"use client";
import { construirArbol, type Nodo } from "@/lib/presentacion-valores";
import { ETIQUETAS_ENTRADA, SECCIONES_ENTRADA } from "@/lib/etiquetas-entrada";
import { ConVerJson, SeccionPlegable } from "./arbol-valores";

/** Fase 5K-B — «Datos de entrada» de un análisis, por los pasos del asistente, con los
 * mismos nombres y unidades y los valores en formato español. «Ver JSON» conserva la
 * vista anterior para quien la necesite. */
export function DatosEntrada({ entrada }: { entrada: Record<string, unknown> }) {
  const usadas = new Set(SECCIONES_ENTRADA.flatMap((s) => s.claves));
  const secciones = [
    ...SECCIONES_ENTRADA.map((s) => ({ titulo: s.titulo, nodos: nodosDe(entrada, s.claves) })),
    { titulo: "Otros datos", nodos: nodosDe(entrada, Object.keys(entrada).filter((k) => !usadas.has(k))) },
  ].filter((s) => s.nodos.length > 0);
  return (
    <ConVerJson json={entrada}>
      <div className="space-y-2">
        {secciones.map((s, i) => <SeccionPlegable key={s.titulo} titulo={s.titulo} nodos={s.nodos} abierta={i === 0} />)}
      </div>
    </ConVerJson>
  );
}

/** Nodos de unas claves de primer nivel. Si la sección es un solo grupo («subasta»),
 * se muestran sus hijos directamente: el título de la sección ya lo nombra. */
function nodosDe(entrada: Record<string, unknown>, claves: string[]): Nodo[] {
  const presentes = Object.fromEntries(claves.filter((k) => entrada[k] !== undefined && entrada[k] !== null).map((k) => [k, entrada[k]]));
  const nodos = construirArbol(presentes, { etiquetas: ETIQUETAS_ENTRADA });
  return nodos.flatMap((n) => (n.tipo === "grupo" && nodos.length === 1 ? n.hijos : [n]));
}

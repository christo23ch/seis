/**
 * Fase 5K-B — nombres y unidades del catálogo de parámetros (el mismo que usan las
 * Simulaciones) indexados por clave, para presentar el árbol T3 legible.
 *
 * La API solo expone el catálogo por análisis (`/analisis/{id}/parametros-simulables`).
 * Sus nombres y unidades no dependen del análisis (solo el valor original lo hace), así
 * que, sin análisis concreto, se pide el del más reciente. Si la organización aún no
 * tiene ninguno, el mapa queda vacío y las claves se humanizan. Un endpoint global del
 * catálogo es deuda del backend (`docs/DEUDA_PRESENTACION_MOTOR.md`).
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ParametrosSimulables } from "@/lib/types";

export type CatalogoPorClave = ReadonlyMap<string, { nombre: string; unidad?: string }>;

export function indexarCatalogo(c: ParametrosSimulables | undefined): CatalogoPorClave {
  const mapa = new Map<string, { nombre: string; unidad?: string }>();
  if (!c) return mapa;
  for (const p of c.no_editables) mapa.set(p.clave, { nombre: p.nombre_legible, unidad: p.unidad || undefined });
  for (const p of c.editables) mapa.set(p.clave, { nombre: p.nombre_legible, unidad: p.unidad || undefined });
  return mapa;
}

/** Catálogo por clave. Con `analisisId`, el de ese análisis; sin él, el del más reciente. */
export function useCatalogoParametros(analisisId?: string): CatalogoPorClave {
  const lista = useQuery({ queryKey: ["analisis"], queryFn: api.listar, enabled: !analisisId, staleTime: 60_000 });
  const id = analisisId ?? lista.data?.[0]?.id;
  const cat = useQuery({
    queryKey: ["parametros-simulables", id], queryFn: () => api.parametrosSimulables(id!),
    enabled: !!id, staleTime: 5 * 60_000, retry: false,
  });
  return indexarCatalogo(cat.data);
}

/**
 * Fase 5K-E — pesos del desglose del ICO leídos del catálogo, no escritos en el frontend.
 *
 * Antes, `resultado.tsx` copiaba los pesos de `defaults.yaml` (`ico.pesos`): si alguien
 * los cambiaba en el catálogo T3, las barras se dibujaban con el máximo equivocado sin
 * que nada avisara. Los pesos correctos son los de los parámetros QUE PRODUJERON el
 * resultado que se está viendo:
 *   · configuración original de un análisis → valor ORIGINAL del catálogo (snapshot);
 *   · simulación validada → sus `parametros_aplicados`;
 *   · asistente (aún sin guardar) → valor VIGENTE (el conocimiento actual, que es el
 *     que usa `/analisis/simular`).
 * Si no se conocen (análisis anterior al snapshot 0014, o sin catálogo), `null`: se
 * muestran los puntos sin máximo, nunca un peso supuesto.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { valorEnRuta } from "@/lib/presentacion-valores";
import type { ParametrosSimulables, ValorJson } from "@/lib/types";

export type PesosIco = Record<string, number>;
const PREFIJO = "ico.pesos.";

/** Pesos del catálogo de un análisis: los originales (snapshot) o los vigentes. */
export function pesosIcoDeCatalogo(c: ParametrosSimulables | undefined, fuente: "original" | "vigente"): PesosIco | null {
  if (!c) return null;
  const pesos: PesosIco = {};
  for (const p of c.editables) {
    if (!p.clave.startsWith(PREFIJO)) continue;
    const v: ValorJson | null = fuente === "original" ? p.valor_original : p.valor_vigente;
    if (typeof v !== "number") return null;           // sin snapshot (o dato raro): no se supone nada
    pesos[p.clave.slice(PREFIJO.length)] = v;
  }
  return Object.keys(pesos).length ? pesos : null;
}

/** Pesos de un árbol de parámetros aplicados (simulación, informe). */
export function pesosIcoDeArbol(arbol: unknown): PesosIco | null {
  const v = valorEnRuta(arbol, "ico.pesos");
  if (typeof v !== "object" || v === null || Array.isArray(v)) return null;
  const entradas = Object.entries(v as Record<string, unknown>);
  if (!entradas.length || !entradas.every(([, x]) => typeof x === "number")) return null;
  return Object.fromEntries(entradas) as PesosIco;
}

export interface PesosIcoEstado {
  pesos: PesosIco | null;
  /** Por qué no hay pesos, si no los hay: el aviso dice la verdad en cada caso. */
  motivo: "cargando" | "sin_catalogo" | "sin_snapshot" | "sin_analisis" | null;
}

/**
 * Pesos del ICO para el resultado mostrado.
 *   · `analisisId` + `simulacionId` → los de esa simulación;
 *   · `analisisId` sin simulación → los originales del análisis;
 *   · nada (asistente) → los vigentes, vía el catálogo del análisis más reciente.
 */
export function usePesosIco(analisisId?: string, simulacionId?: string | null): PesosIcoEstado {
  const sim = useQuery({
    queryKey: ["simulacion", analisisId, simulacionId],
    queryFn: () => api.simulaciones.obtener(analisisId!, simulacionId!),
    enabled: !!analisisId && !!simulacionId, staleTime: 60_000,
  });
  const lista = useQuery({ queryKey: ["analisis"], queryFn: api.listar, enabled: !analisisId, staleTime: 60_000 });
  const idCatalogo = analisisId ?? lista.data?.[0]?.id;
  const cat = useQuery({
    queryKey: ["parametros-simulables", idCatalogo], queryFn: () => api.parametrosSimulables(idCatalogo!),
    enabled: !!idCatalogo && !simulacionId, staleTime: 5 * 60_000, retry: false,
  });
  if (simulacionId) {
    if (sim.isPending) return { pesos: null, motivo: "cargando" };
    const pesos = pesosIcoDeArbol(sim.data?.parametros_aplicados);
    return { pesos, motivo: pesos ? null : sim.isError ? "sin_catalogo" : "sin_snapshot" };
  }
  if (!idCatalogo) {
    if (lista.isPending) return { pesos: null, motivo: "cargando" };
    return { pesos: null, motivo: lista.isError ? "sin_catalogo" : "sin_analisis" };
  }
  if (cat.isPending) return { pesos: null, motivo: "cargando" };
  const pesos = pesosIcoDeCatalogo(cat.data, analisisId ? "original" : "vigente");
  return { pesos, motivo: pesos ? null : cat.isError ? "sin_catalogo" : analisisId ? "sin_snapshot" : "sin_catalogo" };
}

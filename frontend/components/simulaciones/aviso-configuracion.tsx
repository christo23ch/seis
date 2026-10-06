"use client";
import { type QueryClient, useIsMutating, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fecha } from "@/lib/format";
import { puedeEscribir } from "@/lib/permisos";
import type { EstadoSimulacion } from "@/lib/types";
import { Button, ErrorBox } from "@/components/ui";

const ESTADO: Record<EstadoSimulacion, string> = {
  pendiente: "pendiente de revisión", validada: "validada", descartada: "descartada",
};

export const idCorto = (id: string) => id.slice(0, 8);

/** Todo lo que depende de la configuración seleccionada o del estado de las
 * simulaciones. Única lista de claves: la usan el aviso y la pestaña
 * Simulaciones, para que ninguna escritura deje una vista desactualizada.
 * La vista previa y el resto de pestañas leen de `["detalle", id]`. */
export function invalidarConfiguracion(qc: QueryClient, analisisId: string) {
  for (const clave of ["detalle", "simulaciones", "simulacion", "comparacion"]) {
    qc.invalidateQueries({ queryKey: [clave, analisisId] });
  }
}

/** Clave común de TODAS las escrituras de simulaciones de un análisis (crear,
 * validar, descartar, seleccionar, volver a la original), estén en el aviso o
 * en la pestaña. Con ella, `useIsMutating` sabe si hay alguna en curso y los
 * botones de otro componente se desactivan (mitiga la carrera descartar/validar). */
export const claveEscrituraSimulaciones = (analisisId: string) => ["escritura-simulaciones", analisisId];

/** Dice SIEMPRE qué configuración está pintando el detalle: la original del
 * análisis o una simulación seleccionada. Sin colores del semáforo; el estado
 * va en texto. No deduce nada: si el puntero no aparece en el listado como
 * configuración actual, dice «original» y no inventa datos. */
export function AvisoConfiguracion({ analisisId, simulacionValidadaId }: {
  analisisId: string; simulacionValidadaId: string | null;
}) {
  const qc = useQueryClient();
  const { usuario } = useAuth();

  const lista = useQuery({
    queryKey: ["simulaciones", analisisId],
    queryFn: () => api.simulaciones.listar(analisisId),
    enabled: simulacionValidadaId != null,
  });
  const fila = lista.data?.find((s) => s.es_configuracion_actual && s.id === simulacionValidadaId);
  // `version_parametros_base` no viene en el listado: se pide el detalle solo si hay fila.
  const detalle = useQuery({
    queryKey: ["simulacion", analisisId, fila?.id],
    queryFn: () => api.simulaciones.obtener(analisisId, fila!.id),
    enabled: fila != null,
  });

  const volver = useMutation({
    mutationKey: claveEscrituraSimulaciones(analisisId),
    mutationFn: () => api.simulaciones.volverAOriginal(analisisId),
    onSuccess: () => invalidarConfiguracion(qc, analisisId),
  });
  // Cualquier escritura de simulaciones en curso (también las de la pestaña).
  const escribiendo = useIsMutating({ mutationKey: claveEscrituraSimulaciones(analisisId) }) > 0;

  if (simulacionValidadaId == null || (lista.isSuccess && !fila)) {
    return (
      <Caja>
        <p className="font-semibold text-tinta">Configuración original del análisis</p>
        <p className="text-[13px] text-slate-500">Los resultados de todas las pestañas son los del análisis tal como se creó.</p>
      </Caja>
    );
  }

  if (lista.isPending) {
    return <Caja><p className="text-slate-500">Comprobando qué configuración se muestra…</p></Caja>;
  }

  if (lista.isError || !fila) {
    return (
      <Caja simulacion>
        <p className="font-semibold text-tinta">Mostrando una simulación seleccionada ({idCorto(simulacionValidadaId)})</p>
        <p className="text-[13px] text-sem-rojo">No se pudieron cargar sus datos: {(lista.error as Error | null)?.message ?? "error desconocido"}</p>
      </Caja>
    );
  }

  const n = Object.keys(fila.overrides).length;
  const version = detalle.data?.version_parametros_base;
  return (
    <Caja simulacion>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="font-semibold text-tinta">
            Mostrando la simulación <span className="cifra">{idCorto(fila.id)}</span>
          </p>
          <p className="text-[13px] text-slate-600">
            {ESTADO[fila.estado]}, creada {fecha(fila.creado_en)}, {n} {n === 1 ? "override" : "overrides"}
            {" · "}parámetros de la simulación{" "}
            <span className="cifra">{version ? `v${version}` : detalle.isError ? "no disponibles" : "…"}</span>
          </p>
        </div>
        {puedeEscribir(usuario) && (
          <Button variante="secundario" className="shrink-0" cargando={volver.isPending}
            disabled={escribiendo} aria-disabled={escribiendo} onClick={() => volver.mutate()}>
            Volver a la configuración original
          </Button>
        )}
      </div>
      {volver.isError && <div className="mt-3"><ErrorBox mensaje={(volver.error as Error).message} /></div>}
    </Caja>
  );
}

function Caja({ simulacion = false, children }: { simulacion?: boolean; children: React.ReactNode }) {
  return (
    <section role="status" aria-live="polite" aria-label="Configuración mostrada"
      className={`rounded-md border px-4 py-3 text-sm ${
        simulacion ? "border-primario/30 bg-primario-tenue" : "border-borde-linea bg-papel-carta"}`}>
      {children}
    </section>
  );
}

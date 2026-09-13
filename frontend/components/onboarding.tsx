"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Circle, Loader2 } from "lucide-react";
import { api, type PasoOnboarding } from "@/lib/api";
import { rutaApp } from "@/lib/rutas";

// Checklist de arranque. Desaparece sola cuando está completa: un panel de
// «primeros pasos» que sigue ahí el sexto mes es ruido, no ayuda.
//
// Lo que la hace honesta es `origen`. Un paso `datos` NO tiene casilla que
// pulsar: su verdad está en la base —hay un análisis o no lo hay— y ofrecer un
// visto invitaría a declarar un hecho que el sistema puede comprobar. Solo los
// `declarado` se marcan a mano.
export function Onboarding() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["onboarding"], queryFn: api.onboarding });
  const marcar = useMutation({
    mutationFn: api.marcarPasoOnboarding,
    onSuccess: (nuevo) => qc.setQueryData(["onboarding"], nuevo),
  });

  if (isLoading || !data || data.terminado) return null;

  return (
    <section aria-labelledby="onboarding-titulo"
      className="rounded-lg border border-borde-linea bg-papel-carta p-5 shadow-carta">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="onboarding-titulo" className="h-display text-h3 font-semibold text-tinta">
          Primeros pasos
        </h2>
        <span className="font-cifra text-menor tabular-nums text-tinta-suave">
          {data.completados} de {data.total}
        </span>
      </div>

      <ol className="mt-4 divide-y divide-borde-linea">
        {data.pasos.map((p) => (
          <li key={p.clave} className="flex flex-wrap items-start gap-3 py-3">
            <Marca completado={p.completado} />
            <div className="min-w-0 flex-1">
              <div className={`text-base font-medium ${p.completado ? "text-tinta-suave line-through" : "text-tinta"}`}>
                {p.titulo}
              </div>
              <p className="mt-0.5 text-menor text-tinta-suave">{p.descripcion}</p>
            </div>
            <Accion paso={p} pendiente={marcar.isPending && marcar.variables === p.clave}
              onMarcar={() => marcar.mutate(p.clave)} />
          </li>
        ))}
      </ol>

      {marcar.isError && (
        <p className="mt-3 text-menor text-sem-rojo">No se pudo guardar el paso. Inténtalo otra vez.</p>
      )}
    </section>
  );
}

function Marca({ completado }: { completado: boolean }) {
  return completado
    ? <Check className="mt-1 h-4 w-4 shrink-0 text-sem-verde" aria-label="Hecho" />
    : <Circle className="mt-1 h-4 w-4 shrink-0 text-borde-control" aria-label="Pendiente" />;
}

function Accion({ paso, pendiente, onMarcar }: {
  paso: PasoOnboarding; pendiente: boolean; onMarcar: () => void;
}) {
  if (paso.completado) return null;

  // Paso deducido: solo se puede ir a hacerlo. No hay casilla, a propósito.
  if (paso.origen === "datos") {
    return paso.accion ? (
      <Link href={rutaApp(paso.accion)}
        className="rounded-md border border-borde-control px-3 py-1.5 text-menor font-medium text-tinta hover:bg-papel">
        Ir
      </Link>
    ) : null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {paso.accion && (
        <Link href={paso.accion.startsWith("/ayuda") ? paso.accion : rutaApp(paso.accion)}
          className="rounded-md border border-borde-control px-3 py-1.5 text-menor font-medium text-tinta hover:bg-papel">
          Ver
        </Link>
      )}
      <button type="button" onClick={onMarcar} disabled={pendiente}
        className="flex items-center gap-1.5 rounded-md bg-primario px-3 py-1.5 text-menor font-medium text-white hover:bg-primario-hover disabled:opacity-50">
        {pendiente && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
        Marcar como hecho
      </button>
    </div>
  );
}

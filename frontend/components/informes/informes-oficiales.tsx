"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, guardarBlob } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fecha } from "@/lib/format";
import { puedeEscribir } from "@/lib/permisos";
import type { Detalle, InformeOficialResumen, SimulacionResumen, ValorJson } from "@/lib/types";
import { SemaforoBadge } from "@/components/resultado";
import { Button, Card, CardContent, CardHeader, CardTitle, Confirmacion, ErrorBox, Spinner } from "@/components/ui";
import { idCorto, invalidarConfiguracion } from "@/components/simulaciones/aviso-configuracion";

/** Pestaña «Informes oficiales» (API de la Fase 5F.4).
 *
 * Un informe oficial es un SNAPSHOT INMUTABLE de la configuración en uso en el
 * instante de emitirlo. Esta pestaña nunca lo regenera ni lo presenta como si
 * dependiera de la configuración actual: lo que muestra y el PDF que descarga
 * salen del contenido congelado. Por eso cambiar la configuración no invalida
 * `["informes", id]`; solo emitir uno nuevo lo hace. */
export function InformesOficiales({ detalle }: { detalle: Detalle }) {
  const analisisId = detalle.id;
  const qc = useQueryClient();
  const { usuario } = useAuth();
  const escribe = puedeEscribir(usuario);
  const [abierto, setAbierto] = useState<string | null>(null);
  const [confirmar, setConfirmar] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emitido, setEmitido] = useState<string | null>(null);

  const informes = useQuery({
    queryKey: ["informes", analisisId],
    queryFn: () => api.informes.listar(analisisId),
  });
  // Misma clave que la lista y el aviso: da el estado de la simulación de procedencia.
  const simulaciones = useQuery({
    queryKey: ["simulaciones", analisisId],
    queryFn: () => api.simulaciones.listar(analisisId),
  });

  const emitir = useMutation({
    mutationFn: () => api.informes.emitir(analisisId),
    onMutate: () => { setError(null); setEmitido(null); },
    onSuccess: (informe) => {
      qc.invalidateQueries({ queryKey: ["informes", analisisId] });
      setAbierto(informe.id);
      setEmitido(informe.id);
    },
    onError: (e: Error) => {
      setError(e.message);
      // 409: la configuración seleccionada no se puede resolver (se cambió en otro
      // sitio o quedó inconsistente): se vuelve a pedir todo lo que depende de ella.
      if (e instanceof ApiError && e.status === 409) invalidarConfiguracion(qc, analisisId);
    },
  });

  const informeNoExiste = useCallback(() => {
    setAbierto(null);
    setError("El informe no existe o no pertenece a este análisis.");
    qc.invalidateQueries({ queryKey: ["informes", analisisId] });
  }, [qc, analisisId]);

  const enUso = detalle.simulacion_validada_id;
  const textoConfirmacion = `Se congelará la configuración ${
    enUso ? `de la simulación ${idCorto(enUso)}` : "original del análisis"} tal como está ahora. `
    + "El informe no cambiará aunque después cambie la configuración seleccionada.";

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>Informes oficiales</CardTitle>
        {escribe && (
          <Button className="!px-2.5 !py-1.5" cargando={emitir.isPending} disabled={emitir.isPending}
            aria-disabled={emitir.isPending} onClick={() => setConfirmar(true)}>
            Emitir informe oficial
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-[13px] text-slate-600">
          Cada informe oficial es un documento congelado: no cambia aunque después cambie la configuración
          del análisis. Para ver la configuración actual sin congelarla, use la «Vista previa (no oficial)».
        </p>
        {emitido && (
          <p role="status" className="rounded-md border border-primario/30 bg-primario-tenue/40 px-3.5 py-2 text-[13px] text-tinta">
            Informe oficial <span className="cifra">{idCorto(emitido)}</span> emitido.
          </p>
        )}
        {error && <ErrorBox mensaje={error} />}

        {informes.isPending && <Spinner />}
        {informes.isError && <ErrorBox mensaje={`No se pudieron cargar los informes: ${informes.error.message}`} />}
        {informes.data && informes.data.length === 0 && (
          <p className="text-sm text-slate-500">Este análisis todavía no tiene informes oficiales.</p>
        )}
        {informes.data && informes.data.length > 0 && (
          <Historico informes={informes.data} simulaciones={simulaciones.data} abierto={abierto}
            abrir={(id) => { setError(null); setAbierto(id); }} />
        )}

        {abierto && (
          <InformeDetalle key={abierto} analisisId={analisisId} informeId={abierto}
            simulaciones={simulaciones.data} onCerrar={() => setAbierto(null)} onNoExiste={informeNoExiste} />
        )}
      </CardContent>

      <Confirmacion abierta={confirmar} titulo="Emitir informe oficial" texto={textoConfirmacion} boton="Emitir"
        onCancelar={() => setConfirmar(false)}
        onConfirmar={() => { setConfirmar(false); emitir.mutate(); }} />
    </Card>
  );
}

// ─────────────────────────── procedencia ───────────────────────────

/** «Original» o «Simulación {id}» y, si esa simulación sigue en la lista, su
 * estado en palabra. Si no aparece, solo el id: no se inventa nada. */
function Procedencia({ simulacionId, simulaciones }: {
  simulacionId: string | null; simulaciones: SimulacionResumen[] | undefined;
}) {
  if (simulacionId === null) return <span>Original</span>;
  const sim = simulaciones?.find((s) => s.id === simulacionId);
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span>Simulación <span className="cifra">{idCorto(simulacionId)}</span></span>
      {sim && <span className="rounded-full border border-borde-control px-2 py-0.5 text-[11px] font-semibold">{sim.estado}</span>}
    </span>
  );
}

// ─────────────────────────── histórico ───────────────────────────

function Historico({ informes, simulaciones, abierto, abrir }: {
  informes: InformeOficialResumen[]; simulaciones: SimulacionResumen[] | undefined;
  abierto: string | null; abrir: (id: string) => void;
}) {
  return (
    <>
      {/* ≥ md: tabla; < md: tarjetas. El backend ya los da del más reciente al más antiguo. */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[640px] text-[13px]">
          <thead>
            <tr className="border-b border-borde-linea text-left text-[12px] uppercase tracking-wide text-slate-500">
              <th className="px-3.5 py-1.5 font-semibold">Emitido</th>
              <th className="px-3.5 py-1.5 font-semibold">Procedencia</th>
              <th className="px-3.5 py-1.5 font-semibold">Semáforo</th>
              <th className="px-3.5 py-1.5 text-right font-semibold">ICO</th>
              <th className="px-3.5 py-1.5 text-right font-semibold"><span className="sr-only">Abrir</span></th>
            </tr>
          </thead>
          <tbody>
            {informes.map((i) => (
              <tr key={i.id} data-informe={i.id}
                className={`border-b border-borde-linea ${abierto === i.id ? "bg-primario-tenue/40" : ""}`}>
                <td className="px-3.5 py-1.5 text-slate-700">{fecha(i.generado_en)}</td>
                <td className="px-3.5 py-1.5"><Procedencia simulacionId={i.simulacion_id} simulaciones={simulaciones} /></td>
                <td className="px-3.5 py-1.5">{i.semaforo ? <SemaforoBadge s={i.semaforo} /> : "—"}</td>
                <td className="cifra px-3.5 py-1.5 text-right">{i.ico ?? "—"}</td>
                <td className="px-3.5 py-1.5 text-right">
                  <Button variante="secundario" className="!px-2.5 !py-1" onClick={() => abrir(i.id)}>Abrir</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="space-y-2.5 md:hidden">
        {informes.map((i) => (
          <li key={i.id} data-informe={i.id}
            className={`rounded-md border px-3.5 py-3 text-[13px] ${abierto === i.id ? "border-primario/40 bg-primario-tenue/40" : "border-borde-linea"}`}>
            <p className="text-slate-700">Emitido {fecha(i.generado_en)}</p>
            <p className="mt-1"><Procedencia simulacionId={i.simulacion_id} simulaciones={simulaciones} /></p>
            <div className="mt-1.5 flex flex-wrap items-center gap-3">
              {i.semaforo ? <SemaforoBadge s={i.semaforo} /> : <span>Semáforo —</span>}
              <span>ICO <span className="cifra font-semibold">{i.ico ?? "—"}</span></span>
              <Button variante="secundario" className="ml-auto !px-2.5 !py-1" onClick={() => abrir(i.id)}>Abrir</Button>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

// ─────────────────────────── detalle ───────────────────────────

function InformeDetalle({ analisisId, informeId, simulaciones, onCerrar, onNoExiste }: {
  analisisId: string; informeId: string; simulaciones: SimulacionResumen[] | undefined;
  onCerrar: () => void; onNoExiste: () => void;
}) {
  const ref = useRef<HTMLElement>(null);
  const [descargando, setDescargando] = useState(false);
  const [errorPdf, setErrorPdf] = useState<string | null>(null);
  const informe = useQuery({
    queryKey: ["informes", analisisId, informeId],
    queryFn: () => api.informes.obtener(analisisId, informeId),
  });

  useEffect(() => { ref.current?.scrollIntoView({ block: "start", behavior: "smooth" }); }, [informeId]);
  useEffect(() => {
    if (informe.error instanceof ApiError && informe.error.status === 404) onNoExiste();
  }, [informe.error, onNoExiste]);

  async function descargar() {
    if (!informe.data) return;
    setDescargando(true);
    setErrorPdf(null);
    try {
      const blob = await api.informes.descargarPdf(analisisId, informeId);
      // Fecha de EMISIÓN del informe, no la de hoy: el fichero identifica el documento congelado.
      const dia = (informe.data.generado_en ?? "").slice(0, 10) || "sin-fecha";
      guardarBlob(blob, `SEIS_informe_oficial_${idCorto(informeId)}_${dia}.pdf`);
    } catch (e) {
      setErrorPdf((e as Error).message);
    } finally {
      setDescargando(false);
    }
  }

  const i = informe.data;
  const overrides = i ? Object.entries(i.overrides) : [];
  return (
    <section ref={ref} aria-label="Informe oficial" className="scroll-mt-16 rounded-md border border-primario/30 md:scroll-mt-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-borde-linea px-4 py-2.5">
        <h3 className="text-sm font-semibold text-tinta">
          Informe oficial <span className="cifra">{idCorto(informeId)}</span>
        </h3>
        <div className="flex flex-wrap gap-2">
          {i && (
            <Button variante="secundario" className="!px-2.5 !py-1.5" cargando={descargando} onClick={descargar}>
              Descargar PDF oficial
            </Button>
          )}
          <Button variante="fantasma" className="!px-2 !py-1 text-[12px]" onClick={onCerrar}>Cerrar</Button>
        </div>
      </div>
      <div className="space-y-3 px-4 py-3 text-[13px]">
        {informe.isPending && <Spinner />}
        {informe.isError && !(informe.error instanceof ApiError && informe.error.status === 404) && (
          <ErrorBox mensaje={`No se pudo cargar el informe: ${informe.error.message}`} />
        )}
        {errorPdf && <ErrorBox mensaje={`No se pudo descargar el PDF: ${errorPdf}`} />}
        {i && (
          <>
            <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
              <dt className="text-slate-500">Emitido</dt>
              <dd>{fecha(i.generado_en)}</dd>
              <dt className="text-slate-500">Procedencia</dt>
              <dd data-procedencia><Procedencia simulacionId={i.simulacion_id} simulaciones={simulaciones} /></dd>
              <dt className="text-slate-500">Cambios aplicados</dt>
              <dd>
                {overrides.length === 0 ? "Ninguno" : (
                  <ul className="space-y-1">
                    {overrides.map(([clave, valor]) => (
                      <li key={clave} className="break-all">
                        <span className="cifra text-[12px]">{clave}</span> → <Valor v={valor} />
                      </li>
                    ))}
                  </ul>
                )}
              </dd>
            </dl>
            {i.parametros_aplicados === null && (
              <p role="note" className="rounded-md border border-borde-linea bg-papel-carta px-3 py-2 text-tinta">
                Sin snapshot de parámetros (análisis anterior al registro de parámetros).
              </p>
            )}
            {/* El Markdown CONGELADO del informe, mostrado igual que la vista previa. */}
            <pre data-markdown className="max-h-[70vh] overflow-auto whitespace-pre-wrap font-cifra text-[12.5px] leading-relaxed text-slate-700">
              {i.resultado.informe_markdown}
            </pre>
          </>
        )}
      </div>
    </section>
  );
}

function Valor({ v }: { v: ValorJson }) {
  if (v === null || typeof v !== "object") return <span className="cifra">{v === null ? "—" : String(v)}</span>;
  return (
    <details className="inline-block align-top">
      <summary className="cursor-pointer text-[12px] text-slate-600">
        {Array.isArray(v) ? `lista de ${v.length}` : `objeto de ${Object.keys(v).length} claves`}
      </summary>
      <pre className="cifra mt-1 max-w-full overflow-auto whitespace-pre-wrap break-all rounded bg-slate-50 p-2 text-[11px]">
        {JSON.stringify(v, null, 2)}
      </pre>
    </details>
  );
}

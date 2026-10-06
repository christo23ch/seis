"use client";
import { useCallback, useState } from "react";
import { type UseQueryResult, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { eur, fecha } from "@/lib/format";
import { puedeEscribir } from "@/lib/permisos";
import type {
  ComparacionSimulacion, Detalle, EstadoSimulacion, Overrides, Semaforo, SimulacionDetalle, SimulacionResumen,
} from "@/lib/types";
import { SemaforoBadge } from "@/components/resultado";
import { Button, Card, CardContent, CardHeader, CardTitle, Confirmacion, ErrorBox, Spinner } from "@/components/ui";
import { claveEscrituraSimulaciones, idCorto, invalidarConfiguracion } from "./aviso-configuracion";
import { PanelComparacion } from "./comparacion";
import { EditorSimulacion } from "./editor";

type Accion = "validar" | "descartar" | "seleccionar" | "original";
type Peticion = { accion: Accion; id: string | null };

interface Fila {
  clave: string;
  titulo: string;
  estado: EstadoSimulacion | "original";
  enUso: boolean;
  creada: string | null;
  nOverrides: number | null;
  semaforo: Semaforo | null;
  ico: number | null;
  p_objetivo: number | null;
  p_max: number | null;
  nota?: string;                                   // carencia o error de la propia fila
  acciones: { accion: Accion; etiqueta: string; peligro?: boolean }[];
}

// Colores de ESTADO, deliberadamente ajenos a los del semáforo; siempre con su palabra.
const ESTILO_ESTADO: Record<Fila["estado"], { texto: string; clase: string }> = {
  original: { texto: "original", clase: "border border-borde-control bg-papel-carta text-tinta" },
  pendiente: { texto: "pendiente", clase: "border border-dashed border-borde-control bg-white text-tinta" },
  validada: { texto: "validada", clase: "bg-primario-tenue text-primario" },
  descartada: { texto: "descartada", clase: "bg-slate-100 text-slate-500 line-through" },
};

const CONFIRMACION: Partial<Record<Accion, { titulo: string; texto: string; boton: string; peligro?: boolean }>> = {
  validar: {
    titulo: "Validar la simulación",
    texto: "Se validará y pasará a ser la configuración en uso: todas las pestañas mostrarán su resultado. Podrá volver a la original cuando quiera.",
    boton: "Validar",
  },
  descartar: {
    titulo: "Descartar la simulación",
    texto: "Estado definitivo; no se puede deshacer. La simulación se conserva en el histórico, pero no podrá validarse ni usarse.",
    boton: "Descartar", peligro: true,
  },
};

/** Pestaña «Simulaciones»: la configuración original y todas las simulaciones,
 * con las acciones de estado que permite el rol. No decide transiciones: los
 * botones siguen la tabla de estados y, si el backend rechaza algo, manda él. */
export function ListaSimulaciones({ detalle }: { detalle: Detalle }) {
  const analisisId = detalle.id;
  const actualId = detalle.simulacion_validada_id;
  const qc = useQueryClient();
  const { usuario } = useAuth();
  const escribe = puedeEscribir(usuario);
  const [confirmar, setConfirmar] = useState<Peticion | null>(null);
  const [error, setError] = useState<string | null>(null);

  const lista = useQuery({
    queryKey: ["simulaciones", analisisId],
    queryFn: () => api.simulaciones.listar(analisisId),
  });
  // Con una simulación en uso, el detalle ya no trae el resultado original: se
  // lee de la comparación (5F.7.3), que lo sirve desde el snapshot persistido.
  const comparacion = useQuery({
    queryKey: ["comparacion", analisisId, actualId],
    queryFn: () => api.compararSimulacion(analisisId, actualId!),
    enabled: actualId != null,
  });

  const accion = useMutation({
    mutationKey: claveEscrituraSimulaciones(analisisId),
    // La respuesta no se usa: tras cada escritura se vuelve a pedir lo invalidado.
    mutationFn: async ({ accion, id }: Peticion): Promise<void> => {
      if (accion === "original") await api.simulaciones.volverAOriginal(analisisId);
      else await api.simulaciones[accion](analisisId, id!);
    },
    onMutate: () => setError(null),
    onSuccess: () => invalidarConfiguracion(qc, analisisId),
    onError: (e: Error) => {
      const estado = e instanceof ApiError ? e.status : null;
      setError(estado === 404 ? "La simulación no existe o no pertenece a este análisis." : e.message);
      // 409: el estado cambió en otro sitio. 404: la lista está desfasada. En los
      // dos casos se vuelve a pedir todo lo que depende de la configuración.
      if (estado === 409 || estado === 404) invalidarConfiguracion(qc, analisisId);
    },
  });
  // Fase 5F.7.6 — crear. No cambia la configuración en uso: la nueva simulación
  // queda pendiente en la lista y solo se resume lo que devolvió el backend.
  const [editorAbierto, setEditorAbierto] = useState(false);
  const [creada, setCreada] = useState<SimulacionDetalle | null>(null);
  const [errorCrear, setErrorCrear] = useState<string | null>(null);
  const crear = useMutation({
    mutationKey: claveEscrituraSimulaciones(analisisId),
    mutationFn: (overrides: Overrides) => api.simulaciones.crear(analisisId, overrides),
    onMutate: () => { setErrorCrear(null); setCreada(null); },
    onSuccess: (sim) => {
      invalidarConfiguracion(qc, analisisId);
      setCreada(sim);
      setEditorAbierto(false);                 // al desmontarse, el editor descarta sus cambios
    },
    onError: (e: Error) => {
      const estado = e instanceof ApiError ? e.status : null;
      setErrorCrear(estado === 404 ? "El análisis no existe o no pertenece a su organización." : e.message);
    },
  });

  const ocupado = accion.isPending || crear.isPending;

  // Fase 5F.7.7 — una sola comparación abierta a la vez.
  const [comparando, setComparando] = useState<string | null>(null);
  const comparacionNoExiste = useCallback(() => {
    setComparando(null);
    setError("La simulación no existe o no pertenece a este análisis.");
    invalidarConfiguracion(qc, analisisId);
  }, [qc, analisisId]);

  function pedir(p: Peticion) {
    if (CONFIRMACION[p.accion]) setConfirmar(p);
    else accion.mutate(p);
  }

  if (lista.isPending) return <Spinner />;
  if (lista.isError) return <ErrorBox mensaje={`No se pudieron cargar las simulaciones: ${lista.error.message}`} />;

  const filas = [filaOriginal(detalle, comparacion, escribe), ...lista.data.map((s) => filaSimulacion(s, escribe))];
  const dialogo = confirmar ? CONFIRMACION[confirmar.accion] : undefined;

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>Configuraciones del análisis</CardTitle>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-[12px] text-slate-500">
            {lista.data.length} {lista.data.length === 1 ? "simulación" : "simulaciones"}
            {!escribe && " · solo lectura"}
          </span>
          {escribe && !editorAbierto && (
            <Button className="!px-2.5 !py-1.5" disabled={ocupado} aria-disabled={ocupado}
              onClick={() => { setCreada(null); setErrorCrear(null); setEditorAbierto(true); }}>
              Nueva simulación
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {escribe && editorAbierto && (
          <EditorSimulacion analisisId={analisisId} creando={crear.isPending} bloqueado={ocupado}
            error={errorCrear} onCrear={(o) => crear.mutate(o)}
            onCerrar={() => { setEditorAbierto(false); setErrorCrear(null); }} />
        )}
        {creada && (
          <SimulacionCreada sim={creada} onCerrar={() => setCreada(null)} onComparar={() => setComparando(creada.id)} />
        )}
        {error && <ErrorBox mensaje={error} />}
        {comparando && (
          <PanelComparacion key={comparando} analisisId={analisisId} simulacionId={comparando}
            onCerrar={() => setComparando(null)} onNoExiste={comparacionNoExiste} />
        )}
        {lista.data.length === 0 && (
          <p className="text-sm text-slate-500">Este análisis todavía no tiene simulaciones.</p>
        )}

        {/* ≥ md: tabla densa; el contenedor desplaza la tabla, nunca la página. */}
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full min-w-[860px] text-[13px]">
            <thead>
              <tr className="border-b border-borde-linea text-left text-[12px] uppercase tracking-wide text-slate-500">
                <th className="px-3.5 py-1.5 font-semibold">Configuración</th>
                <th className="px-3.5 py-1.5 font-semibold">Estado</th>
                <th className="px-3.5 py-1.5 font-semibold">Creada</th>
                <th className="px-3.5 py-1.5 text-right font-semibold">Overrides</th>
                <th className="px-3.5 py-1.5 font-semibold">Semáforo</th>
                <th className="px-3.5 py-1.5 text-right font-semibold">ICO</th>
                <th className="px-3.5 py-1.5 text-right font-semibold">P. objetivo</th>
                <th className="px-3.5 py-1.5 text-right font-semibold">P. máximo</th>
                <th className="px-3.5 py-1.5 text-right font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.clave} data-fila={f.clave}
                  className={`border-b border-borde-linea align-top ${f.enUso ? "bg-primario-tenue/40" : ""}`}>
                  <td className="px-3.5 py-1.5">
                    <div className="font-medium text-tinta">{f.titulo}</div>
                    {f.nota && <div className="text-[12px] text-sem-rojo">{f.nota}</div>}
                  </td>
                  <td className="px-3.5 py-1.5"><Estado f={f} /></td>
                  <td className="px-3.5 py-1.5 text-slate-600">{f.creada ? fecha(f.creada) : "—"}</td>
                  <td className="cifra px-3.5 py-1.5 text-right">{f.nOverrides ?? "—"}</td>
                  <td className="px-3.5 py-1.5">{f.semaforo ? <SemaforoBadge s={f.semaforo} /> : "—"}</td>
                  <td className="cifra px-3.5 py-1.5 text-right">{f.ico ?? "—"}</td>
                  <td className="cifra px-3.5 py-1.5 text-right">{eur(f.p_objetivo)}</td>
                  <td className="cifra px-3.5 py-1.5 text-right">{eur(f.p_max)}</td>
                  <td className="px-3.5 py-1.5">
                    <Acciones f={f} ocupado={ocupado} pedir={pedir} comparar={setComparando} clase="justify-end" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* < md: tarjetas apiladas con lo imprescindible siempre visible. */}
        <ul className="space-y-2.5 md:hidden">
          {filas.map((f) => (
            <li key={f.clave} data-fila={f.clave}
              className={`rounded-md border px-3.5 py-3 ${f.enUso ? "border-primario/40 bg-primario-tenue/40" : "border-borde-linea"}`}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-tinta">{f.titulo}</span>
                <Estado f={f} />
              </div>
              {f.nota && <p className="mt-1 text-[12px] text-sem-rojo">{f.nota}</p>}
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[13px]">
                {f.semaforo ? <SemaforoBadge s={f.semaforo} /> : <span>Semáforo —</span>}
                <span>ICO <span className="cifra font-semibold">{f.ico ?? "—"}</span></span>
                <span>P. máx. <span className="cifra font-semibold">{eur(f.p_max)}</span></span>
              </div>
              <p className="mt-1 text-[12px] text-slate-500">
                {f.creada ? `Creada ${fecha(f.creada)}` : "—"}
                {f.nOverrides != null && ` · ${f.nOverrides} ${f.nOverrides === 1 ? "override" : "overrides"}`}
                {" · P. obj. "}<span className="cifra">{eur(f.p_objetivo)}</span>
              </p>
              <Acciones f={f} ocupado={ocupado} pedir={pedir} comparar={setComparando} clase="mt-2.5" />
            </li>
          ))}
        </ul>
      </CardContent>

      <Confirmacion
        abierta={!!confirmar && !!dialogo}
        titulo={dialogo?.titulo ?? ""} texto={dialogo?.texto ?? ""}
        boton={dialogo?.boton ?? ""} peligro={dialogo?.peligro}
        onCancelar={() => setConfirmar(null)}
        onConfirmar={() => { if (confirmar) accion.mutate(confirmar); setConfirmar(null); }}
      />
    </Card>
  );
}

// ─────────────────────────── filas ───────────────────────────

function filaOriginal(detalle: Detalle, comparacion: UseQueryResult<ComparacionSimulacion>,
                      escribe: boolean): Fila {
  const enUso = detalle.simulacion_validada_id == null;
  const base = {
    clave: "original", titulo: "Original", estado: "original" as const, enUso,
    creada: detalle.creado_en, nOverrides: null,
    acciones: !enUso && escribe ? [{ accion: "original" as const, etiqueta: "Volver a la original" }] : [],
  };
  if (enUso) {
    const d = detalle.resultado.decision;
    return { ...base, semaforo: d.semaforo, ico: d.ico, p_objetivo: d.precios.p_objetivo, p_max: d.precios.p_max };
  }
  const vacia = { semaforo: null, ico: null, p_objetivo: null, p_max: null };
  if (comparacion.isError) {
    return { ...base, ...vacia, nota: `No se pudo leer el resultado original: ${comparacion.error?.message ?? "error"}` };
  }
  if (!comparacion.data) return { ...base, ...vacia, nota: comparacion.isPending ? "Cargando el resultado original…" : undefined };
  const o = comparacion.data.resultado.original;
  return { ...base, semaforo: o.semaforo, ico: o.ico, p_objetivo: o.p_objetivo, p_max: o.p_max };
}

function filaSimulacion(s: SimulacionResumen, escribe: boolean): Fila {
  const acciones: Fila["acciones"] = [];
  if (escribe && s.estado === "pendiente") {
    acciones.push({ accion: "validar", etiqueta: "Validar" }, { accion: "descartar", etiqueta: "Descartar", peligro: true });
  }
  if (escribe && s.estado === "validada" && !s.es_configuracion_actual) {
    acciones.push({ accion: "seleccionar", etiqueta: "Usar esta configuración" });
  }
  return {
    clave: s.id, titulo: `Simulación ${idCorto(s.id)}`, estado: s.estado, enUso: s.es_configuracion_actual,
    creada: s.creado_en, nOverrides: Object.keys(s.overrides).length,
    semaforo: s.semaforo, ico: s.ico, p_objetivo: s.p_objetivo, p_max: s.p_max, acciones,
  };
}

// ─────────────────────────── piezas ───────────────────────────

/** Resumen de la simulación recién creada, tomado de la respuesta del backend. */
function SimulacionCreada({ sim, onCerrar, onComparar }: {
  sim: SimulacionDetalle; onCerrar: () => void; onComparar: () => void;
}) {
  const d = sim.resultado.decision;
  const n = Object.keys(sim.overrides).length;
  return (
    <div role="status" aria-label="Simulación creada"
      className="flex flex-col gap-2 rounded-md border border-primario/30 bg-primario-tenue/40 px-3.5 py-2.5 text-[13px] sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-semibold text-tinta">Simulación <span className="cifra">{idCorto(sim.id)}</span> creada</span>
        <span className="inline-flex items-center rounded-full border border-dashed border-borde-control bg-white px-2.5 py-0.5 text-[12px] font-semibold text-tinta">
          {sim.estado}
        </span>
        <SemaforoBadge s={d.semaforo} />
        <span>ICO <span className="cifra font-semibold">{d.ico}</span></span>
        <span>P. obj. <span className="cifra font-semibold">{eur(d.precios.p_objetivo)}</span></span>
        <span>P. máx. <span className="cifra font-semibold">{eur(d.precios.p_max)}</span></span>
        <span className="text-slate-500">{n} {n === 1 ? "override" : "overrides"} · no está en uso</span>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <Button variante="secundario" className="!px-2.5 !py-1.5 text-[12px]" onClick={onComparar}>Comparar con original</Button>
        <Button variante="fantasma" className="!px-2 !py-1 text-[12px]" onClick={onCerrar}>Cerrar aviso</Button>
      </div>
    </div>
  );
}

function Estado({ f }: { f: Fila }) {
  const e = ESTILO_ESTADO[f.estado];
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${e.clase}`}>{e.texto}</span>
      {f.enUso && (
        <span className="inline-flex items-center rounded-full bg-primario px-2.5 py-0.5 text-[12px] font-semibold text-white">En uso</span>
      )}
    </span>
  );
}

function Acciones({ f, ocupado, pedir, comparar, clase = "" }: {
  f: Fila; ocupado: boolean; pedir: (p: Peticion) => void; comparar: (id: string) => void; clase?: string;
}) {
  const id = f.clave === "original" ? null : f.clave;
  // «Comparar» es lectura: en todas las simulaciones (también descartadas) y para
  // cualquier rol; no se desactiva mientras hay una escritura en curso.
  if (f.acciones.length === 0 && id === null) return null;
  return (
    <div className={`flex flex-wrap gap-2 ${clase}`}>
      {id !== null && (
        <Button variante="fantasma" className="!px-2.5 !py-1.5" onClick={() => comparar(id)}>
          Comparar con original
        </Button>
      )}
      {f.acciones.map((a) => (
        <Button key={a.accion} variante={a.peligro ? "peligro" : "secundario"}
          className="!px-2.5 !py-1.5" disabled={ocupado} aria-disabled={ocupado}
          onClick={() => pedir({ accion: a.accion, id })}>
          {a.etiqueta}
        </Button>
      ))}
    </div>
  );
}

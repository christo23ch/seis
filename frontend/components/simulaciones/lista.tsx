"use client";
import { useEffect, useRef, useState } from "react";
import { type UseQueryResult, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { eur, fecha } from "@/lib/format";
import { puedeEscribir } from "@/lib/permisos";
import type { ComparacionSimulacion, Detalle, EstadoSimulacion, Semaforo, SimulacionResumen } from "@/lib/types";
import { SemaforoBadge } from "@/components/resultado";
import { Button, Card, CardContent, CardHeader, CardTitle, ErrorBox, Spinner } from "@/components/ui";
import { idCorto, invalidarConfiguracion } from "./aviso-configuracion";

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
  const ocupado = accion.isPending;

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
      <CardHeader className="flex flex-wrap items-baseline justify-between gap-2">
        <CardTitle>Configuraciones del análisis</CardTitle>
        <span className="text-[12px] text-slate-500">
          {lista.data.length} {lista.data.length === 1 ? "simulación" : "simulaciones"}
          {!escribe && " · solo lectura"}
        </span>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <ErrorBox mensaje={error} />}
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
                    <Acciones f={f} ocupado={ocupado} pedir={pedir} clase="justify-end" />
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
              <Acciones f={f} ocupado={ocupado} pedir={pedir} clase="mt-2.5" />
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

function Acciones({ f, ocupado, pedir, clase = "" }: {
  f: Fila; ocupado: boolean; pedir: (p: Peticion) => void; clase?: string;
}) {
  if (f.acciones.length === 0) return null;
  const id = f.clave === "original" ? null : f.clave;
  return (
    <div className={`flex flex-wrap gap-2 ${clase}`}>
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

/** Diálogo de confirmación mínimo sobre `<dialog>` nativo: `showModal()` ya da
 * foco dentro, cierre con Escape y fondo inerte, sin librerías. */
function Confirmacion({ abierta, titulo, texto, boton, peligro, onConfirmar, onCancelar }: {
  abierta: boolean; titulo: string; texto: string; boton: string; peligro?: boolean;
  onConfirmar: () => void; onCancelar: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (abierta && !d.open) d.showModal();
    if (!abierta && d.open) d.close();
  }, [abierta]);
  return (
    <dialog ref={ref} onCancel={(e) => { e.preventDefault(); onCancelar(); }}
      aria-labelledby="confirmacion-titulo"
      className="w-[min(420px,calc(100vw-32px))] rounded-lg border border-borde-linea p-0 shadow-carta backdrop:bg-tinta/40">
      <div className="px-5 py-4">
        <h2 id="confirmacion-titulo" className="text-base font-semibold text-tinta">{titulo}</h2>
        <p className="mt-2 text-sm text-slate-600">{texto}</p>
      </div>
      <div className="flex justify-end gap-2 border-t border-borde-linea px-5 py-3">
        <Button variante="fantasma" onClick={onCancelar}>Cancelar</Button>
        <Button variante={peligro ? "peligro" : "primario"} onClick={onConfirmar}>{boton}</Button>
      </div>
    </dialog>
  );
}

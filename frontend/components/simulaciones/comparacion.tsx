"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { eur, fecha, num, pct, puntos } from "@/lib/format";
import type { ComparacionSimulacion, FilaComparacion, ResumenResultadoComparado, ValorJson } from "@/lib/types";
import { SemaforoBadge } from "@/components/resultado";
import { Button, Check, ErrorBox, Spinner } from "@/components/ui";
import { idCorto } from "./aviso-configuracion";

/** Original frente a una simulación.
 *
 * Toda la comparación la hace el backend (`GET /simulaciones/{sid}/comparacion`,
 * Fase 5F.7.3): qué parámetros cambian, por qué y los resultados de cada lado.
 * Aquí no se compara, no se calculan diferencias ni deltas y no se decide qué ha
 * cambiado: se pinta lo recibido. Sin flechas ni colores de «mejor/peor». */
export function PanelComparacion({ analisisId, simulacionId, onCerrar, onNoExiste }: {
  analisisId: string;
  simulacionId: string;
  onCerrar: () => void;
  onNoExiste: () => void;                  // 404: la lista cierra el panel y se refresca
}) {
  const [todos, setTodos] = useState(false);
  const ref = useRef<HTMLElement>(null);
  // Misma clave que usa la fila «Original» de la lista: `invalidarConfiguracion`
  // la refresca tras validar o seleccionar, y «En uso» se actualiza aquí solo.
  const cmp = useQuery({
    queryKey: ["comparacion", analisisId, simulacionId],
    queryFn: () => api.compararSimulacion(analisisId, simulacionId),
  });

  useEffect(() => { ref.current?.scrollIntoView({ block: "start", behavior: "smooth" }); }, [simulacionId]);
  useEffect(() => {
    if (cmp.error instanceof ApiError && cmp.error.status === 404) onNoExiste();
  }, [cmp.error, onNoExiste]);

  return (
    <section ref={ref} aria-label="Comparación con el original"
      className="scroll-mt-16 rounded-md border border-primario/30 md:scroll-mt-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-borde-linea px-4 py-2.5">
        <h3 className="text-sm font-semibold text-tinta">
          Comparación con el original · simulación <span className="cifra">{idCorto(simulacionId)}</span>
        </h3>
        <Button variante="fantasma" className="!px-2 !py-1 text-[12px]" onClick={onCerrar}>Cerrar</Button>
      </div>
      <div className="space-y-4 px-4 py-3">
        {cmp.isPending && <Spinner />}
        {cmp.isError && !(cmp.error instanceof ApiError && cmp.error.status === 404) && (
          <ErrorBox mensaje={`No se pudo cargar la comparación: ${cmp.error.message}`} />
        )}
        {cmp.data && <Contenido data={cmp.data} todos={todos} setTodos={setTodos} />}
      </div>
    </section>
  );
}

function Contenido({ data, todos, setTodos }: {
  data: ComparacionSimulacion; todos: boolean; setTodos: (v: boolean) => void;
}) {
  const s = data.simulacion, o = data.original;
  const modificadas = data.parametros.filter((f) => f.modificado);
  const filas = todos ? data.parametros : modificadas;
  const hayDeriva = data.parametros.some((f) => f.causa === "conocimiento_vigente");

  return (
    <>
      {/* 1. Cabecera: los dos lados, con sus versiones tal como llegan. */}
      <div className="grid gap-2 text-[13px] sm:grid-cols-2">
        <div className="rounded-md border border-borde-linea px-3 py-2">
          <p className="font-semibold text-tinta">Original</p>
          <p className="text-slate-600">Creado {fecha(o.creado_en)}</p>
          <p className="text-slate-500">
            Parámetros <span className="cifra">v{o.version_parametros}</span> · reglas <span className="cifra">v{o.version_reglas}</span>
          </p>
        </div>
        <div className="rounded-md border border-borde-linea px-3 py-2">
          <p className="flex flex-wrap items-center gap-1.5 font-semibold text-tinta">
            Simulación <span className="cifra">{idCorto(s.id)}</span>
            <span className="rounded-full border border-borde-control px-2 py-0.5 text-[11px] font-semibold">{s.estado}</span>
            {s.es_configuracion_actual && (
              <span className="rounded-full bg-primario px-2 py-0.5 text-[11px] font-semibold text-white">En uso</span>
            )}
          </p>
          <p className="text-slate-600">Creada {fecha(s.creado_en)}</p>
          <p className="text-slate-500">
            Parámetros <span className="cifra">{s.version_parametros_base ? `v${s.version_parametros_base}` : "—"}</span>
            {" · "}reglas <span className="cifra">{s.version_reglas ? `v${s.version_reglas}` : "—"}</span>
          </p>
        </div>
      </div>

      {/* 2. Carencia declarada. */}
      {!o.parametros_disponibles && (
        <p role="note" className="rounded-md border border-borde-linea bg-papel-carta px-3 py-2 text-[13px] text-tinta">
          Este análisis es anterior al registro de parámetros: no hay valores originales con los que comparar;
          solo se muestran los cambios pedidos en la simulación.
        </p>
      )}

      {/* 3. Resultado lado a lado: los dos valores, sin deltas. */}
      <Resultado original={data.resultado.original} simulacion={data.resultado.simulacion} />

      {/* 4. Parámetros. */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[13px] text-slate-600" aria-live="polite">
            <span className="cifra font-semibold">{modificadas.length}</span>{" "}
            {modificadas.length === 1 ? "parámetro modificado" : "parámetros modificados"} de{" "}
            <span className="cifra">{data.parametros.length}</span>
          </p>
          <Check label="Mostrar todos" checked={todos} onChange={(e) => setTodos(e.target.checked)} />
        </div>
        {hayDeriva && (
          <p role="note" className="text-[12px] text-slate-600">
            Las simulaciones parten del conocimiento vigente, que ha cambiado desde que se creó el análisis.
          </p>
        )}
        {filas.length === 0 ? (
          <p className="text-sm text-slate-500">Esta simulación no cambia ningún parámetro respecto al original.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-[13px]">
              <thead>
                <tr className="border-b border-borde-linea text-left text-[12px] uppercase tracking-wide text-slate-500">
                  <th className="px-3.5 py-1.5 font-semibold">Parámetro</th>
                  <th className="px-3.5 py-1.5 font-semibold">Original</th>
                  <th className="px-3.5 py-1.5 font-semibold">Cambio pedido</th>
                  <th className="px-3.5 py-1.5 font-semibold">Aplicado</th>
                  <th className="px-3.5 py-1.5 font-semibold">Causa</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => <FilaParametro key={f.clave} f={f} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

// ─────────────────────────── resultado ───────────────────────────

type Campo = keyof ResumenResultadoComparado;
const CAMPOS: { campo: Campo; etiqueta: string; formato: (v: number) => string }[] = [
  { campo: "ico", etiqueta: "ICO", formato: (v) => num(v) },
  { campo: "ra", etiqueta: "RA", formato: (v) => num(v) },
  { campo: "ici", etiqueta: "ICI", formato: (v) => num(v) },
  { campo: "icu", etiqueta: "ICU", formato: (v) => num(v) },
  { campo: "p_ideal", etiqueta: "P. ideal", formato: eur },
  { campo: "p_objetivo", etiqueta: "P. objetivo", formato: eur },
  { campo: "p_max", etiqueta: "P. máximo", formato: eur },
  { campo: "p_limite", etiqueta: "P. límite", formato: eur },
  { campo: "p_adj_esperado", etiqueta: "P. adjudicación esperado", formato: eur },
  { campo: "rvc", etiqueta: "RVC", formato: (v) => num(v, 3) },
  { campo: "margen_seguridad_valor", etiqueta: "Margen de seguridad", formato: (v) => pct(v) },
  // Fase 5H.1-A (ADR-0017): informativos; «—» si el resultado no los trae.
  { campo: "van_coste_capital", etiqueta: "VAN al coste de capital", formato: eur },
  { campo: "diferencial_tir_coste_capital", etiqueta: "TIR − coste de capital", formato: (v) => puntos(v) },
];

function Resultado({ original, simulacion }: { original: ResumenResultadoComparado; simulacion: ResumenResultadoComparado }) {
  // Fase 5G.3: con la escalera degenerada (marca de M12) el límite no es una
  // cifra utilizable. Si la marca falta (null, dato antiguo), la cifra como siempre.
  const noUtilizable = (r: ResumenResultadoComparado, c: (typeof CAMPOS)[number]) =>
    c.campo === "p_limite" && r.escalera_degenerada === true;
  // Fase 5G.4-C: «No utilizable» es texto, no una cifra: no lleva la fuente monoespaciada.
  const claseCifra = (r: ResumenResultadoComparado, c: (typeof CAMPOS)[number]) =>
    noUtilizable(r, c) ? "" : "cifra ";
  const celda = (r: ResumenResultadoComparado, c: (typeof CAMPOS)[number]) => {
    if (noUtilizable(r, c)) return "No utilizable";
    const v = r[c.campo];
    return typeof v === "number" ? c.formato(v) : "—";
  };
  return (
    <div>
      <p className="mb-1 text-[12px] font-semibold uppercase tracking-wide text-slate-500">Resultado</p>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-borde-linea text-left text-[12px] text-slate-500">
            <th className="py-1 pr-2 font-semibold"><span className="sr-only">Indicador</span></th>
            <th className="px-2 py-1 text-right font-semibold">Original</th>
            <th className="py-1 pl-2 text-right font-semibold">Simulación</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-borde-linea">
            <th scope="row" className="py-1 pr-2 text-left font-normal text-slate-600">Semáforo</th>
            <td className="px-2 py-1 text-right">{original.semaforo ? <SemaforoBadge s={original.semaforo} /> : "—"}</td>
            <td className="py-1 pl-2 text-right">{simulacion.semaforo ? <SemaforoBadge s={simulacion.semaforo} /> : "—"}</td>
          </tr>
          {CAMPOS.map((c) => (
            <tr key={c.campo} className="border-b border-borde-linea">
              <th scope="row" className="py-1 pr-2 text-left font-normal text-slate-600">{c.etiqueta}</th>
              <td className={`${claseCifra(original, c)}px-2 py-1 text-right`}>{celda(original, c)}</td>
              <td className={`${claseCifra(simulacion, c)}py-1 pl-2 text-right`}>{celda(simulacion, c)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────── parámetros ───────────────────────────

const CAUSA: Record<NonNullable<FilaComparacion["causa"]>, string> = {
  override: "Cambio pedido en esta simulación",
  conocimiento_vigente: "Cambió el conocimiento del sistema",
};

function FilaParametro({ f }: { f: FilaComparacion }) {
  return (
    <tr data-comparacion={f.clave} className="border-b border-borde-linea align-top">
      <td className="px-3.5 py-1.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-medium text-tinta">{f.nombre_legible ?? f.clave}</span>
          {!f.editable && (
            <span className="rounded-full border border-borde-control px-2 py-0.5 text-[11px] font-semibold">no editable</span>
          )}
        </div>
        <div className="cifra break-all text-[11px] text-slate-500">{f.clave}{f.unidad ? ` · ${f.unidad}` : ""}</div>
      </td>
      <td className="px-3.5 py-1.5"><Valor v={f.valor_original} /></td>
      <td className="px-3.5 py-1.5">{f.tiene_override ? <Valor v={f.override} /> : "—"}</td>
      <td className="px-3.5 py-1.5"><Valor v={f.valor_aplicado} /></td>
      <td className="px-3.5 py-1.5 text-slate-700">{f.causa ? CAUSA[f.causa] : "—"}</td>
    </tr>
  );
}

/** Escalares tal cual; estructuras con un resumen corto y el JSON plegado. */
function Valor({ v }: { v: ValorJson | null }) {
  if (v === null) return <span>—</span>;
  if (typeof v !== "object") return <span className="cifra">{String(v)}</span>;
  const resumen = Array.isArray(v) ? `lista de ${v.length}` : `objeto de ${Object.keys(v).length} claves`;
  return (
    <details>
      <summary className="cursor-pointer text-[12px] text-slate-600">{resumen}</summary>
      <pre className="cifra mt-1 max-w-[280px] overflow-auto whitespace-pre-wrap break-all rounded bg-slate-50 p-2 text-[11px]">
        {JSON.stringify(v, null, 2)}
      </pre>
    </details>
  );
}

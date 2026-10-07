"use client";
import { useState } from "react";
import { NO_CONSTA, contarValores, type Nodo } from "@/lib/presentacion-valores";
import { Button, cx } from "./ui";

/** Fase 5K-B — un árbol de valores legible: filas «nombre · valor · unidad», grupos
 * anidados y tablas con desplazamiento propio. Solo pinta lo que dan los nodos. */
export function ArbolValores({ nodos, nivel = 0 }: { nodos: Nodo[]; nivel?: number }) {
  return (
    <dl className={cx("min-w-0 space-y-1", nivel > 0 && "border-l border-borde-linea pl-3")}>
      {nodos.map((n) => <NodoValor key={n.ruta} n={n} nivel={nivel} />)}
    </dl>
  );
}

function NodoValor({ n, nivel }: { n: Nodo; nivel: number }) {
  if (n.tipo === "grupo") {
    return (
      <div data-ruta={n.ruta} className="pt-1.5">
        <dt className="mb-1 text-[12.5px] font-semibold text-tinta">{n.etiqueta}</dt>
        <dd><ArbolValores nodos={n.hijos} nivel={nivel + 1} /></dd>
      </div>
    );
  }
  if (n.tipo === "tabla") {
    return (
      <div data-ruta={n.ruta} className="pt-1.5">
        <dt className="mb-1 text-[12.5px] font-semibold text-tinta">{n.etiqueta}</dt>
        <dd role="region" aria-label={n.etiqueta} tabIndex={0}
          className="max-w-full overflow-x-auto rounded-md border border-borde-linea focus:outline-none focus-visible:ring-2 focus-visible:ring-primario">
          <table className="w-full min-w-max text-[12.5px]">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>{n.columnas.map((c) => <th key={c} scope="col" className="px-2.5 py-1 font-semibold">{c}</th>)}</tr>
            </thead>
            <tbody>
              {n.filas.map((f, i) => (
                <tr key={i} className="border-t border-borde-linea">
                  {f.map((c, j) => <td key={j} className="cifra px-2.5 py-1">{c}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </dd>
      </div>
    );
  }
  return (
    <div data-ruta={n.ruta} className="flex flex-wrap items-baseline justify-between gap-x-3 border-b border-slate-50 py-1">
      <dt className="min-w-0 text-[12.5px] text-slate-600">{n.etiqueta}</dt>
      <dd className="min-w-0 text-right">
        {/* Monoespaciada solo para cifras; «No consta» y los textos, en la letra normal. */}
        <span className={cx("text-[13px]", n.valor === NO_CONSTA ? "text-slate-500"
          : /^[-+]?\d/.test(n.valor) ? "cifra font-semibold text-tinta" : "font-medium text-tinta")}>{n.valor}</span>
        {n.unidad && n.valor !== NO_CONSTA && <span className="text-[12px] text-slate-500">{` ${n.unidad}`}</span>}
        {n.detalle && <span className="block text-[11.5px] text-slate-500">{n.detalle}</span>}
      </dd>
    </div>
  );
}

/** Sección plegable con el recuento de valores en el resumen. */
export function SeccionPlegable({ titulo, nodos, abierta = false }: { titulo: string; nodos: Nodo[]; abierta?: boolean }) {
  const total = contarValores(nodos);
  return (
    <details open={abierta} className="group rounded-md border border-borde-linea">
      <summary className="flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-sm font-medium text-tinta focus:outline-none focus-visible:ring-2 focus-visible:ring-primario group-open:border-b group-open:border-borde-linea">
        <span>{titulo}</span>
        <span className="text-[12px] font-normal text-slate-500">{total} {total === 1 ? "valor" : "valores"}</span>
      </summary>
      <div className="px-3 py-2"><ArbolValores nodos={nodos} /></div>
    </details>
  );
}

/** Modo avanzado: el mismo dato como JSON, para quien lo necesite. */
export function ConVerJson({ json, children }: { json: unknown; children: React.ReactNode }) {
  const [verJson, setVerJson] = useState(false);
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button variante="fantasma" className="!px-2 !py-1 text-[12px]" aria-pressed={verJson}
          onClick={() => setVerJson((v) => !v)}>
          {verJson ? "Ver presentación" : "Ver JSON"}
        </Button>
      </div>
      {verJson ? (
        <pre data-json className="max-h-[70vh] max-w-full overflow-auto whitespace-pre-wrap break-all rounded-md bg-slate-50 p-3 font-cifra text-[12px] text-slate-600">
          {JSON.stringify(json, null, 2)}
        </pre>
      ) : children}
    </div>
  );
}

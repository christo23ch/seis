"use client";
import { Fragment, useMemo } from "react";
import { analizarMarkdown, type Bloque, type Inline } from "@/lib/markdown";
import { cx } from "./ui";

/** Fase 5K-A — pinta el Markdown del informe (M14) con el estilo de la app.
 *
 * Los niveles de título bajan uno (`#` → h2…): la página ya tiene su h1. Las tablas
 * llevan su propio desplazamiento horizontal, enfocable con el teclado, para que en
 * 390 px no desborden la página. `data-markdown` se conserva en el contenedor: las
 * e2e lo esperan y comparan su texto. */
export function Markdown({ texto, className }: { texto: string; className?: string }) {
  const bloques = useMemo(() => analizarMarkdown(texto), [texto]);
  return (
    <div data-markdown className={cx("min-w-0 space-y-3 break-words text-[13.5px] leading-relaxed text-slate-700", className)}>
      {bloques.map((b, i) => <BloqueMd key={i} b={b} />)}
    </div>
  );
}

function BloqueMd({ b }: { b: Bloque }) {
  switch (b.tipo) {
    case "titulo": {
      const contenido = <EnLinea nodos={b.contenido} />;
      if (b.nivel === 1) return <h2 className="h-display pt-1 text-xl font-bold text-tinta">{contenido}</h2>;
      if (b.nivel === 2) return <h3 className="border-b border-borde-linea pb-1 pt-3 text-base font-semibold text-tinta">{contenido}</h3>;
      return <h4 className="pt-2 text-sm font-semibold text-tinta">{contenido}</h4>;
    }
    case "parrafo":
      return (
        <p>
          {b.lineas.map((l, i) => <Fragment key={i}>{i > 0 && <br />}<EnLinea nodos={l} /></Fragment>)}
        </p>
      );
    case "lista":
      return (
        <ul className="space-y-1 pl-1">
          {b.items.map((it, i) => (
            <li key={i} className="flex gap-2">
              {it.casilla === null
                ? <span aria-hidden="true" className="text-primario">▸</span>
                : <span role="img" aria-label={it.casilla ? "Hecho" : "Pendiente"}
                    className={cx("mt-1 inline-block h-3.5 w-3.5 shrink-0 rounded-sm border",
                      it.casilla ? "border-sem-verde bg-sem-verde" : "border-slate-400 bg-white")} />}
              <span className="min-w-0"><EnLinea nodos={it.contenido} /></span>
            </li>
          ))}
        </ul>
      );
    case "tabla":
      return (
        <div role="region" aria-label="Tabla del informe" tabIndex={0}
          className="max-w-full overflow-x-auto rounded-md border border-borde-linea focus:outline-none focus-visible:ring-2 focus-visible:ring-primario">
          <table className="w-full min-w-[30rem] border-collapse text-[13px]">
            {b.cabecera && (
              <thead className="bg-slate-50 text-left text-[12px] uppercase tracking-wide text-slate-500">
                <tr>{b.cabecera.map((c, i) => <th key={i} scope="col" className="px-3 py-1.5 font-semibold"><EnLinea nodos={c} /></th>)}</tr>
              </thead>
            )}
            <tbody>
              {b.filas.map((f, i) => (
                <tr key={i} className="border-t border-borde-linea align-top">
                  {f.map((c, j) => <td key={j} className="px-3 py-1.5"><EnLinea nodos={c} /></td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "separador":
      return <hr className="border-borde-linea" />;
  }
}

export function EnLinea({ nodos }: { nodos: Inline[] }) {
  return (
    <>
      {nodos.map((n, i) => {
        switch (n.tipo) {
          case "texto": return <Fragment key={i}>{n.texto}</Fragment>;
          case "negrita": return <strong key={i} className="font-semibold text-tinta"><EnLinea nodos={n.hijos} /></strong>;
          case "cursiva": return <em key={i}><EnLinea nodos={n.hijos} /></em>;
          case "codigo": return <code key={i} className="rounded bg-slate-100 px-1 py-0.5 font-cifra text-[12px]">{n.texto}</code>;
        }
      })}
    </>
  );
}

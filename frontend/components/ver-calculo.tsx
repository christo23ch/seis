"use client";
import { NO_DISPONIBLE, type Calculo } from "@/lib/calculos";
import { TextoFormulas } from "./texto-formulas";
import { cx } from "./ui";

/** Fase 5K-D — panel plegable «Ver cálculo»: fórmula, valores sustituidos y resultado
 * del motor. Si el resultado no trae el dato, lo dice y nombra lo que falta. */
export function VerCalculo({ calculos, titulo = "Ver cálculo", className }:
  { calculos: Calculo[]; titulo?: string; className?: string }) {
  if (calculos.length === 0) return null;
  return (
    <details data-ver-calculo className={cx("group mt-3 rounded-md border border-borde-linea text-[12.5px]", className)}>
      <summary className="cursor-pointer px-3 py-1.5 font-medium text-primario focus:outline-none focus-visible:ring-2 focus-visible:ring-primario">
        {titulo}
      </summary>
      <div className="space-y-3 border-t border-borde-linea px-3 py-2.5">
        {calculos.map((c) => <UnCalculo key={c.clave} c={c} />)}
      </div>
    </details>
  );
}

function UnCalculo({ c }: { c: Calculo }) {
  return (
    <section data-calculo={c.clave} aria-label={c.titulo} className="min-w-0 space-y-1 text-slate-700">
      <h4 className="font-semibold text-tinta"><TextoFormulas texto={c.titulo} /></h4>
      {!c.disponible ? (
        <p data-no-disponible className="text-slate-500">
          {NO_DISPONIBLE}: falta en el resultado <TextoFormulas texto={c.falta ?? "el dato necesario"} />.
        </p>
      ) : (
        <>
          {c.formula && <p className="break-words font-serif"><TextoFormulas texto={c.formula} /></p>}
          {c.sustitucion && <p className="cifra break-words text-slate-600"><TextoFormulas texto={c.sustitucion} /></p>}
          {c.resultado && <p>Resultado del motor: <b className="cifra text-tinta"><TextoFormulas texto={c.resultado} /></b></p>}
          {c.filas && c.filas.length > 0 && (
            <dl className="mt-1 space-y-0.5 border-l border-borde-linea pl-2.5">
              {c.filas.map((f, i) => (
                <div key={`${f.etiqueta}-${i}`} className="flex flex-wrap justify-between gap-x-3">
                  <dt className="text-slate-500"><TextoFormulas texto={f.etiqueta} /></dt>
                  <dd className="cifra text-right"><TextoFormulas texto={f.valor} /></dd>
                </div>
              ))}
            </dl>
          )}
          {c.nota && <p className="text-[12px] text-slate-500"><TextoFormulas texto={c.nota} /></p>}
        </>
      )}
    </section>
  );
}

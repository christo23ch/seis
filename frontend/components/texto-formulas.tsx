import { Fragment } from "react";
import { segmentarTexto } from "@/lib/formulas";

/** Fase 5K-C — pinta un texto del motor con las fórmulas en subíndice («P<sub>máx</sub>»)
 * y las claves internas con su nombre legible. El texto de origen no cambia: `title`
 * conserva el símbolo tal como lo escribe el motor. */
export function TextoFormulas({ texto }: { texto: string }) {
  return (
    <>
      {segmentarTexto(texto).map((s, i) => {
        if (s.tipo === "texto") return <Fragment key={i}>{s.texto}</Fragment>;
        if (s.tipo === "identificador") return <span key={i} title={s.original}>{s.texto}</span>;
        return (
          <var key={i} title={s.original} className="whitespace-nowrap font-serif not-italic">
            <i>{s.base}</i><sub className="text-[0.75em]">{s.sub}</sub>
          </var>
        );
      })}
    </>
  );
}

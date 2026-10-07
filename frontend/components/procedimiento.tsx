"use client";
import { etiquetaEstado, filasProcedimiento } from "@/lib/procedimiento";
import type { ProcedimientoResultado } from "@/lib/types";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "./ui";

/** Fase 5J-1 (ADR-0022): datos del procedimiento de subasta. Los umbrales son
 * informativos; desde la 5J-2b el depósito, la forma de puja y los meses de
 * inmovilización entran en el cálculo, y el aviso del motor lo dice. Un resultado
 * anterior a la fase no trae el bloque: se explica en vez de inventarlo. */
export function ProcedimientoPanel({ datos }: { datos: ProcedimientoResultado | null | undefined }) {
  return (
    <Card data-procedimiento>
      <CardHeader className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>Procedimiento y umbrales legales</CardTitle>
        <Badge tono="azul">Orientativo</Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        {datos ? <Contenido datos={datos} /> : (
          <p className="text-sm text-slate-500">
            Este análisis es anterior al cálculo de los datos del procedimiento. Vuelva a analizarlo
            para ver el depósito exigido y los umbrales de aprobación.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function Contenido({ datos }: { datos: ProcedimientoResultado }) {
  return (
    <>
      <dl className="grid gap-x-6 gap-y-2.5 sm:grid-cols-2">
        {filasProcedimiento(datos).map((f) => (
          <div key={f.clave} data-fila={f.clave} className="min-w-0 border-b border-slate-50 pb-1.5">
            <dt className="text-[12.5px] text-slate-500">{f.etiqueta}</dt>
            <dd className="text-sm font-semibold text-tinta">
              <span className="cifra">{f.valor}</span>
              {f.detalle && <span className="ml-1.5 text-[12px] font-normal text-slate-500">· {f.detalle}</span>}
            </dd>
          </div>
        ))}
      </dl>

      {datos.avisos.length > 0 && (
        <div role="note" aria-label="Avisos del procedimiento" className="rounded-md bg-sem-amarillobg px-3 py-2.5">
          <p className="mb-1 text-[12px] font-semibold uppercase tracking-wide text-sem-amarillo">Avisos</p>
          <ul className="space-y-1 text-[13px] text-slate-700">
            {datos.avisos.map((a) => <li key={a} className="flex gap-2"><span className="text-sem-amarillo">▸</span><span>{a}</span></li>)}
          </ul>
        </div>
      )}

      {datos.datos_legales.length > 0 && (
        <details className="text-[13px]">
          <summary className="cursor-pointer text-slate-600">Base legal aplicada</summary>
          <ul className="mt-2 space-y-1.5">
            {datos.datos_legales.map((d) => (
              <li key={d.dato} className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-medium text-tinta">{d.dato}{d.texto ? ` (${d.texto})` : ""}:</span>
                <span className="text-slate-600">{d.articulo}</span>
                <Badge tono={d.estado === "confirmado" ? "verde" : "amarillo"}>{etiquetaEstado(d.estado)}</Badge>
                {d.nota && <span className="basis-full text-[12px] text-slate-500">{d.nota}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}

      <p data-aviso-orientativo className="text-[12px] text-slate-500">{datos.aviso_orientativo}</p>
    </>
  );
}

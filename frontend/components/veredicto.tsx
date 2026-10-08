"use client";
import { calculoVeredicto } from "@/lib/calculos";
import { eur } from "@/lib/format";
import type { Resultado, VeredictoPuja } from "@/lib/types";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "./ui";
import { VerCalculo } from "./ver-calculo";

/** Fase 5J-4 (ADR-0028): las tres cifras de la puja y el veredicto. Todos los textos los redacta
 * el motor (los mismos que el informe); aquí solo se presentan. Informativo: no bloquea nada y el
 * usuario puede seguir simulando. Un resultado anterior a la fase no trae veredicto: no se pinta. */
export function VeredictoPanel({ res }: { res: Resultado }) {
  const v = res.decision.veredicto;
  if (!v) return null;
  return (
    <Card data-veredicto={v.estado}>
      <CardHeader className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>Veredicto de la puja</CardTitle>
        <Badge tono={tonoVeredicto(v)}>{v.titulo}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        {v.aprobacion_texto && (
          <p data-aprobacion={v.aprobacion ?? undefined} className="text-sm font-semibold text-tinta">{v.aprobacion_texto}</p>
        )}
        <p className="text-[13px] text-slate-700">{v.texto}</p>
        <dl className="grid gap-3 sm:grid-cols-3">
          <Cifra clave="p_max" etiqueta="Precio máximo económico" valor={v.p_max} />
          <Cifra clave="minima" etiqueta="Puja mínima aprobable" valor={v.puja_minima_efectiva} />
          <Cifra clave="segura" etiqueta="Puja de aprobación segura" valor={v.puja_aprobacion_segura} />
        </dl>
        {v.puja_recomendada != null && (
          <p data-puja-recomendada className="text-sm text-slate-700">
            Puja recomendada: <b className="cifra">{eur(v.puja_recomendada)}</b>
          </p>
        )}
        {v.alternativa_vivienda && <p data-alternativa-vivienda className="text-[13px] text-slate-600">{v.alternativa_vivienda}</p>}
        {v.cambios.length > 0 && (
          <div role="note" aria-label="Qué tendría que cambiar" className="rounded-md bg-sem-amarillobg px-3 py-2.5">
            <p className="mb-1 text-[12px] font-semibold uppercase tracking-wide text-sem-amarillo">Qué tendría que cambiar</p>
            <ul className="space-y-1 text-[13px] text-slate-700">
              {v.cambios.map((c) => <li key={c} className="flex gap-2"><span className="text-sem-amarillo">▸</span><span>{c}</span></li>)}
            </ul>
          </div>
        )}
        {v.aviso_rentabilidad && <p data-aviso-rentabilidad className="text-[12px] italic text-slate-500">{v.aviso_rentabilidad}</p>}
        <VerCalculo calculos={[calculoVeredicto(res)]} />
      </CardContent>
    </Card>
  );
}

function tonoVeredicto(v: VeredictoPuja): "verde" | "naranja" | "rojo" | "neutro" {
  if (v.estado === "viable") return "verde";
  if (v.estado === "inviable") return v.cabe_en_limite ? "naranja" : "rojo";
  return "neutro";
}

function Cifra({ clave, etiqueta, valor }: { clave: string; etiqueta: string; valor: number | null | undefined }) {
  return (
    <div data-cifra={clave} className="min-w-0 border-b border-slate-50 pb-1.5">
      <dt className="text-[12.5px] text-slate-500">{etiqueta}</dt>
      <dd className="cifra text-sm font-semibold text-tinta">{valor != null ? eur(valor) : "No consta"}</dd>
    </div>
  );
}

"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Badge, Campo, Card, CardContent, CardHeader, CardTitle, ErrorBox, Input, Spinner } from "@/components/ui";
import { eur, fecha } from "@/lib/format";
import { Info } from "lucide-react";

// La nota es ORIENTATIVA: la calcula el scoring exprés con los datos brutos de la
// captación (sin cargas, posesión, comparables ni financiación). No sustituye al
// motor M01–M14 ni a los vetos: sirve para priorizar qué analizar en profundidad.
function NotaOrientativa({ score, desglose }: { score?: number | null; desglose?: Record<string, number> | null }) {
  if (score == null) return <Badge tono="neutro">sin puntuar</Badge>;
  const tono = score >= 70 ? "verde" : score >= 45 ? "amarillo" : "rojo";
  const detalle = desglose ? Object.entries(desglose).map(([k, v]) => `${k}: ${v}`).join(" · ") : "";
  return (
    <span className="flex items-center gap-1.5" title={detalle}>
      <Badge tono={tono}>{score}/100</Badge>
      <span className="text-[11px] uppercase tracking-wide text-slate-400">orientativa</span>
    </span>
  );
}

export default function Subastas() {
  const [scoreMin, setScoreMin] = useState("");
  const min = scoreMin === "" ? undefined : Number(scoreMin);
  const { data, isLoading, error } = useQuery({
    queryKey: ["subastas", min],
    queryFn: () => api.subastas(min),
  });

  return (
    <div className="max-w-5xl space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Subastas captadas</h1>
        <p className="text-sm text-slate-500">
          Oportunidades captadas de los portales, con una puntuación exprés para priorizar el análisis completo.
        </p>
      </header>

      <div className="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
        <p>
          La <strong>puntuación es orientativa</strong>: se calcula solo con los datos brutos de la captación
          (descuento aparente, fuente, subastas desiertas, información disponible y plazo hasta el cierre).
          No conoce cargas registrales, situación posesoria, comparables ni financiación, por lo que
          <strong> no sustituye al análisis completo</strong>: una subasta con nota alta puede resultar ROJO tras el motor experto.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle>Filtro</CardTitle></CardHeader>
        <CardContent>
          <div className="max-w-xs">
            <Campo label="Puntuación mínima" ayuda="las subastas sin puntuación quedan fuera del filtro">
              <Input type="number" min={0} max={100} value={scoreMin}
                onChange={(e) => setScoreMin(e.target.value)} placeholder="(sin filtro)" />
            </Campo>
          </div>
        </CardContent>
      </Card>

      {isLoading && <Spinner />}
      {error && <ErrorBox mensaje={(error as ApiError).message} />}

      {data && (
        <Card>
          <CardHeader><CardTitle>Resultados ({data.length})</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {data.length === 0 && (
              <p className="text-sm text-slate-500">No hay subastas captadas que cumplan el filtro.</p>
            )}
            {data.map((s) => (
              <div key={s.id} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2.5">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">
                    {s.identificador_externo ?? s.id.slice(0, 8)} · {s.fuente_codigo}
                  </div>
                  <div className="truncate text-xs text-slate-500">
                    VS {eur(s.valor_subasta)}
                    {s.fecha_cierre && ` · cierra ${fecha(s.fecha_cierre)}`}
                    {s.subastas_desiertas_previas > 0 && ` · ${s.subastas_desiertas_previas} desierta(s)`}
                  </div>
                </div>
                <NotaOrientativa score={s.score} desglose={s.score_desglose} />
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

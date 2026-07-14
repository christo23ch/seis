"use client";
import { useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { eur, num, pct } from "@/lib/format";
import type { Detalle } from "@/lib/types";
import { SemaforoBadge } from "@/components/resultado";
import { Card, CardContent, CardHeader, CardTitle, ErrorBox, Spinner } from "@/components/ui";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const PALETA = ["#2E4B8F", "#B45309", "#0F766E"];

export default function Comparativa() {
  const { data: lista, isLoading, error } = useQuery({ queryKey: ["analisis"], queryFn: api.listar });
  const [sel, setSel] = useState<string[]>([]);

  const detalles = useQueries({
    queries: sel.map((id) => ({ queryKey: ["detalle", id], queryFn: () => api.detalle(id) })),
  });
  const cargados = detalles.filter((d) => d.data).map((d) => d.data as Detalle);

  function alternar(id: string) {
    setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 3 ? s : [...s, id]));
  }

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as Error).message} />;

  const etiqueta = (d: Detalle) => `${d.entrada?.activo?.municipio ?? "activo"} · ${d.id.slice(0, 6)}`;
  const chart = ["Ideal", "Objetivo", "Máximo", "Límite"].map((m, i) => {
    const fila: Record<string, string | number> = { m };
    cargados.forEach((d) => {
      const p = d.resultado.decision.precios;
      fila[etiqueta(d)] = [p.p_ideal, p.p_objetivo, p.p_max, p.p_limite][i];
    });
    return fila;
  });

  const filas: { k: string; f: (d: Detalle) => string }[] = [
    { k: "Semáforo", f: (d) => d.resultado.decision.semaforo.toUpperCase() },
    { k: "ICO", f: (d) => `${d.resultado.decision.ico}` },
    { k: "RA (banda)", f: (d) => `${d.resultado.decision.ra} (${d.resultado.riesgos.banda})` },
    { k: "ICI / ICU", f: (d) => `${d.resultado.decision.ici} / ${d.resultado.decision.icu}` },
    { k: "P. objetivo", f: (d) => eur(d.resultado.decision.precios.p_objetivo) },
    { k: "P. máximo", f: (d) => eur(d.resultado.decision.precios.p_max) },
    { k: "ROI anual (base)", f: (d) => pct(d.resultado.rentabilidad.roi_anualizado) },
    { k: "TIR anual", f: (d) => pct(d.resultado.rentabilidad.tir_anual) },
    { k: "Margen de seguridad", f: (d) => pct(d.resultado.decision.margen_seguridad_valor) },
    { k: "Valor esperado", f: (d) => eur(d.resultado.rentabilidad.valor_esperado) },
    { k: "RVC (banda)", f: (d) => `${d.resultado.decision.rvc.toFixed(2)} (${d.resultado.puja.banda_rvc})` },
    { k: "P. adjudicación esp.", f: (d) => eur(d.resultado.decision.p_adj_esperado) },
  ];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Comparativa</h1>
        <p className="text-sm text-slate-500">Seleccione hasta 3 análisis para compararlos lado a lado.</p>
      </header>

      <Card>
        <CardContent className="flex flex-wrap gap-2">
          {(lista ?? []).map((a) => (
            <button key={a.id} onClick={() => alternar(a.id)}
              className={`rounded-full border px-3 py-1.5 text-[13px] font-medium transition-colors
                ${sel.includes(a.id) ? "border-primario bg-primario-tenue text-primario" : "border-slate-300 text-slate-600 hover:bg-slate-50"}`}>
              {a.tipologia ?? "activo"} · {a.municipio ?? "—"} · ICO {a.ico}
            </button>
          ))}
          {(lista ?? []).length === 0 && <span className="text-sm text-slate-400">No hay análisis guardados todavía.</span>}
        </CardContent>
      </Card>

      {cargados.length > 0 && (
        <>
          <Card>
            <CardContent className="px-0 py-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-[11.5px] uppercase tracking-wide text-slate-400">
                    <th className="px-5 py-2.5">Métrica</th>
                    {cargados.map((d, i) => (
                      <th key={d.id} className="px-3 py-2.5" style={{ color: PALETA[i] }}>{etiqueta(d)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filas.map((f) => (
                    <tr key={f.k} className="border-b border-slate-50">
                      <td className="px-5 py-2 text-slate-500">{f.k}</td>
                      {cargados.map((d) => (
                        <td key={d.id} className="cifra px-3 py-2 font-medium">
                          {f.k === "Semáforo" ? <SemaforoBadge s={d.resultado.decision.semaforo} /> : f.f(d)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Escaleras de precios comparadas</CardTitle></CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart}>
                    <CartesianGrid vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="m" tick={{ fontSize: 12 }} />
                    <YAxis tickFormatter={(v) => num(Number(v) / 1000) + "k"} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: unknown) => eur(Number(v))} />
                    <Legend />
                    {cargados.map((d, i) => (
                      <Bar key={d.id} dataKey={etiqueta(d)} fill={PALETA[i]} radius={[3, 3, 0, 0]} />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

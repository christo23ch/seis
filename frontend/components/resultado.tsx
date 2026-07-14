"use client";
import { eur, num, pct } from "@/lib/format";
import type { Decision, Resultado, RiesgoDim, Semaforo } from "@/lib/types";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "./ui";

export const SEM_COLOR: Record<Semaforo, string> = { verde: "#15803D", amarillo: "#B45309", naranja: "#C2410C", rojo: "#B91C1C" };
const SEM_BG: Record<Semaforo, string> = { verde: "bg-sem-verdebg", amarillo: "bg-sem-amarillobg", naranja: "bg-sem-naranjabg", rojo: "bg-sem-rojobg" };
const SEM_TXT: Record<Semaforo, string> = { verde: "text-sem-verde", amarillo: "text-sem-amarillo", naranja: "text-sem-naranja", rojo: "text-sem-rojo" };

export function SemaforoBadge({ s }: { s: Semaforo }) {
  return <Badge tono={s}>{s.toUpperCase()}</Badge>;
}

export function SemaforoHero({ d }: { d: Decision }) {
  return (
    <div className={`rounded-lg border px-6 py-5 ${SEM_BG[d.semaforo]} border-current/10`}>
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
        <div className="flex items-center gap-3">
          <span className={`h-4 w-4 rounded-full`} style={{ background: SEM_COLOR[d.semaforo] }} />
          <span className={`h-display text-3xl font-bold ${SEM_TXT[d.semaforo]}`}>{d.semaforo.toUpperCase()}</span>
        </div>
        <MetricaMini etiqueta="ICO" valor={`${d.ico} / 100`} />
        <MetricaMini etiqueta="RA" valor={`${d.ra} / 100`} />
        <MetricaMini etiqueta="ICI" valor={`${d.ici}`} />
        <MetricaMini etiqueta="ICU" valor={`${d.icu}`} />
        <MetricaMini etiqueta="RVC" valor={d.rvc.toFixed(2)} />
      </div>
      {d.razones.length > 0 && <p className="mt-3 text-sm text-slate-700">{d.razones[0]}</p>}
    </div>
  );
}
const MetricaMini = ({ etiqueta, valor }: { etiqueta: string; valor: string }) => (
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{etiqueta}</div>
    <div className="cifra text-lg font-semibold">{valor}</div>
  </div>
);

/** Elemento firma: la escalera de precios como escalera real, con P_adj cruzándola. */
export function EscaleraPrecios({ d }: { d: Decision }) {
  const p = d.precios;
  const escalones = [
    { n: "Ideal", v: p.p_ideal, alto: 34 },
    { n: "Objetivo", v: p.p_objetivo, alto: 56 },
    { n: "Máximo", v: p.p_max, alto: 78 },
    { n: "Límite", v: p.p_limite, alto: 100 },
  ];
  const max = p.p_limite;
  const adjPct = Math.min(100, Math.max(2, (d.p_adj_esperado / max) * 100));
  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Escalera de precios</CardTitle>
        <span className="text-[12px] text-slate-400">P. adjudicación esperado: <b className="cifra text-slate-600">{eur(d.p_adj_esperado)}</b></span>
      </CardHeader>
      <CardContent>
        <div className="relative mt-6 flex h-44 items-end gap-3 pb-1">
          <div className="absolute inset-x-0 border-t-2 border-dashed border-slate-400" style={{ bottom: `${adjPct * 0.88}%` }}>
            <span className="absolute -top-5 right-0 rounded bg-tinta px-1.5 py-0.5 text-[10px] font-semibold text-white">P adj. {eur(d.p_adj_esperado)}</span>
          </div>
          {escalones.map((e, i) => (
            <div key={e.n} className="escalon flex-1" style={{ height: `${e.alto}%`, background: i === 3 ? "#FBEAEA" : i === 2 ? "#E8EDF7" : "white" }}>
              <span className="escalon-etiqueta">{e.n}</span>
              <div className="px-2 pb-2 text-center">
                <div className="cifra text-sm font-bold">{eur(e.v)}</div>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[12px] text-slate-500">
          El <b>límite absoluto</b> es infranqueable por software; superar el <b>máximo</b> exige doble firma del comité.
          {p.degenerada && <span className="ml-1 font-semibold text-sem-rojo">Escalera degenerada: la estructura de costes consume el valor.</span>}
        </p>
      </CardContent>
    </Card>
  );
}

const NIVEL_COLOR: Record<string, string> = { bajo: "#94A3B8", medio: "#B45309", alto: "#C2410C", critico: "#B91C1C" };
export function RiesgosPanel({ riesgos }: { riesgos: { ra: number; banda: string; dominancia_aplicada: string | null; dimensiones: RiesgoDim[] } }) {
  const data = riesgos.dimensiones.map((r) => ({ dim: r.dimension, score: r.score, nivel: r.nivel }));
  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Riesgos (matriz P×I)</CardTitle>
        <span className="text-[12px] text-slate-500">
          RA <b className="cifra">{riesgos.ra}</b> · banda <b>{riesgos.banda}</b>
          {riesgos.dominancia_aplicada && <> · dominancia <b>{riesgos.dominancia_aplicada}</b></>}
        </span>
      </CardHeader>
      <CardContent>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
              <CartesianGrid horizontal={false} stroke="#E2E8F0" />
              <XAxis type="number" domain={[0, 25]} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="dim" width={86} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: any, _n, it: any) => [`${v} (${it.payload.nivel})`, "score"]} />
              <Bar dataKey="score" radius={[0, 3, 3, 0]}>
                {data.map((d, i) => <Cell key={i} fill={NIVEL_COLOR[d.nivel]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-3 space-y-1.5">
          {riesgos.dimensiones.filter((r) => r.condiciones.length).map((r) => (
            <div key={r.dimension} className="text-[12.5px] text-slate-600">
              <b className="text-slate-700">{r.dimension}</b>: {r.condiciones.join("; ")}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function EscenariosPanel({ r }: { r: Resultado["rentabilidad"] }) {
  const data = r.escenarios.map((e) => ({ n: e.nombre, beneficio: e.beneficio, prob: e.probabilidad, roi: e.roi_anualizado }));
  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Escenarios (a precio objetivo)</CardTitle>
        <span className="text-[12px] text-slate-500">Valor esperado <b className="cifra text-slate-700">{eur(r.valor_esperado)}</b></span>
      </CardHeader>
      <CardContent>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ left: 8, right: 8 }}>
              <CartesianGrid vertical={false} stroke="#E2E8F0" />
              <XAxis dataKey="n" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v) => num(v / 1000) + "k"} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: any) => eur(Number(v))} />
              <Bar dataKey="beneficio" radius={[4, 4, 0, 0]}>
                {data.map((d, i) => <Cell key={i} fill={d.beneficio >= 0 ? "#2E4B8F" : "#B91C1C"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 text-center text-[12px] text-slate-500">
          {data.map((d) => <div key={d.n}>p={Math.round(d.prob * 100)}% · ROI a. {pct(d.roi)}</div>)}
        </div>
      </CardContent>
    </Card>
  );
}

export function IcoDesglose({ d }: { d: Decision }) {
  const entradas = Object.entries(d.ico_desglose);
  const pesos: Record<string, number> = { rentabilidad: 25, juridico: 15, ubicacion: 15, liquidez: 12, revalorizacion: 10, financiero: 8, informacion: 8, urbanistico: 7 };
  return (
    <Card>
      <CardHeader><CardTitle>ICO {d.ico} / 100 — desglose</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {entradas.map(([k, v]) => {
          const max = pesos[k] ?? 15;
          return (
            <div key={k} className="flex items-center gap-3 text-[12.5px]">
              <span className="w-28 shrink-0 capitalize text-slate-600">{k}</span>
              <div className="h-2 flex-1 rounded bg-slate-100">
                <div className="h-2 rounded bg-primario" style={{ width: `${Math.min(100, (v / max) * 100)}%` }} />
              </div>
              <span className="cifra w-16 text-right text-slate-500">{v.toFixed(1)} / {max}</span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export function CondicionesVetos({ d }: { d: Decision }) {
  if (!d.vetos.length && !d.condiciones.length) return null;
  return (
    <Card>
      <CardHeader><CardTitle>{d.vetos.length ? "Vetos" : "Condiciones para proceder"}</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm">
        {d.vetos.map((v) => (
          <div key={v.codigo} className="rounded-md bg-sem-rojobg px-3 py-2 text-sem-rojo">
            <b>{v.codigo}</b> — {v.motivo}
            {v.subsanable_con && <div className="mt-0.5 text-[12.5px]">Subsanable con: {v.subsanable_con}</div>}
          </div>
        ))}
        {d.condiciones.map((c, i) => (
          <div key={i} className="flex gap-2 text-slate-700"><span className="text-sem-amarillo">▸</span>{c}</div>
        ))}
      </CardContent>
    </Card>
  );
}

export function MetricasClave({ res }: { res: Resultado }) {
  const d = res.decision, r = res.rentabilidad;
  const filas: [string, string][] = [
    ["Precio ideal", eur(d.precios.p_ideal)], ["Precio objetivo", eur(d.precios.p_objetivo)],
    ["Precio máximo", eur(d.precios.p_max)], ["Precio límite", eur(d.precios.p_limite)],
    ["ROI (base)", `${pct(r.roi)} · ${pct(r.roi_anualizado)} anual`], ["TIR anual", pct(r.tir_anual)],
    ["Margen de seguridad", pct(d.margen_seguridad_valor)], ["Inversión total a P obj.", eur(r.inversion_total)],
    ["VS prudente", eur(res.vs_prudente)], ["δ_v aplicado", pct(res.delta_v)],
  ];
  return (
    <Card>
      <CardHeader><CardTitle>Métricas de decisión</CardTitle></CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2.5">
          {filas.map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between gap-3 border-b border-slate-50 pb-1.5">
              <dt className="text-[12.5px] text-slate-500">{k}</dt>
              <dd className="cifra text-sm font-semibold">{v}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

export function ChecklistLista({ items }: { items: Resultado["checklist"] }) {
  const grupos = [...new Set(items.map((i) => i.grupo))];
  const icono = { ok: "✓", pendiente: "○", no_aplica: "–" } as const;
  const color = { ok: "text-sem-verde", pendiente: "text-sem-amarillo", no_aplica: "text-slate-300" } as const;
  return (
    <div className="space-y-4">
      {grupos.map((g) => (
        <div key={g}>
          <h4 className="mb-1.5 text-[12px] font-semibold uppercase tracking-wide text-slate-500">{g}</h4>
          <div className="space-y-1">
            {items.filter((i) => i.grupo === g).map((i) => (
              <div key={i.orden} className="flex gap-2.5 text-[13px]">
                <span className={`w-4 font-bold ${color[i.estado]}`}>{icono[i.estado]}</span>
                <div className="flex-1">
                  <span className={i.estado === "no_aplica" ? "text-slate-400" : "text-slate-700"}>
                    {i.bloqueante && <b className="mr-1 text-sem-rojo">[B]</b>}{i.texto}
                  </span>
                  {i.detalle && <span className="ml-1 text-slate-400">— {i.detalle}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

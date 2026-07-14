"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { eur, fecha, num } from "@/lib/format";
import type { Semaforo } from "@/lib/types";
import { SEM_COLOR, SemaforoBadge } from "@/components/resultado";
import { Button, Card, CardContent, CardHeader, CardTitle, ErrorBox, Spinner, Stat } from "@/components/ui";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Bar, BarChart, XAxis, YAxis } from "recharts";
import { FilePlus2 } from "lucide-react";

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ["analisis"], queryFn: api.listar });
  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as Error).message} />;
  const lista = data ?? [];

  const porSem = (["verde", "amarillo", "naranja", "rojo"] as Semaforo[]).map((s) => ({
    name: s, value: lista.filter((a) => a.semaforo === s).length,
  }));
  const icoMedio = lista.length ? Math.round(lista.reduce((acc, a) => acc + a.ico, 0) / lista.length) : 0;
  const capitalObjetivo = lista.filter((a) => a.semaforo === "verde" || a.semaforo === "amarillo")
    .reduce((acc, a) => acc + a.p_objetivo, 0);
  const recientes = lista.slice(0, 7);
  const barras = [...lista].slice(0, 10).reverse().map((a, i) => ({ n: `#${i + 1}`, ico: a.ico, sem: a.semaforo }));

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="h-display text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-slate-500">Cartera de análisis y estado del embudo de decisión.</p>
        </div>
        <Link href="/nueva"><Button><FilePlus2 className="h-4 w-4" /> Nueva inversión</Button></Link>
      </header>

      {lista.length === 0 ? (
        <Card><CardContent className="py-14 text-center">
          <p className="text-slate-500">Aún no hay análisis. Cree el primero con el asistente de 11 pasos.</p>
          <Link href="/nueva" className="mt-4 inline-block"><Button>Empezar ahora</Button></Link>
        </CardContent></Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat etiqueta="Análisis totales" valor={num(lista.length)} />
            <Stat etiqueta="ICO medio" valor={`${icoMedio} / 100`} />
            <Stat etiqueta="Operaciones accionables" valor={num(porSem[0].value + porSem[1].value)} sub="verde + amarillo" />
            <Stat etiqueta="Capital a precio objetivo" valor={eur(capitalObjetivo)} sub="suma de accionables" />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader><CardTitle>Distribución de semáforo</CardTitle></CardHeader>
              <CardContent>
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={porSem} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                        {porSem.map((p) => <Cell key={p.name} fill={SEM_COLOR[p.name as Semaforo]} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-1 flex justify-center gap-4 text-[12px]">
                  {porSem.map((p) => (
                    <span key={p.name} className="flex items-center gap-1.5 capitalize text-slate-600">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: SEM_COLOR[p.name as Semaforo] }} />
                      {p.name} <b className="cifra">{p.value}</b>
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>ICO de los últimos análisis</CardTitle></CardHeader>
              <CardContent>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barras}>
                      <XAxis dataKey="n" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="ico" radius={[3, 3, 0, 0]}>
                        {barras.map((b, i) => <Cell key={i} fill={SEM_COLOR[b.sem as Semaforo]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Recientes</CardTitle></CardHeader>
            <CardContent className="px-0 pb-0">
              <table className="w-full text-sm">
                <thead className="text-left text-[11.5px] uppercase tracking-wide text-slate-400">
                  <tr className="border-b border-slate-100">
                    <th className="px-5 py-2">Activo</th><th className="px-3 py-2">Semáforo</th>
                    <th className="px-3 py-2">ICO</th><th className="px-3 py-2">P. objetivo</th>
                    <th className="px-3 py-2">RVC</th><th className="px-3 py-2">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {recientes.map((a) => (
                    <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50/60">
                      <td className="px-5 py-2.5">
                        <Link href={`/inversiones/${a.id}`} className="font-medium text-primario hover:underline">
                          {a.tipologia ?? "activo"} · {a.municipio ?? "—"}
                        </Link>
                        <div className="text-[12px] text-slate-400">{a.perfil} · {num(a.superficie_m2 ?? 0)} m²</div>
                      </td>
                      <td className="px-3 py-2.5"><SemaforoBadge s={a.semaforo} /></td>
                      <td className="cifra px-3 py-2.5">{a.ico}</td>
                      <td className="cifra px-3 py-2.5">{eur(a.p_objetivo)}</td>
                      <td className="cifra px-3 py-2.5">{a.rvc.toFixed(2)}</td>
                      <td className="px-3 py-2.5 text-slate-500">{fecha(a.creado_en)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { eur, fecha, num } from "@/lib/format";
import type { Semaforo } from "@/lib/types";
import { SemaforoBadge } from "@/components/resultado";
import { Button, Card, CardContent, ErrorBox, Input, Select, Spinner } from "@/components/ui";
import { FilePlus2 } from "lucide-react";

export default function Inversiones() {
  const { data, isLoading, error } = useQuery({ queryKey: ["analisis"], queryFn: api.listar });
  const [sem, setSem] = useState<string>("todos");
  const [q, setQ] = useState("");

  const lista = useMemo(() => {
    let l = data ?? [];
    if (sem !== "todos") l = l.filter((a) => a.semaforo === sem);
    if (q.trim()) {
      const t = q.toLowerCase();
      l = l.filter((a) => `${a.municipio ?? ""} ${a.tipologia ?? ""} ${a.perfil}`.toLowerCase().includes(t));
    }
    return l;
  }, [data, sem, q]);

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as Error).message} />;

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="h-display text-2xl font-bold">Inversiones</h1>
          <p className="text-sm text-slate-500">{num(lista.length)} análisis en cartera.</p>
        </div>
        <Link href="/nueva"><Button><FilePlus2 className="h-4 w-4" /> Nueva inversión</Button></Link>
      </header>

      <div className="flex flex-wrap gap-3">
        <div className="w-48">
          <Select value={sem} onChange={(e) => setSem(e.target.value)}>
            <option value="todos">Todos los semáforos</option>
            {(["verde", "amarillo", "naranja", "rojo"] as Semaforo[]).map((s) => (
              <option key={s} value={s}>{s.toUpperCase()}</option>
            ))}
          </Select>
        </div>
        <div className="w-72">
          <Input placeholder="Buscar por municipio, tipología o perfil…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>

      <Card>
        <CardContent className="px-0 py-0">
          <table className="w-full text-sm">
            <thead className="text-left text-[11.5px] uppercase tracking-wide text-slate-400">
              <tr className="border-b border-slate-100">
                <th className="px-5 py-2.5">Activo</th><th className="px-3 py-2.5">Semáforo</th>
                <th className="px-3 py-2.5">ICO</th><th className="px-3 py-2.5">RA</th><th className="px-3 py-2.5">ICI</th>
                <th className="px-3 py-2.5">P. objetivo</th><th className="px-3 py-2.5">P. máximo</th>
                <th className="px-3 py-2.5">RVC</th><th className="px-3 py-2.5">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {lista.map((a) => (
                <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50/60">
                  <td className="px-5 py-2.5">
                    <Link href={`/inversiones/${a.id}`} className="font-medium text-primario hover:underline">
                      {a.tipologia ?? "activo"} · {a.municipio ?? "—"}
                    </Link>
                    <div className="text-[12px] text-slate-400">{a.perfil} · {num(a.superficie_m2 ?? 0)} m²</div>
                  </td>
                  <td className="px-3 py-2.5"><SemaforoBadge s={a.semaforo} /></td>
                  <td className="cifra px-3 py-2.5">{a.ico}</td>
                  <td className="cifra px-3 py-2.5">{a.ra}</td>
                  <td className="cifra px-3 py-2.5">{a.ici}</td>
                  <td className="cifra px-3 py-2.5">{eur(a.p_objetivo)}</td>
                  <td className="cifra px-3 py-2.5">{eur(a.p_max)}</td>
                  <td className="cifra px-3 py-2.5">{a.rvc.toFixed(2)}</td>
                  <td className="px-3 py-2.5 text-slate-500">{fecha(a.creado_en)}</td>
                </tr>
              ))}
              {lista.length === 0 && (
                <tr><td colSpan={9} className="px-5 py-10 text-center text-slate-400">Sin resultados con los filtros actuales.</td></tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

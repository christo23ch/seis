"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Campo, Card, CardContent, CardHeader, CardTitle, ErrorBox, Input, Spinner, Textarea } from "@/components/ui";
import { Save } from "lucide-react";

export default function Parametros() {
  const qc = useQueryClient();
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";
  const { data, isLoading, error } = useQuery({ queryKey: ["parametros"], queryFn: api.parametros });

  const [itpLocal, setItpLocal] = useState<Record<string, string>>({});
  const [clave, setClave] = useState("");
  const [valor, setValor] = useState("");
  const [fuente, setFuente] = useState("");
  const [mensaje, setMensaje] = useState("");

  const guardar = useMutation({
    mutationFn: (b: { clave: string; valor: unknown; fuente_legal?: string }) => api.putParametro(b as any),
    onSuccess: (_r, b) => {
      setMensaje(`Parámetro «${b.clave}» actualizado con vigencia desde hoy.`);
      qc.invalidateQueries({ queryKey: ["parametros"] });
    },
    onError: (e: Error) => setMensaje(e.message),
  });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as Error).message} />;

  const itp: Record<string, number> = data?.fiscal?.itp_por_ccaa ?? {};
  const secciones = Object.keys(data ?? {}).filter((k) => k !== "version");

  function publicarLibre() {
    let v: unknown = valor.trim();
    try { v = JSON.parse(valor); } catch { if (!Number.isNaN(Number(valor)) && valor.trim() !== "") v = Number(valor); }
    guardar.mutate({ clave, valor: v, fuente_legal: fuente || undefined });
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Parámetros (T3)</h1>
        <p className="text-sm text-slate-500">
          Versión vigente <b className="cifra">{data?.version}</b>. Cada cambio crea una fila con vigencia y auditoría; el motor lo usa de inmediato.
        </p>
      </header>
      {mensaje && <p className={`text-sm ${guardar.isError ? "text-sem-rojo" : "text-sem-verde"}`}>{mensaje}</p>}

      <Card>
        <CardHeader><CardTitle>ITP por comunidad autónoma (tipo general, %)</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-x-6 gap-y-2.5 sm:grid-cols-3 lg:grid-cols-4">
            {Object.entries(itp).map(([ccaa, tipo]) => {
              const mostrado = itpLocal[ccaa] ?? String((tipo * 100).toFixed(2).replace(/\.?0+$/, ""));
              return (
                <div key={ccaa} className="flex items-center gap-2">
                  <span className="w-36 truncate text-[13px] capitalize text-slate-600">{ccaa.replace(/_/g, " ")}</span>
                  <Input className="w-20 !py-1 text-right" value={mostrado} disabled={!esAdmin}
                    onChange={(e) => setItpLocal((s) => ({ ...s, [ccaa]: e.target.value }))} />
                  {esAdmin && itpLocal[ccaa] !== undefined && (
                    <Button variante="fantasma" className="!px-1.5 !py-1"
                      onClick={() => guardar.mutate({
                        clave: `fiscal.itp_por_ccaa.${ccaa}`,
                        valor: Number(itpLocal[ccaa].replace(",", ".")) / 100,
                        fuente_legal: "Actualización manual desde la UI",
                      })}>
                      <Save className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-[12px] text-slate-400">Los tipos fiscales deben validarse con asesoría profesional ante cada cambio normativo (§20).</p>
        </CardContent>
      </Card>

      {esAdmin && (
        <Card>
          <CardHeader><CardTitle>Editor libre de parámetro</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <Campo label="Clave (ruta con puntos)" ayuda="Debe existir en el árbol T3; p. ej. tenencia.mensual_defecto">
              <Input value={clave} onChange={(e) => setClave(e.target.value)} placeholder="reforma.baremos_m2.media" />
            </Campo>
            <Campo label="Valor (JSON, número o texto)">
              <Input value={valor} onChange={(e) => setValor(e.target.value)} placeholder="560" />
            </Campo>
            <Campo label="Fuente legal / justificación">
              <Input value={fuente} onChange={(e) => setFuente(e.target.value)} placeholder="BOE / criterio del comité" />
            </Campo>
            <div className="sm:col-span-3">
              <Button onClick={publicarLibre} cargando={guardar.isPending} disabled={!clave.trim()}>
                <Save className="h-4 w-4" /> Publicar con vigencia desde hoy
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Árbol completo vigente</CardTitle></CardHeader>
        <CardContent className="space-y-1.5">
          {secciones.map((k) => (
            <details key={k} className="group rounded-md border border-slate-100">
              <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-700 group-open:border-b group-open:border-slate-100">
                {k}
              </summary>
              <Textarea readOnly rows={Math.min(16, JSON.stringify(data[k], null, 2).split("\n").length)}
                className="!border-0" value={JSON.stringify(data[k], null, 2)} />
            </details>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { fecha } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import { Badge, Button, Campo, Card, CardContent, CardHeader, CardTitle, ErrorBox, Input, Select, Spinner, Textarea } from "@/components/ui";
import { History, Save } from "lucide-react";

const TONO: Record<string, "rojo" | "amarillo" | "azul" | "neutro"> = { veto: "rojo", semaforo: "amarillo", puja: "azul" };

function Condicion({ c }: { c: any }) {
  const objetivo = "expr" in c ? c.expr : Array.isArray(c.valor) ? `[${c.valor.join(", ")}]` : String(c.valor ?? "");
  return (
    <code className="rounded bg-slate-100 px-1.5 py-0.5 font-cifra text-[12px] text-slate-700">
      {c.hecho} <b className="text-primario">{c.op ?? "=="}</b> {objetivo}
    </code>
  );
}

export default function Reglas() {
  const qc = useQueryClient();
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";
  const { data, isLoading, error } = useQuery({ queryKey: ["reglas"], queryFn: api.reglas });
  const [histCodigo, setHistCodigo] = useState<string | null>(null);
  const historial = useQuery({
    queryKey: ["historial", histCodigo], queryFn: () => api.historialRegla(histCodigo!), enabled: !!histCodigo,
  });

  const [editando, setEditando] = useState<string>("");
  const [json, setJson] = useState("");
  const [justificacion, setJustificacion] = useState("");
  const [mensaje, setMensaje] = useState("");

  const publicar = useMutation({
    mutationFn: () => api.nuevaRegla(JSON.parse(json), justificacion),
    onSuccess: (r) => {
      setMensaje(`Publicada ${r.codigo} v${r.version}. La versión anterior queda cerrada con vigencia.`);
      setEditando(""); setJustificacion("");
      qc.invalidateQueries({ queryKey: ["reglas"] });
    },
    onError: (e: Error) => setMensaje(e.message),
  });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as Error).message} />;

  const reglas = data?.reglas ?? [];
  const categorias = ["veto", "semaforo", "puja"].filter((c) => reglas.some((r: any) => r.categoria === c));

  function abrirEditor(r: any) {
    setEditando(r.codigo);
    setJson(JSON.stringify(r, null, 2));
    setMensaje("");
  }

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="h-display text-2xl font-bold">Motor de reglas</h1>
          <p className="text-sm text-slate-500">
            Catálogo T2 vigente · versión <b className="cifra">{data?.version}</b>. Cada publicación cierra la vigencia anterior y queda auditada.
          </p>
        </div>
      </header>

      {mensaje && <p className={`text-sm ${publicar.isError ? "text-sem-rojo" : "text-sem-verde"}`}>{mensaje}</p>}

      {editando && (
        <Card>
          <CardHeader><CardTitle>Nueva versión de {editando}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Textarea rows={14} value={json} onChange={(e) => setJson(e.target.value)} />
            <Campo label="Justificación del cambio (obligatoria, queda en auditoría)">
              <Input value={justificacion} onChange={(e) => setJustificacion(e.target.value)} />
            </Campo>
            <div className="flex gap-3">
              <Button onClick={() => publicar.mutate()} cargando={publicar.isPending}
                disabled={!justificacion.trim()}>
                <Save className="h-4 w-4" /> Publicar versión
              </Button>
              <Button variante="secundario" onClick={() => setEditando("")}>Cancelar</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {categorias.map((cat) => (
        <div key={cat}>
          <h2 className="mb-2 text-[12px] font-semibold uppercase tracking-wider text-slate-500">
            {cat === "veto" ? "Vetos no compensatorios" : cat === "semaforo" ? "Techos y condiciones de semáforo" : "Ejecución de puja"}
          </h2>
          <div className="grid gap-3 xl:grid-cols-2">
            {reglas.filter((r: any) => r.categoria === cat).map((r: any) => (
              <Card key={r.codigo}>
                <CardContent className="py-3.5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="font-cifra text-sm font-bold">{r.codigo}</span>
                      <Badge tono={TONO[r.categoria] ?? "neutro"}>{r.categoria}</Badge>
                      <span className="text-[11px] text-slate-400">v{r.version} · prio {r.prioridad}</span>
                    </div>
                    <div className="flex gap-1">
                      <Button variante="fantasma" className="!px-2 !py-1 text-[12px]"
                        onClick={() => setHistCodigo(histCodigo === r.codigo ? null : r.codigo)}>
                        <History className="h-3.5 w-3.5" /> Historial
                      </Button>
                      {esAdmin && (
                        <Button variante="fantasma" className="!px-2 !py-1 text-[12px]" onClick={() => abrirEditor(r)}>
                          Nueva versión
                        </Button>
                      )}
                    </div>
                  </div>
                  <div className="mt-2 space-y-1 text-[13px]">
                    <div className="text-slate-500">
                      Cuando <b>{"all" in r.cuando ? "TODAS" : "ALGUNA"}</b>:
                      <span className="ml-1.5 inline-flex flex-wrap gap-1.5">
                        {(r.cuando.all ?? r.cuando.any ?? []).map((c: any, i: number) => <Condicion key={i} c={c} />)}
                      </span>
                    </div>
                    <div className="text-slate-600">
                      {r.efecto.veto && <>Efecto: <b className="text-sem-rojo">VETO</b> — {r.efecto.veto.motivo}</>}
                      {r.efecto.techo_semaforo && <div>Techo de semáforo: <b>{r.efecto.techo_semaforo}</b></div>}
                      {r.efecto.condicion && <div>Condición: {r.efecto.condicion}</div>}
                    </div>
                  </div>
                  {histCodigo === r.codigo && (
                    <div className="mt-3 rounded-md border border-slate-100 bg-slate-50 p-2.5 text-[12px]">
                      {historial.isLoading && <span className="text-slate-400">Cargando historial…</span>}
                      {historial.isError && <span className="text-slate-400">Sin historial en BD (regla de semilla YAML).</span>}
                      {historial.data?.map((h: any) => (
                        <div key={h.version} className="flex flex-wrap gap-x-3 border-b border-slate-100 py-1 last:border-0">
                          <b className="cifra">v{h.version}</b>
                          <span>{fecha(h.vigente_desde)} → {h.vigente_hasta ? fecha(h.vigente_hasta) : "vigente"}</span>
                          {h.autor && <span className="text-slate-500">{h.autor}</span>}
                          {h.justificacion && <span className="text-slate-500">«{h.justificacion}»</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

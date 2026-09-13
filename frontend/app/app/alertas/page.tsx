"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Badge, Button, Campo, Card, CardContent, CardHeader, CardTitle, ErrorBox, Input, Select, Spinner, TabPanel, Tabs, TabsLista } from "@/components/ui";
import { BellPlus, Link2, Link2Off, Trash2 } from "lucide-react";
import type { PreferenciasNotificacion } from "@/lib/types";

const FUENTES = ["", "judicial_boe", "aeat", "tgss", "concursal", "banco", "notarial", "privada"];

function PestanaAlertas() {
  const qc = useQueryClient();
  const { data: alertas, isLoading, error } = useQuery({ queryKey: ["alertas"], queryFn: api.alertas });
  const [form, setForm] = useState({ nombre: "", fuente: "", valor_max: "", score_min: "" });

  const invalidar = () => qc.invalidateQueries({ queryKey: ["alertas"] });
  const crear = useMutation({
    mutationFn: () => {
      const criterios: Record<string, any> = {};
      if (form.fuente) criterios.fuente = form.fuente;
      if (form.valor_max) criterios.valor_max = Number(form.valor_max);
      if (form.score_min) criterios.score_min = Number(form.score_min);
      return api.crearAlerta({ nombre: form.nombre, criterios });
    },
    onSuccess: () => { setForm({ nombre: "", fuente: "", valor_max: "", score_min: "" }); invalidar(); },
  });
  const toggle = useMutation({
    mutationFn: ({ id, activa }: { id: string; activa: boolean }) => api.patchAlerta(id, { activa }),
    onSuccess: invalidar,
  });
  const eliminar = useMutation({ mutationFn: (id: string) => api.eliminarAlerta(id), onSuccess: invalidar });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as ApiError).message} />;

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader><CardTitle>Nueva alerta</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo label="Nombre"><Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></Campo>
            <Campo label="Fuente" ayuda="vacío = cualquier fuente">
              <Select value={form.fuente} onChange={(e) => setForm({ ...form, fuente: e.target.value })}>
                {FUENTES.map((f) => <option key={f} value={f}>{f || "(cualquiera)"}</option>)}
              </Select>
            </Campo>
            <Campo label="Valor de subasta máximo (€)"><Input type="number" value={form.valor_max} onChange={(e) => setForm({ ...form, valor_max: e.target.value })} /></Campo>
            <Campo label="Puntuación mínima (0–100)" ayuda="puntuación exprés orientativa; sin puntuación la subasta no casa">
              <Input type="number" min={0} max={100} value={form.score_min} onChange={(e) => setForm({ ...form, score_min: e.target.value })} />
            </Campo>
          </div>
          {crear.isError && <ErrorBox mensaje={(crear.error as ApiError).message} />}
          <Button onClick={() => crear.mutate()} cargando={crear.isPending} disabled={!form.nombre}>
            <BellPlus className="h-4 w-4" /> Crear alerta
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Mis alertas ({alertas?.length ?? 0})</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {(alertas ?? []).length === 0 && <p className="text-sm text-slate-500">Aún no tiene alertas. Cree una para recibir avisos de subastas captadas.</p>}
          {(alertas ?? []).map((a) => (
            <div key={a.id} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2.5">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{a.nombre}</div>
                <div className="truncate text-xs text-slate-500">
                  {a.criterios.fuente ? `fuente ${a.criterios.fuente}` : "cualquier fuente"}
                  {a.criterios.valor_max != null && ` · VS ≤ ${Number(a.criterios.valor_max).toLocaleString("es-ES")} €`}
                  {a.criterios.score_min != null && ` · puntuación ≥ ${a.criterios.score_min}`}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge tono={a.activa ? "verde" : "neutro"}>{a.activa ? "activa" : "pausada"}</Badge>
                <Button variante="secundario" className="!px-2.5 !py-1 text-xs"
                  onClick={() => toggle.mutate({ id: a.id, activa: !a.activa })}>
                  {a.activa ? "Pausar" : "Activar"}
                </Button>
                <Button variante="secundario" className="!px-2 !py-1 text-xs" onClick={() => eliminar.mutate(a.id)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function PestanaPreferencias() {
  const qc = useQueryClient();
  const { data: pref, isLoading, error } = useQuery({ queryKey: ["preferencias"], queryFn: api.preferencias });
  const [codigo, setCodigo] = useState<{ codigo: string; enlace?: string | null } | null>(null);

  const invalidar = () => qc.invalidateQueries({ queryKey: ["preferencias"] });
  const guardar = useMutation({
    mutationFn: (b: Partial<PreferenciasNotificacion>) => api.putPreferencias(b),
    onSuccess: invalidar,
  });
  const generarCodigo = useMutation({ mutationFn: api.codigoTelegram, onSuccess: (c) => setCodigo(c) });
  const desvincular = useMutation({ mutationFn: api.desvincularTelegram, onSuccess: () => { setCodigo(null); invalidar(); } });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as ApiError).message} />;
  if (!pref) return null;

  const toggleCanal = (canal: string) => {
    const canales = pref.canales.includes(canal) ? pref.canales.filter((c) => c !== canal) : [...pref.canales, canal];
    guardar.mutate({ canales });
  };

  return (
    <div className="space-y-5">
      {!pref.comunicaciones_activas && (
        <ErrorBox mensaje="Las comunicaciones están desactivadas (se dio de baja). Ninguna alerta se enviará." />
      )}
      <Card>
        <CardHeader><CardTitle>Canales y modo de envío</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            {["email", "telegram"].map((c) => (
              <label key={c} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={pref.canales.includes(c)} onChange={() => toggleCanal(c)} /> {c}
              </label>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Campo label="Modo">
              <Select value={pref.modo} onChange={(e) => guardar.mutate({ modo: e.target.value as PreferenciasNotificacion["modo"] })}>
                <option value="instantaneo">Instantáneo</option>
                <option value="digest_diario">Resumen diario</option>
                <option value="digest_semanal">Resumen semanal (lunes)</option>
              </Select>
            </Campo>
            <Campo label="Hora del resumen (UTC)">
              <Input type="number" min={0} max={23} defaultValue={pref.hora_digest}
                onBlur={(e) => guardar.mutate({ hora_digest: Number(e.target.value) })} />
            </Campo>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Campo label="Silencio desde (hora)" ayuda="en la franja de silencio nada se envía al instante">
              <Input type="number" min={0} max={23} defaultValue={pref.silencio_inicio ?? ""}
                onBlur={(e) => guardar.mutate({ silencio_inicio: e.target.value === "" ? null : Number(e.target.value) })} />
            </Campo>
            <Campo label="Silencio hasta (hora)">
              <Input type="number" min={0} max={23} defaultValue={pref.silencio_fin ?? ""}
                onBlur={(e) => guardar.mutate({ silencio_fin: e.target.value === "" ? null : Number(e.target.value) })} />
            </Campo>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Telegram</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {pref.telegram_vinculado ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm"><Badge tono="verde">vinculado</Badge> Recibirá las alertas en su chat de Telegram.</div>
              <Button variante="secundario" onClick={() => desvincular.mutate()} cargando={desvincular.isPending}>
                <Link2Off className="h-4 w-4" /> Desvincular
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-slate-500">Genere un código y envíe <code>/start CÓDIGO</code> al bot de SEIS en Telegram (caduca en 10 minutos, un solo uso).</p>
              <Button onClick={() => generarCodigo.mutate()} cargando={generarCodigo.isPending}>
                <Link2 className="h-4 w-4" /> Generar código
              </Button>
              {codigo && (
                <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
                  Código: <span className="font-mono text-lg font-bold tracking-widest">{codigo.codigo}</span>
                  {codigo.enlace && <> · <a className="text-primario underline" href={codigo.enlace} target="_blank" rel="noreferrer">abrir el bot</a></>}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function Alertas() {
  return (
    <div className="max-w-3xl space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Alertas</h1>
        <p className="text-sm text-slate-500">Avisos de subastas captadas que casan con sus criterios, por email o Telegram.</p>
      </header>
      <Tabs defecto="alertas">
        <TabsLista items={[{ valor: "alertas", etiqueta: "Alertas" }, { valor: "preferencias", etiqueta: "Preferencias" }]} />
        <TabPanel valor="alertas"><PestanaAlertas /></TabPanel>
        <TabPanel valor="preferencias"><PestanaPreferencias /></TabPanel>
      </Tabs>
    </div>
  );
}

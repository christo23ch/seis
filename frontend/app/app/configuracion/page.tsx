"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Card, CardContent, CardHeader, CardTitle, Campo, ErrorBox, Input, Select, Spinner } from "@/components/ui";
import { Save } from "lucide-react";

export default function Configuracion() {
  const qc = useQueryClient();
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";
  const { data, isLoading, error } = useQuery({ queryKey: ["perfiles"], queryFn: api.perfiles });
  const [codigo, setCodigo] = useState("");
  const [valores, setValores] = useState<Record<string, number>>({});
  const [mensaje, setMensaje] = useState("");

  useEffect(() => {
    if (data && !codigo) setCodigo(Object.keys(data)[0] ?? "");
  }, [data, codigo]);
  useEffect(() => {
    if (data && codigo && data[codigo]) {
      const nums: Record<string, number> = {};
      Object.entries(data[codigo]).forEach(([k, v]) => { if (typeof v === "number") nums[k] = v as number; });
      setValores(nums);
      setMensaje("");
    }
  }, [data, codigo]);

  const guardar = useMutation({
    mutationFn: () => api.putPerfil(codigo, { ...data![codigo], ...valores }),
    onSuccess: () => { setMensaje("Perfil actualizado. Los nuevos análisis usarán estos objetivos."); qc.invalidateQueries({ queryKey: ["perfiles"] }); },
    onError: (e: Error) => setMensaje(e.message),
  });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as Error).message} />;
  const perfil = data?.[codigo];

  return (
    <div className="max-w-3xl space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Perfiles de inversión</h1>
        <p className="text-sm text-slate-500">
          Objetivos y umbrales por estrategia (§9.6/§10). Los cambios quedan auditados y afectan solo a análisis nuevos.
        </p>
      </header>
      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Perfil</CardTitle>
          <div className="w-64">
            <Select value={codigo} onChange={(e) => setCodigo(e.target.value)}>
              {Object.entries(data ?? {}).map(([k, v]) => <option key={k} value={k}>{(v as any).nombre ?? k}</option>)}
            </Select>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {perfil && (
            <>
              <div className="flex gap-6 text-sm text-slate-500">
                <span>Código: <b className="text-slate-700">{codigo}</b></span>
                <span>Tipo: <b className="text-slate-700">{perfil.tipo}</b></span>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                {Object.entries(valores).map(([k, v]) => (
                  <Campo key={k} label={k.replace(/_/g, " ")}>
                    <Input type="number" step="any" value={v} disabled={!esAdmin}
                      onChange={(e) => setValores((s) => ({ ...s, [k]: Number(e.target.value) }))} />
                  </Campo>
                ))}
              </div>
              {mensaje && <p className={`text-sm ${guardar.isError ? "text-sem-rojo" : "text-sem-verde"}`}>{mensaje}</p>}
              {esAdmin ? (
                <Button onClick={() => guardar.mutate()} cargando={guardar.isPending}>
                  <Save className="h-4 w-4" /> Guardar cambios
                </Button>
              ) : (
                <p className="text-[13px] text-slate-400">Solo el rol administrador puede modificar perfiles.</p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

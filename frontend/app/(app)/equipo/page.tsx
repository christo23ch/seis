"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Badge, Button, Campo, Card, CardContent, CardHeader, CardTitle, ErrorBox, Input, Select, Spinner } from "@/components/ui";
import { UserPlus } from "lucide-react";

export default function Equipo() {
  const { usuario } = useAuth();
  const qc = useQueryClient();
  const { data: org, isLoading, error } = useQuery({ queryKey: ["organizacion"], queryFn: api.organizacion });

  const [form, setForm] = useState({ email: "", nombre: "", password: "", rol: "analista" });
  const [mensaje, setMensaje] = useState("");

  const crear = useMutation({
    mutationFn: () => api.crearMiembro(form),
    onSuccess: (m) => {
      setMensaje(`Miembro ${m.email} creado con rol ${m.rol}.`);
      setForm({ email: "", nombre: "", password: "", rol: "analista" });
      qc.invalidateQueries({ queryKey: ["organizacion"] });
    },
    onError: (e: Error) => setMensaje(e.message),
  });

  const toggle = useMutation({
    mutationFn: ({ id, activo }: { id: string; activo: boolean }) => api.patchMiembro(id, activo),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["organizacion"] }),
  });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBox mensaje={(error as ApiError).message} />;
  if (!org) return null;

  const puedeGestionar = org.puede_gestionar;

  return (
    <div className="max-w-3xl space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Mi equipo</h1>
        <p className="text-sm text-slate-500">
          Organización <span className="font-medium">{org.nombre}</span> — los análisis y resultados son privados de tu equipo.
        </p>
      </header>

      {puedeGestionar && (
        <Card>
          <CardHeader><CardTitle>Invitar miembro</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Campo>
              <Campo label="Nombre"><Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></Campo>
              <Campo label="Contraseña temporal"><Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Campo>
              <Campo label="Rol" ayuda="analista: crea análisis · lector: solo consulta">
                <Select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
                  <option value="analista">analista</option>
                  <option value="lector">lector</option>
                </Select>
              </Campo>
            </div>
            {mensaje && <p className={`text-sm ${crear.isError ? "text-sem-rojo" : "text-sem-verde"}`}>{mensaje}</p>}
            <Button onClick={() => crear.mutate()} cargando={crear.isPending} disabled={!form.email || !form.password}>
              <UserPlus className="h-4 w-4" /> Crear miembro
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Miembros ({org.miembros.length})</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {org.miembros.map((m) => (
            <div key={m.id} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2.5">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{m.nombre ?? m.email}</div>
                <div className="truncate text-xs text-slate-500">{m.email}</div>
              </div>
              <div className="flex items-center gap-2">
                {m.rol_org === "propietario" && <Badge tono="azul">propietario</Badge>}
                <Badge tono="neutro">{m.rol}</Badge>
                <Badge tono={m.activo ? "verde" : "rojo"}>{m.activo ? "activo" : "inactivo"}</Badge>
                {puedeGestionar && m.rol_org !== "propietario" && m.email !== usuario?.email && (
                  <Button variante="secundario" className="!px-2.5 !py-1 text-xs"
                    cargando={toggle.isPending && toggle.variables?.id === m.id}
                    onClick={() => toggle.mutate({ id: m.id, activo: !m.activo })}>
                    {m.activo ? "Desactivar" : "Activar"}
                  </Button>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

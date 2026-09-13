"use client";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Campo, Card, CardContent, CardHeader, CardTitle, Input, Select } from "@/components/ui";
import { UserPlus } from "lucide-react";

export default function Administracion() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";
  const { data: reglas } = useQuery({ queryKey: ["reglas"], queryFn: api.reglas });
  const { data: params } = useQuery({ queryKey: ["parametros"], queryFn: api.parametros });

  const [form, setForm] = useState({ email: "", nombre: "", password: "", rol: "analista" });
  const [mensaje, setMensaje] = useState("");
  const crear = useMutation({
    mutationFn: () => api.crearUsuario(form),
    onSuccess: (r) => { setMensaje(`Usuario ${r.email} creado con rol ${r.rol}.`); setForm({ email: "", nombre: "", password: "", rol: "analista" }); },
    onError: (e: Error) => setMensaje(e.message),
  });

  return (
    <div className="max-w-3xl space-y-5">
      <header>
        <h1 className="h-display text-2xl font-bold">Administración</h1>
        <p className="text-sm text-slate-500">Usuarios, roles y estado del conocimiento del sistema.</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <Info k="Versión de reglas (T2)" v={reglas?.version ?? "—"} />
        <Info k="Versión de parámetros (T3)" v={params?.version ?? "—"} />
        <Info k="API" v={(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/docs"} />
      </div>

      <Card>
        <CardHeader><CardTitle>Alta de usuario</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {esAdmin ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Campo>
                <Campo label="Nombre"><Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></Campo>
                <Campo label="Contraseña temporal"><Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Campo>
                <Campo label="Rol" ayuda="admin: todo · analista: crea análisis · lector: solo consulta">
                  <Select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
                    <option value="admin">admin</option><option value="analista">analista</option><option value="lector">lector</option>
                  </Select>
                </Campo>
              </div>
              {mensaje && <p className={`text-sm ${crear.isError ? "text-sem-rojo" : "text-sem-verde"}`}>{mensaje}</p>}
              <Button onClick={() => crear.mutate()} cargando={crear.isPending}
                disabled={!form.email || !form.password}>
                <UserPlus className="h-4 w-4" /> Crear usuario
              </Button>
            </>
          ) : (
            <p className="text-sm text-slate-500">Solo el rol administrador puede gestionar usuarios.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Gobernanza y auditoría</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm text-slate-600">
          <p>▸ Cada análisis congela versiones de reglas y parámetros: el resultado es reproducible para siempre (P1).</p>
          <p>▸ Todo cambio de reglas, parámetros, perfiles o usuarios genera una entrada en la tabla de auditoría con autor y delta.</p>
          <p>▸ La decisión final de puja pertenece al comité de inversión: el sistema recomienda, no ordena.</p>
        </CardContent>
      </Card>
    </div>
  );
}
const Info = ({ k, v }: { k: string; v: string }) => (
  <Card><CardContent className="py-3.5">
    <div className="text-[12px] font-medium uppercase tracking-wide text-slate-500">{k}</div>
    <div className="cifra mt-1 truncate text-sm font-semibold">{v}</div>
  </CardContent></Card>
);

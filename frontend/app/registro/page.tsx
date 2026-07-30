"use client";
import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input } from "@/components/ui";
import { Gavel } from "lucide-react";

// Página pública (sin login), hermana de /login y fuera del grupo (app) para no
// pasar por su guardia de sesión. El backend responde 201 exista o no la cuenta,
// así que esta pantalla nunca revela si una dirección está registrada: siempre
// muestra el mismo mensaje de «revise su correo».
export default function RegistroPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [estado, setEstado] = useState<"inicial" | "cargando" | "hecho" | "error">("inicial");
  const [mensaje, setMensaje] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEstado("cargando");
    try {
      const r = await api.registro({ email, password, nombre: nombre || undefined });
      setMensaje(r.mensaje);
      setEstado("hecho");
    } catch (err) {
      setMensaje(err instanceof ApiError ? err.message : "No se pudo completar el registro");
      setEstado("error");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>

        {estado === "hecho" ? (
          <>
            <h1 className="h-display text-xl font-semibold">Revise su correo</h1>
            <p className="rounded-md border border-sem-verde/30 bg-sem-verdebg px-4 py-3 text-sm text-sem-verde">{mensaje}</p>
            <p className="text-sm text-slate-600">
              El enlace de confirmación caduca en 24 horas. Hasta que confirme la dirección, la cuenta no se activa.
            </p>
            <Link href="/login" className="block text-sm text-primario hover:underline">Volver a iniciar sesión</Link>
          </>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <h1 className="h-display text-xl font-semibold">Crear una cuenta</h1>
            <p className="text-sm text-slate-600">
              Se creará una organización propia de la que usted será propietario.
            </p>
            <Campo label="Nombre (opcional)">
              <Input autoComplete="name" value={nombre} onChange={(e) => setNombre(e.target.value)} />
            </Campo>
            <Campo label="Email">
              <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Campo>
            <Campo label="Contraseña">
              <Input type="password" autoComplete="new-password" minLength={8} value={password}
                     onChange={(e) => setPassword(e.target.value)} required />
            </Campo>
            <p className="text-[12px] text-slate-400">Mínimo 8 caracteres.</p>
            {estado === "error" && <p className="text-sm text-sem-rojo">{mensaje}</p>}
            <Button type="submit" className="w-full" cargando={estado === "cargando"}>Crear cuenta</Button>
            <p className="text-sm text-slate-600">
              ¿Ya tiene cuenta? <Link href="/login" className="text-primario hover:underline">Inicie sesión</Link>
            </p>
          </form>
        )}
      </div>
    </main>
  );
}

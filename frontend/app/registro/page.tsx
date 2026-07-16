"use client";
import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input } from "@/components/ui";
import { Gavel } from "lucide-react";

export default function RegistroPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setCargando(true);
    try {
      await api.registro({ email, password, nombre: nombre || undefined });
      setEnviado(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar el registro");
    } finally { setCargando(false); }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-tinta p-10 text-white lg:flex">
        <div className="flex items-center gap-2.5 text-lg font-semibold">
          <Gavel className="h-6 w-6 text-primario-tenue" /> SEIS
        </div>
        <div>
          <h1 className="h-display max-w-md text-4xl font-bold leading-tight">
            La disciplina de precio, convertida en software.
          </h1>
          <p className="mt-4 max-w-md text-slate-300">
            Crea tu cuenta y la organización de tu equipo en un paso.
          </p>
        </div>
        <p className="text-[12px] text-slate-500">
          El sistema recomienda; la decisión de puja pertenece al comité de inversión.
        </p>
      </section>
      <section className="flex items-center justify-center p-6">
        {enviado ? (
          <div className="w-full max-w-sm space-y-4 text-center">
            <div className="lg:hidden mb-6 flex items-center justify-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
            <h2 className="text-xl font-semibold">Revisa tu email</h2>
            <p className="text-sm text-slate-500">
              Hemos enviado un enlace de verificación a <span className="font-medium">{email}</span>.
              El enlace caduca en 24 horas.
            </p>
            <Link href="/login" className="inline-block text-sm text-primario-tenue underline">
              Volver a iniciar sesión
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4">
            <div className="lg:hidden mb-6 flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
            <h2 className="text-xl font-semibold">Crear cuenta</h2>
            <Campo label="Nombre">
              <Input value={nombre} onChange={(e) => setNombre(e.target.value)} />
            </Campo>
            <Campo label="Email">
              <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Campo>
            <Campo label="Contraseña" ayuda="Mínimo 8 caracteres">
              <Input type="password" autoComplete="new-password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
            </Campo>
            {error && <p className="text-sm text-sem-rojo">{error}</p>}
            <Button type="submit" className="w-full" cargando={cargando} disabled={!email || password.length < 8}>
              Crear cuenta
            </Button>
            <p className="text-[12px] text-slate-400">
              ¿Ya tienes cuenta? <Link href="/login" className="underline">Inicia sesión</Link>
            </p>
          </form>
        )}
      </section>
    </main>
  );
}

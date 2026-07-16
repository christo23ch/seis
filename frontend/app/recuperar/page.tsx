"use client";
import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input } from "@/components/ui";
import { Gavel } from "lucide-react";

export default function RecuperarPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setCargando(true);
    try {
      await api.recuperar(email);
      setEnviado(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo procesar la solicitud");
    } finally { setCargando(false); }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4">
        <div className="mb-6 flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
        {enviado ? (
          <div className="space-y-4 text-center">
            <h2 className="text-xl font-semibold">Revisa tu email</h2>
            <p className="text-sm text-slate-500">
              Si la cuenta existe, recibirás instrucciones para restablecer tu contraseña.
            </p>
            <Link href="/login" className="inline-block text-sm text-primario-tenue underline">
              Volver a iniciar sesión
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <h2 className="text-xl font-semibold">Recuperar contraseña</h2>
            <p className="text-sm text-slate-500">
              Introduce tu email y te enviaremos un enlace para restablecer tu contraseña.
            </p>
            <Campo label="Email">
              <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Campo>
            {error && <p className="text-sm text-sem-rojo">{error}</p>}
            <Button type="submit" className="w-full" cargando={cargando} disabled={!email}>
              Enviar enlace
            </Button>
            <p className="text-[12px] text-slate-400">
              <Link href="/login" className="underline">Volver a iniciar sesión</Link>
            </p>
          </form>
        )}
      </div>
    </main>
  );
}

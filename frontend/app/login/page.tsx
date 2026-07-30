"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input } from "@/components/ui";
import { Gavel } from "lucide-react";

export default function LoginPage() {
  const { entrar } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  // El backend distingue «sin verificar» (403) de «credenciales incorrectas»
  // (401). Solo en el primer caso tiene sentido ofrecer el reenvío del correo.
  const [sinVerificar, setSinVerificar] = useState(false);
  const [reenviado, setReenviado] = useState("");
  const [cargando, setCargando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setSinVerificar(false); setReenviado(""); setCargando(true);
    try {
      await entrar(email, password);
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        setSinVerificar(err.status === 403);
      } else {
        setError("No se pudo iniciar sesión");
      }
    } finally { setCargando(false); }
  }

  async function reenviar() {
    try {
      const r = await api.reenviarVerificacion(email);
      setReenviado(r.mensaje);
    } catch {
      setReenviado("No se pudo reenviar el correo de confirmación");
    }
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
            Sistema Experto de Inversión en Subastas: escalera de precios, riesgo agregado,
            semáforo y checklist — determinista, auditable y explicable.
          </p>
        </div>
        <p className="text-[12px] text-slate-500">
          El sistema recomienda; la decisión de puja pertenece al comité de inversión.
        </p>
      </section>
      <section className="flex items-center justify-center p-6">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4">
          <div className="lg:hidden mb-6 flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
          <h2 className="text-xl font-semibold">Iniciar sesión</h2>
          <Campo label="Email">
            <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Campo>
          <Campo label="Contraseña">
            <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Campo>
          {error && <p className="text-sm text-sem-rojo">{error}</p>}
          {sinVerificar && !reenviado && (
            <Button type="button" variante="secundario" className="w-full" onClick={reenviar}>
              Reenviar el correo de confirmación
            </Button>
          )}
          {reenviado && (
            <p className="rounded-md border border-sem-verde/30 bg-sem-verdebg px-4 py-3 text-sm text-sem-verde">{reenviado}</p>
          )}
          <Button type="submit" className="w-full" cargando={cargando}>Entrar</Button>
          <div className="flex items-center justify-between text-sm">
            <Link href="/registro" className="text-primario hover:underline">Crear una cuenta</Link>
            <Link href="/recuperar" className="text-primario hover:underline">He olvidado mi contraseña</Link>
          </div>
          <p className="text-[12px] text-slate-400">Primer arranque: admin@seis.local / admin (cámbiela de inmediato).</p>
        </form>
      </section>
    </main>
  );
}

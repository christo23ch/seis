"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input } from "@/components/ui";
import { Gavel } from "lucide-react";

function ResetearContenido() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token");
  const [nueva, setNueva] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [hecho, setHecho] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) { setError("Falta el token de reseteo en el enlace."); return; }
    setError(""); setCargando(true);
    try {
      await api.resetear(token, nueva);
      setHecho(true);
      setTimeout(() => router.replace("/login"), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo restablecer la contraseña");
    } finally { setCargando(false); }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4">
        <div className="mb-6 flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
        {hecho ? (
          <div className="space-y-4 text-center">
            <h2 className="text-xl font-semibold text-sem-verde">Contraseña actualizada</h2>
            <p className="text-sm text-slate-500">Te llevamos a iniciar sesión…</p>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <h2 className="text-xl font-semibold">Restablecer contraseña</h2>
            <Campo label="Nueva contraseña" ayuda="Mínimo 8 caracteres">
              <Input type="password" autoComplete="new-password" minLength={8} value={nueva} onChange={(e) => setNueva(e.target.value)} required />
            </Campo>
            {error && <p className="text-sm text-sem-rojo">{error}</p>}
            <Button type="submit" className="w-full" cargando={cargando} disabled={!token || nueva.length < 8}>
              Restablecer
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

export default function ResetearPage() {
  return (
    <Suspense fallback={null}>
      <ResetearContenido />
    </Suspense>
  );
}

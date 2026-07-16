"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Gavel } from "lucide-react";

function VerificarContenido() {
  const params = useSearchParams();
  const token = params.get("token");
  const [estado, setEstado] = useState<"cargando" | "ok" | "error">("cargando");
  const [mensaje, setMensaje] = useState("");

  useEffect(() => {
    if (!token) { setEstado("error"); setMensaje("Falta el token de verificación en el enlace."); return; }
    api.verificar(token)
      .then((r) => { setEstado("ok"); setMensaje(r.mensaje); })
      .catch((err) => {
        setEstado("error");
        setMensaje(err instanceof ApiError ? err.message : "No se pudo verificar la cuenta");
      });
  }, [token]);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4 text-center">
        <div className="mb-6 flex items-center justify-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
        {estado === "cargando" && <p className="text-sm text-slate-500">Verificando tu cuenta…</p>}
        {estado === "ok" && (
          <>
            <h2 className="text-xl font-semibold text-sem-verde">Cuenta verificada</h2>
            <p className="text-sm text-slate-500">{mensaje}</p>
          </>
        )}
        {estado === "error" && (
          <>
            <h2 className="text-xl font-semibold text-sem-rojo">No se pudo verificar</h2>
            <p className="text-sm text-slate-500">{mensaje}</p>
          </>
        )}
        <Link href="/login" className="inline-block text-sm text-primario-tenue underline">
          Ir a iniciar sesión
        </Link>
      </div>
    </main>
  );
}

export default function VerificarPage() {
  return (
    <Suspense fallback={null}>
      <VerificarContenido />
    </Suspense>
  );
}

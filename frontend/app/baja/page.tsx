"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Spinner } from "@/components/ui";
import { Gavel } from "lucide-react";

// Página pública (sin login): el enlace de baja de cada email lleva un token
// firmado con propósito «baja». Confirmar aquí desactiva las comunicaciones.
function ConfirmarBaja() {
  const token = useSearchParams().get("token") ?? "";
  const [estado, setEstado] = useState<"inicial" | "cargando" | "hecho" | "error">("inicial");
  const [mensaje, setMensaje] = useState("");

  async function darDeBaja() {
    setEstado("cargando");
    try {
      const r = await api.baja(token);
      setMensaje(r.mensaje);
      setEstado("hecho");
    } catch (err) {
      setMensaje(err instanceof ApiError ? err.message : "No se pudo procesar la baja");
      setEstado("error");
    }
  }

  return (
    <div className="w-full max-w-sm space-y-4">
      <div className="flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
      <h1 className="h-display text-xl font-semibold">Baja de comunicaciones</h1>

      {!token && <p className="text-sm text-sem-rojo">El enlace no incluye un token válido.</p>}

      {token && estado !== "hecho" && (
        <>
          <p className="text-sm text-slate-600">
            Al confirmar dejará de recibir alertas y resúmenes de SEIS por cualquier canal.
            Podrá reactivarlas desde <span className="font-medium">Alertas → Preferencias</span> iniciando sesión.
          </p>
          {estado === "error" && <p className="text-sm text-sem-rojo">{mensaje}</p>}
          <Button onClick={darDeBaja} cargando={estado === "cargando"} className="w-full">
            Confirmar baja
          </Button>
        </>
      )}

      {estado === "hecho" && (
        <p className="rounded-md border border-sem-verde/30 bg-sem-verdebg px-4 py-3 text-sm text-sem-verde">{mensaje}</p>
      )}
    </div>
  );
}

export default function BajaPage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <Suspense fallback={<Spinner />}>
        <ConfirmarBaja />
      </Suspense>
    </main>
  );
}

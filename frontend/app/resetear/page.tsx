"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input, Spinner } from "@/components/ui";
import { Gavel } from "lucide-react";

// Página pública: el correo de recuperación trae un token firmado con propósito
// «resetear», de un solo uso y válido una hora. Mismo patrón que /baja.
function FormularioReseteo() {
  const token = useSearchParams().get("token") ?? "";
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [estado, setEstado] = useState<"inicial" | "cargando" | "hecho" | "error">("inicial");
  const [mensaje, setMensaje] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (nueva !== repetida) {
      setMensaje("Las dos contraseñas no coinciden");
      setEstado("error");
      return;
    }
    setEstado("cargando");
    try {
      const r = await api.resetear(token, nueva);
      setMensaje(r.mensaje);
      setEstado("hecho");
    } catch (err) {
      setMensaje(err instanceof ApiError ? err.message : "No se pudo cambiar la contraseña");
      setEstado("error");
    }
  }

  if (!token) return <p className="text-sm text-sem-rojo">El enlace no incluye un token válido.</p>;

  if (estado === "hecho") {
    return (
      <>
        <p className="rounded-md border border-sem-verde/30 bg-sem-verdebg px-4 py-3 text-sm text-sem-verde">{mensaje}</p>
        <Link href="/login" className="block"><Button className="w-full">Iniciar sesión</Button></Link>
      </>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Campo label="Contraseña nueva">
        <Input type="password" autoComplete="new-password" minLength={8} value={nueva}
               onChange={(e) => setNueva(e.target.value)} required />
      </Campo>
      <Campo label="Repita la contraseña">
        <Input type="password" autoComplete="new-password" minLength={8} value={repetida}
               onChange={(e) => setRepetida(e.target.value)} required />
      </Campo>
      <p className="text-[12px] text-slate-400">Mínimo 8 caracteres.</p>
      {estado === "error" && <p className="text-sm text-sem-rojo">{mensaje}</p>}
      <Button type="submit" className="w-full" cargando={estado === "cargando"}>Guardar la contraseña</Button>
      <Link href="/recuperar" className="block text-sm text-primario hover:underline">Solicitar un enlace nuevo</Link>
    </form>
  );
}

export default function ResetearPage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
        <h1 className="h-display text-xl font-semibold">Nueva contraseña</h1>
        <Suspense fallback={<Spinner />}>
          <FormularioReseteo />
        </Suspense>
      </div>
    </main>
  );
}

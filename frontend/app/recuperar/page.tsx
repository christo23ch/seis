"use client";
import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input } from "@/components/ui";
import { Gavel } from "lucide-react";

// Página pública. El backend responde 200 exista o no la cuenta, de modo que
// esta pantalla no puede usarse para averiguar qué direcciones están dadas de
// alta: el mensaje de confirmación es siempre el mismo.
export default function RecuperarPage() {
  const [email, setEmail] = useState("");
  const [estado, setEstado] = useState<"inicial" | "cargando" | "hecho" | "error">("inicial");
  const [mensaje, setMensaje] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEstado("cargando");
    try {
      const r = await api.recuperar(email);
      setMensaje(r.mensaje);
      setEstado("hecho");
    } catch (err) {
      setMensaje(err instanceof ApiError ? err.message : "No se pudo procesar la solicitud");
      setEstado("error");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
        <h1 className="h-display text-xl font-semibold">Recuperar el acceso</h1>

        {estado === "hecho" ? (
          <>
            <p className="rounded-md border border-sem-verde/30 bg-sem-verdebg px-4 py-3 text-sm text-sem-verde">{mensaje}</p>
            <p className="text-sm text-slate-600">El enlace caduca en una hora y solo puede usarse una vez.</p>
            <Link href="/login" className="block text-sm text-primario hover:underline">Volver a iniciar sesión</Link>
          </>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <p className="text-sm text-slate-600">
              Indique su dirección y le enviaremos un enlace para establecer una contraseña nueva.
            </p>
            <Campo label="Email">
              <Input type="email" autoComplete="username" value={email}
                     onChange={(e) => setEmail(e.target.value)} required />
            </Campo>
            {estado === "error" && <p className="text-sm text-sem-rojo">{mensaje}</p>}
            <Button type="submit" className="w-full" cargando={estado === "cargando"}>Enviar el enlace</Button>
            <Link href="/login" className="block text-sm text-primario hover:underline">Volver a iniciar sesión</Link>
          </form>
        )}
      </div>
    </main>
  );
}

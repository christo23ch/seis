"use client";
import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Check, Input } from "@/components/ui";
import { Gavel } from "lucide-react";

// Página pública (sin login), hermana de /login y fuera del grupo (app) para no
// pasar por su guardia de sesión. El backend responde 201 exista o no la cuenta,
// así que esta pantalla nunca revela si una dirección está registrada: siempre
// muestra el mismo mensaje de «revise su correo».
export default function RegistroPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  // Fase 14 (RGPD). Todos empiezan DESMARCADOS, incluido el obligatorio: una
  // casilla premarcada no recoge consentimiento, porque no hay acto por parte
  // de quien la deja como estaba.
  const [aceptaTerminos, setAceptaTerminos] = useState(false);
  const [aceptaPrivacidad, setAceptaPrivacidad] = useState(false);
  const [aceptaComerciales, setAceptaComerciales] = useState(false);
  const [estado, setEstado] = useState<"inicial" | "cargando" | "hecho" | "error">("inicial");
  const [mensaje, setMensaje] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEstado("cargando");
    try {
      const r = await api.registro({
        email, password, nombre: nombre || undefined,
        acepta_terminos: aceptaTerminos,
        acepta_privacidad: aceptaPrivacidad,
        acepta_comunicaciones_comerciales: aceptaComerciales,
      });
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

            <fieldset className="space-y-3 border-t border-slate-200 pt-4">
              <legend className="sr-only">Consentimientos</legend>
              {/* `required` en los dos obligatorios: el navegador impide enviar
                  el formulario sin marcarlos, así que quien se registra no llega
                  a ver un 422 del servidor. La validación del backend sigue
                  siendo la que manda — esta solo evita el viaje. */}
              <Check
                required
                checked={aceptaTerminos}
                onChange={(e) => setAceptaTerminos(e.target.checked)}
                label={<>Acepto las <Link href="/legal/terminos" target="_blank" className="text-primario hover:underline">condiciones del servicio</Link>.</>}
              />
              <Check
                required
                checked={aceptaPrivacidad}
                onChange={(e) => setAceptaPrivacidad(e.target.checked)}
                label={<>He leído la <Link href="/legal/privacidad" target="_blank" className="text-primario hover:underline">política de privacidad</Link>.</>}
              />
              {/* Sin `required`, y esto no es un olvido: condicionar el alta a
                  aceptar publicidad haría que el consentimiento no fuera libre,
                  y entonces no valdría como consentimiento. */}
              <Check
                checked={aceptaComerciales}
                onChange={(e) => setAceptaComerciales(e.target.checked)}
                label={<>Quiero recibir novedades del producto por correo <span className="text-slate-400">(opcional)</span>.</>}
              />
            </fieldset>

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

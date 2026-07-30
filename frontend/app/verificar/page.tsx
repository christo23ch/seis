"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Campo, Input, Spinner } from "@/components/ui";
import { Gavel } from "lucide-react";

// Página pública: el correo de alta trae un token firmado con propósito
// «verificar». Mismo patrón que /baja — componente partido con <Suspense> porque
// useSearchParams obliga a ello en Next 15.
//
// La confirmación exige un clic y NO se dispara al montar la página. El token es
// de un solo uso, y hay mucho software que abre los enlaces de un correo sin que
// nadie se lo pida: escáneres corporativos tipo Safe Links, antivirus,
// previsualizadores del propio cliente de correo. Si la verificación ocurriera en
// un `useEffect`, cualquiera de ellos gastaría el enlace antes que su
// destinatario, que se encontraría un error habiendo hecho todo bien.
function ConfirmarCuenta() {
  const token = useSearchParams().get("token") ?? "";
  const [estado, setEstado] = useState<"inicial" | "cargando" | "hecho" | "error">("inicial");
  const [mensaje, setMensaje] = useState("");

  async function confirmar() {
    setEstado("cargando");
    try {
      const r = await api.verificar(token);
      setMensaje(r.mensaje);
      setEstado("hecho");
    } catch (err) {
      setMensaje(err instanceof ApiError ? err.message : "No se pudo verificar la cuenta");
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

  if (estado === "error") return <ReintentarVerificacion mensaje={mensaje} />;

  return (
    <>
      <p className="text-sm text-slate-600">
        Confirme que esta dirección es suya para activar la cuenta. El enlace solo puede usarse una vez.
      </p>
      <Button onClick={confirmar} cargando={estado === "cargando"} className="w-full">
        Confirmar mi cuenta
      </Button>
    </>
  );
}

// Un enlace caducado dejaría la cuenta sin salida: no puede entrar por no estar
// verificada, ni verificarse porque su único enlace expiró. Por eso el camino de
// error ofrece pedir uno nuevo en vez de ser un callejón sin salida.
function ReintentarVerificacion({ mensaje }: { mensaje: string }) {
  const [email, setEmail] = useState("");
  const [estado, setEstado] = useState<"inicial" | "cargando" | "hecho">("inicial");
  const [aviso, setAviso] = useState("");

  async function reenviar(e: React.FormEvent) {
    e.preventDefault();
    setEstado("cargando");
    try {
      const r = await api.reenviarVerificacion(email);
      setAviso(r.mensaje);
    } catch (err) {
      setAviso(err instanceof ApiError ? err.message : "No se pudo reenviar el correo");
    } finally {
      setEstado("hecho");
    }
  }

  return (
    <>
      <p className="text-sm text-sem-rojo">{mensaje}</p>
      {estado === "hecho" ? (
        <p className="rounded-md border border-sem-verde/30 bg-sem-verdebg px-4 py-3 text-sm text-sem-verde">{aviso}</p>
      ) : (
        <form onSubmit={reenviar} className="space-y-4">
          <p className="text-sm text-slate-600">Podemos enviarle un enlace nuevo.</p>
          <Campo label="Email">
            <Input type="email" autoComplete="username" value={email}
                   onChange={(e) => setEmail(e.target.value)} required />
          </Campo>
          <Button type="submit" className="w-full" cargando={estado === "cargando"}>
            Reenviar el correo de confirmación
          </Button>
        </form>
      )}
      <Link href="/login" className="block text-sm text-primario hover:underline">Volver a iniciar sesión</Link>
    </>
  );
}

export default function VerificarPage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" /> SEIS</div>
        <h1 className="h-display text-xl font-semibold">Confirmación de la cuenta</h1>
        <Suspense fallback={<Spinner />}>
          <ConfirmarCuenta />
        </Suspense>
      </div>
    </main>
  );
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { use } from "react";
import { api, ApiError } from "@/lib/api";
import { Gavel } from "lucide-react";

type Texto = {
  tipo: string; titulo: string; version: string; cuerpo: string;
  obligatorio: boolean; pendiente_de_redaccion: boolean;
};

// Página pública: los textos legales hay que poder leerlos ANTES de tener
// cuenta. Una casilla de consentimiento que no deja leer lo que se acepta no
// recoge consentimiento, recoge un clic.
export default function LegalPage({ params }: { params: Promise<{ tipo: string }> }) {
  const { tipo } = use(params);
  const [texto, setTexto] = useState<Texto | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.textoLegal(tipo)
      .then(setTexto)
      .catch((e) => setError(e instanceof ApiError ? e.message : "No se pudo cargar el texto"));
  }, [tipo]);

  return (
    <main className="mx-auto max-w-2xl p-6">
      <Link href="/registro" className="mb-6 flex items-center gap-2 text-lg font-semibold">
        <Gavel className="h-5 w-5" /> SEIS
      </Link>
      {error && <p className="text-sm text-sem-rojo">{error}</p>}
      {texto && (
        <article className="space-y-4">
          <header className="space-y-1">
            <h1 className="h-display text-2xl font-semibold">{texto.titulo}</h1>
            <p className="text-sm text-slate-500">Versión {texto.version}</p>
          </header>
          {/* Se avisa en vez de ocultarlo: un texto provisional presentado como
              definitivo es peor que uno que se declara provisional. */}
          {texto.pendiente_de_redaccion && (
            <p className="rounded-md border border-sem-amarillo/40 bg-sem-amarillobg px-4 py-3 text-sm">
              Este texto está pendiente de redacción legal. Se publicará antes de la
              apertura del servicio y la versión subirá al hacerlo.
            </p>
          )}
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            {texto.cuerpo}
          </div>
        </article>
      )}
    </main>
  );
}

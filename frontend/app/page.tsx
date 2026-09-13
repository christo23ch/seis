import Link from "next/link";
import type { Metadata } from "next";
import { Gavel, ListChecks, Lock, Ruler, ShieldAlert, TriangleAlert } from "lucide-react";
import { rutaApp } from "@/lib/rutas";

// ⚠️ CONTENIDO PROVISIONAL, Y ESTÁ DICHO A PROPÓSITO.
//
// Esta página es la ESTRUCTURA de la landing con los tokens del sistema de diseño
// aplicados. El texto describe únicamente lo que el motor hace de verdad —la
// escalera de precios, el semáforo, los cuatro índices, la matriz de nueve
// dimensiones, el acta inmutable— y NO contiene ni una cifra de negocio, ni un
// testimonio, ni un precio, ni un nombre de cliente. Nada de eso existe todavía y
// no se inventa: la ficha de la Fase 15 asigna el contenido real al responsable
// del producto (`docs/PLAN_FASES.md`).
//
// La misma regla que el motor aplica a sus informes (ADR-0015): antes un hueco
// declarado que un número que alguien se va a creer.

export const metadata: Metadata = {
  title: "SEIS · La disciplina de precio, convertida en software",
  description:
    "Análisis determinista, auditable y explicable de inversión en subastas: escalera de precios, "
    + "riesgo agregado, semáforo y checklist. El sistema recomienda; la decisión de puja es tuya.",
};

const CAPACIDADES = [
  {
    icono: Ruler,
    titulo: "Una escalera de precios, no una corazonada",
    texto: "Cuatro peldaños calculados con fórmulas cerradas: precio ideal, objetivo, máximo y "
      + "un límite absoluto que el software no deja cruzar. Se cargan en la interfaz de puja "
      + "antes de abrir la sesión.",
  },
  {
    icono: ShieldAlert,
    titulo: "Riesgo medido en nueve dimensiones",
    texto: "Jurídico, documental, ocupación, urbanístico, técnico, financiero, comercial, "
      + "liquidez y mercado. Cada uno con probabilidad, impacto y las condiciones que habría "
      + "que cumplir para mitigarlo.",
  },
  {
    icono: TriangleAlert,
    titulo: "Dice lo que no sabe",
    texto: "Cuando faltan comparables, no hay valor de referencia del Catastro o el estado "
      + "posesorio está sin verificar, el análisis lo declara y baja su propia confianza. "
      + "Un hueco declarado vale más que un número que nadie puede sostener.",
  },
  {
    icono: ListChecks,
    titulo: "Checklist con puntos bloqueantes",
    texto: "Documental, jurídico, fiscal, económico y técnico. Lo que está pendiente aparece "
      + "como pendiente, y lo bloqueante impide dar la operación por buena.",
  },
  {
    icono: Lock,
    titulo: "Acta inmutable",
    texto: "Cada análisis queda congelado con la versión de reglas y de parámetros con la que "
      + "se calculó. Seis meses después se puede reconstruir por qué dijo lo que dijo.",
  },
  {
    icono: Gavel,
    titulo: "Determinista, no generativo",
    texto: "Las mismas entradas dan siempre la misma salida, y cada regla que se dispara queda "
      + "trazada con su código y su versión. No hay nada que adivinar.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-papel">
      <header className="border-b border-borde-linea bg-papel-carta">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-4 px-4 py-4 md:px-8">
          <span className="flex items-center gap-2 text-guia font-semibold text-tinta">
            <Gavel className="h-5 w-5 text-primario" /> SEIS
          </span>
          <nav className="flex items-center gap-3 text-menor">
            <Link href="/ayuda" className="rounded px-2 py-1 text-tinta-suave hover:text-primario">
              Cómo funciona
            </Link>
            <Link href="/login" className="rounded px-2 py-1 font-medium text-primario hover:underline">
              Entrar
            </Link>
            <Link href="/registro"
              className="rounded-md bg-primario px-3 py-2 font-medium text-white hover:bg-primario-hover">
              Crear una cuenta
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1200px] px-4 md:px-8">
        {/* Portada: una sola idea y una sola acción. */}
        <section className="py-14 md:py-20">
          <h1 className="h-display max-w-[26ch] text-h1 font-semibold leading-tight text-tinta md:text-[44px]">
            La disciplina de precio, convertida en software.
          </h1>
          <p className="mt-5 max-w-[62ch] text-guia text-tinta-suave">
            SEIS analiza una subasta inmobiliaria y devuelve el precio máximo al que la operación
            sigue teniendo sentido — con el riesgo desglosado, lo que falta por verificar y el
            rastro completo de cómo llegó a esa cifra.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/registro"
              className="rounded-md bg-primario px-5 py-3 text-base font-medium text-white hover:bg-primario-hover">
              Crear una cuenta
            </Link>
            <Link href="/ayuda"
              className="rounded-md border border-borde-control px-5 py-3 text-base font-medium text-tinta hover:bg-papel-carta">
              Ver cómo funciona
            </Link>
          </div>
          <p className="mt-6 max-w-[62ch] text-menor text-tinta-suave">
            El sistema recomienda; la decisión de puja pertenece al comité de inversión.
          </p>
        </section>

        <section className="grid gap-4 pb-16 sm:grid-cols-2 lg:grid-cols-3">
          {CAPACIDADES.map(({ icono: Ico, titulo, texto }) => (
            <article key={titulo}
              className="rounded-lg border border-borde-linea bg-papel-carta p-5 shadow-carta">
              <Ico className="h-5 w-5 text-primario" aria-hidden="true" />
              <h2 className="h-display mt-3 text-h3 font-semibold text-tinta">{titulo}</h2>
              <p className="mt-2 text-menor text-tinta-suave">{texto}</p>
            </article>
          ))}
        </section>
      </main>

      <footer className="border-t border-borde-linea bg-papel-carta">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-3 px-4 py-6 text-micro text-tinta-suave md:px-8">
          <span>SEIS · Sistema Experto de Inversión en Subastas</span>
          <nav className="flex flex-wrap gap-4">
            <Link href="/legal/terminos" className="hover:text-primario">Condiciones</Link>
            <Link href="/legal/privacidad" className="hover:text-primario">Privacidad</Link>
            <Link href={rutaApp()} className="hover:text-primario">Ir a la aplicación</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}

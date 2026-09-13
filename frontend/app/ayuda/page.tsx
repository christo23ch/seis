import Link from "next/link";
import type { Metadata } from "next";
import { Gavel } from "lucide-react";

// ⚠️ CONTENIDO PROVISIONAL. Describe el funcionamiento real del motor —los pasos,
// los cuatro índices, la escalera— y nada más: ni cifras de negocio, ni precios,
// ni plazos comerciales. El texto definitivo y el MANUAL_DE_USUARIO.md los escribe
// el responsable del producto (ficha de la Fase 15).

export const metadata: Metadata = {
  title: "Cómo funciona SEIS",
  description: "Qué hace el motor, en qué orden, y qué significa cada número del informe.",
};

const PASOS = [
  {
    n: "1",
    titulo: "Se describe el activo y la subasta",
    texto: "Tipología, superficie, año, estado de conservación, municipio y comunidad autónoma; "
      + "valor de subasta, depósito y fuente. Cuanto más se declare, más sube la confianza del "
      + "análisis — y lo que no se declare queda registrado como carencia, no se rellena solo.",
  },
  {
    n: "2",
    titulo: "Se valora contra comparables",
    texto: "Con comparables de mercado el motor calcula un valor de mercado y su dispersión. "
      + "Sin ellos lo dice: la confianza cae a cero y la carencia aparece en el informe, porque "
      + "un análisis que se compara consigo mismo no informa de nada.",
  },
  {
    n: "3",
    titulo: "Se mide el riesgo y la información disponible",
    texto: "Cuatro índices. ICI: cuánta información hay de verdad. ICU: calidad de la ubicación. "
      + "RA: riesgo agregado sobre nueve dimensiones, con dominancia de las críticas. "
      + "ICO: la síntesis multicriterio.",
  },
  {
    n: "4",
    titulo: "Se calculan los costes con la fiscalidad real",
    texto: "Reforma por niveles, posesión, atrasos de comunidad e IBI, tenencia, "
      + "comercialización y contingencia. El impuesto de transmisiones se liquida sobre el mayor "
      + "de valor de referencia, valor declarado y precio pagado — no sobre la puja.",
  },
  {
    n: "5",
    titulo: "Se obtiene la escalera de precios",
    texto: "Precio ideal, objetivo, máximo y límite. El límite es infranqueable: es el punto "
      + "donde la operación deja de tener sentido incluso en el escenario estresado.",
  },
  {
    n: "6",
    titulo: "Se emite el semáforo, con sus condiciones",
    texto: "Verde, amarillo, naranja o rojo, con los vetos que se hayan disparado, las "
      + "condiciones que habría que cumplir antes de pujar y un checklist donde lo bloqueante "
      + "aparece como bloqueante.",
  },
];

const NUMEROS = [
  ["ICO", "Índice de calidad de la operación: la síntesis multicriterio, de 0 a 100."],
  ["RA", "Riesgo agregado, de 0 a 100. Una dimensión crítica no mitigable domina el resultado."],
  ["ICI", "Índice de confianza de la información. Penaliza lo que falta; no premia lo que se supone."],
  ["ICU", "Índice de calidad de la ubicación, entre macro y micro."],
  ["RVC", "Ratio de viabilidad competitiva: tu precio máximo frente a la adjudicación esperada. "
    + "Por debajo de 1 es probable que alguien puje más alto que tu límite."],
];

export default function Ayuda() {
  return (
    <div className="min-h-screen bg-papel">
      <header className="border-b border-borde-linea bg-papel-carta">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-4 px-4 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-2 text-guia font-semibold text-tinta">
            <Gavel className="h-5 w-5 text-primario" /> SEIS
          </Link>
          <nav className="flex items-center gap-3 text-menor">
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

      <main className="mx-auto max-w-[1200px] px-4 py-12 md:px-8">
        <h1 className="h-display max-w-[24ch] text-h1 font-semibold text-tinta">Cómo funciona</h1>
        <p className="mt-4 max-w-[68ch] text-guia text-tinta-suave">
          El motor es determinista: las mismas entradas dan siempre la misma salida, y cada regla
          que se dispara queda trazada con su código y su versión. Esto es el orden en que trabaja.
        </p>

        <ol className="mt-10 grid gap-4 md:grid-cols-2">
          {PASOS.map((p) => (
            <li key={p.n} className="rounded-lg border border-borde-linea bg-papel-carta p-5 shadow-carta">
              <span className="font-cifra text-menor font-semibold text-primario">Paso {p.n}</span>
              <h2 className="h-display mt-1.5 text-h3 font-semibold text-tinta">{p.titulo}</h2>
              <p className="mt-2 text-menor text-tinta-suave">{p.texto}</p>
            </li>
          ))}
        </ol>

        <h2 className="h-display mt-14 text-h2 font-semibold text-tinta">Qué significa cada número</h2>
        <dl className="mt-5 max-w-[80ch] divide-y divide-borde-linea rounded-lg border border-borde-linea bg-papel-carta">
          {NUMEROS.map(([clave, texto]) => (
            <div key={clave} className="flex flex-col gap-1 px-5 py-3.5 sm:flex-row sm:gap-5">
              <dt className="font-cifra text-menor font-bold text-tinta sm:w-16 sm:shrink-0">{clave}</dt>
              <dd className="text-menor text-tinta-suave">{texto}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-14 rounded-lg border border-borde-linea bg-papel-carta p-6 shadow-carta">
          <h2 className="h-display text-h3 font-semibold text-tinta">Lo que SEIS no hace</h2>
          <ul className="mt-3 max-w-[68ch] list-disc space-y-2 pl-5 text-menor text-tinta-suave">
            <li>No puja por ti ni se conecta a la plataforma de subastas.</li>
            <li>No sustituye la nota simple, el certificado de cargas ni la visita al inmueble:
              te dice cuáles faltan y cuánto baja la confianza por no tenerlos.</li>
            <li>No decide. <b className="text-tinta">El sistema recomienda; la decisión de puja
              pertenece al comité de inversión.</b></li>
          </ul>
        </div>

        <p className="mt-10 text-menor text-tinta-suave">
          <Link href="/" className="text-primario hover:underline">← Volver</Link>
        </p>
      </main>
    </div>
  );
}

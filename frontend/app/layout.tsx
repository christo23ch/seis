import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

// Fase 0' §2: Source Serif 4 en cabeceras, Inter en cuerpo. `next/font` las
// AUTO-ALOJA en el build —no se enlaza el CDN de Google—, porque servirlas desde
// `fonts.gstatic.com` mandaría la IP del visitante a un tercero fuera de la UE.
// Contrapartida declarada: el build necesita red la primera vez para bajarlas.
const inter = Inter({
  subsets: ["latin"], display: "swap", variable: "--fuente-texto",
});
const sourceSerif = Source_Serif_4({
  subsets: ["latin"], display: "swap", variable: "--fuente-display",
});

export const metadata: Metadata = {
  title: "SEIS · Sistema Experto de Inversión en Subastas",
  description: "Decisión determinista, auditable y explicable para inversión en subastas.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${inter.variable} ${sourceSerif.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

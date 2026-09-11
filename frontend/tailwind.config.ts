import type { Config } from "tailwindcss";

// Tokens del sistema de diseño. La justificación de cada bloque está en
// `docs/DESIGN_SYSTEM.md`; aquí solo van los valores. Nada de tipografía ni de
// color se inventa fuera de este fichero: esa era la causa raíz del diagnóstico
// (nueve tamaños distintos en 64 usos, y `fontSize` sin definir).
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tinta: { DEFAULT: "#101828", suave: "#1D2939", borde: "#2E3A4E" },
        papel: { DEFAULT: "#F5F6F8", carta: "#FFFFFF" },
        primario: { DEFAULT: "#2E4B8F", hover: "#243C73", tenue: "#E8EDF7" },
        // Dos bordes, y la diferencia importa (WCAG 1.4.11): `linea` separa y
        // decora —no le aplica el 3:1—; `control` delimita algo con lo que se
        // interactúa (campo, casilla, botón secundario) y SÍ debe cumplirlo.
        borde: { linea: "#E4E7EC", control: "#8C8E92" },
        // Semáforo: AAA (≥7:1) sobre su fondo, sobre blanco y sobre papel.
        // Medido y vigilado por backend/tests/test_contraste.py.
        sem: {
          verde: "#0F5E2C", verdebg: "#E8F5ED",
          amarillo: "#7F3A06", amarillobg: "#FFF6E1",
          naranja: "#8D2E09", naranjabg: "#FFEADF",
          rojo: "#9A1717", rojobg: "#FBE7E7",
        },
      },
      fontFamily: {
        // `Source Serif 4` va ENTRECOMILLADO dentro de la cadena y no es manía:
        // sin comillas, CSS lee `4` como un identificador —y ninguno puede empezar
        // por dígito—, así que invalida la declaración ENTERA y el navegador cae en
        // silencio a la fuente heredada. Se detectó midiendo `getComputedStyle` en
        // el navegador: el documento decía serif y la pantalla mostraba Inter.
        display: ["var(--fuente-display)", "'Source Serif 4'", "Georgia", "serif"],
        texto: ["var(--fuente-texto)", "Inter", "system-ui", "sans-serif"],
        cifra: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      // Siete pasos. Cualquier `text-[13.5px]` que vuelva a aparecer es un error
      // de revisión, no una necesidad: no hay hueco que no cubra esta escala.
      fontSize: {
        micro: ["12px", { lineHeight: "1.5" }],
        menor: ["13px", { lineHeight: "1.35" }],
        base: ["15px", { lineHeight: "1.5" }],
        guia: ["17px", { lineHeight: "1.5" }],
        h3: ["19px", { lineHeight: "1.25" }],
        h2: ["24px", { lineHeight: "1.25" }],
        h1: ["32px", { lineHeight: "1.25", letterSpacing: "-0.01em" }],
      },
      boxShadow: { carta: "0 1px 2px rgba(16,24,40,.06), 0 1px 3px rgba(16,24,40,.10)" },
    },
  },
  plugins: [],
} satisfies Config;

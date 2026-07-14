import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tinta: { DEFAULT: "#101828", suave: "#1D2939", borde: "#2E3A4E" },
        papel: { DEFAULT: "#F5F6F8", carta: "#FFFFFF" },
        primario: { DEFAULT: "#2E4B8F", hover: "#243C73", tenue: "#E8EDF7" },
        sem: {
          verde: "#15803D", verdebg: "#EAF6EF",
          amarillo: "#B45309", amarillobg: "#FDF3E3",
          naranja: "#C2410C", naranjabg: "#FCECE3",
          rojo: "#B91C1C", rojobg: "#FBEAEA",
        },
      },
      fontFamily: {
        display: ["Georgia", "Cambria", "Times New Roman", "serif"],
        cifra: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: { carta: "0 1px 2px rgba(16,24,40,.06), 0 1px 3px rgba(16,24,40,.10)" },
    },
  },
  plugins: [],
} satisfies Config;

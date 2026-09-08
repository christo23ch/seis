#!/usr/bin/env node
// Capturas del frontend para revisión visual. Procedimiento: docs/REVISION_VISUAL.md
//
//   node scripts/capturar.mjs antes|despues
//   SEIS_EMAIL=… SEIS_PASSWORD=… node scripts/capturar.mjs despues   ← incluye rutas privadas
//
// Requiere el frontend servido en BASE (por defecto http://localhost:3000) y COMPILADO:
// `npm run start` sirve lo que compiló `npm run build`, no el código fuente.

import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

// El Chromium del sandbox no siempre coincide con el que espera `playwright`. Si cambia
// la build, esta es la única línea que hay que tocar (ver docs/REVISION_VISUAL.md §3).
const EJECUTABLE = process.env.CHROMIUM_PATH
  ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const BASE = process.env.SEIS_BASE ?? "http://localhost:3000";

const ANCHURAS = [
  { nombre: "escritorio", width: 1440, height: 900 },
  { nombre: "movil", width: 390, height: 844 },
];

const PUBLICAS = ["/login", "/registro", "/recuperar", "/resetear", "/verificar"];
const PRIVADAS = ["/", "/inversiones", "/nueva", "/alertas", "/subastas",
                  "/comparativa", "/mapa", "/equipo", "/reglas", "/parametros"];

const etiqueta = process.argv[2];
if (!["antes", "despues"].includes(etiqueta)) {
  console.error("Uso: node scripts/capturar.mjs antes|despues");
  process.exit(1);
}

const destino = `capturas/${etiqueta}`;
await mkdir(destino, { recursive: true });

const navegador = await chromium.launch({ executablePath: EJECUTABLE });
const contexto = await navegador.newContext();

// Sesión: solo si hay credenciales. Sin ellas se capturan las públicas, que ya bastan
// para el grueso del trabajo de sistema de diseño.
let conSesion = false;
if (process.env.SEIS_EMAIL && process.env.SEIS_PASSWORD) {
  const p = await contexto.newPage();
  try {
    await p.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 20000 });
    await p.fill('input[type="email"]', process.env.SEIS_EMAIL);
    await p.fill('input[type="password"]', process.env.SEIS_PASSWORD);
    await p.click('button[type="submit"]');
    await p.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 15000 });
    conSesion = true;
    console.log("sesión iniciada: se capturan también las rutas privadas");
  } catch {
    console.log("no se pudo iniciar sesión (¿backend caído?): solo rutas públicas");
  } finally {
    await p.close();
  }
}

const rutas = conSesion ? [...PUBLICAS, ...PRIVADAS] : PUBLICAS;
let capturadas = 0;

for (const ruta of rutas) {
  for (const v of ANCHURAS) {
    const pagina = await contexto.newPage();
    await pagina.setViewportSize({ width: v.width, height: v.height });
    try {
      await pagina.goto(BASE + ruta, { waitUntil: "domcontentloaded", timeout: 20000 });
      // `networkidle` se cuelga si hay sondeos periódicos; una espera corta basta
      // para que entren fuentes y estilos.
      await pagina.waitForTimeout(700);
      const nombre = (ruta === "/" ? "inicio" : ruta.slice(1).replaceAll("/", "-"));
      await pagina.screenshot({ path: `${destino}/${nombre}--${v.nombre}.png`, fullPage: true });
      capturadas++;
    } catch (e) {
      console.log(`  fallo en ${ruta} (${v.nombre}): ${e.message.split("\n")[0]}`);
    } finally {
      await pagina.close();
    }
  }
}

await navegador.close();
console.log(`${capturadas} capturas en ${destino}/`);

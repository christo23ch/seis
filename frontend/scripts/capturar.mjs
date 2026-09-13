#!/usr/bin/env node
// Capturas del frontend para revisión visual. Procedimiento: docs/REVISION_VISUAL.md
//
//   node scripts/capturar.mjs antes|despues
//   SEIS_EMAIL=… SEIS_PASSWORD=… node scripts/capturar.mjs despues   ← incluye rutas privadas
//   SEIS_ENCAJE=1 node scripts/capturar.mjs despues                  ← recorta al viewport
//
// ═══ QUÉ PREGUNTA CONTESTA ESTE GUION, Y CUÁL NO ═══════════════════════════
//
// **Contesta:** ¿cómo queda el contenido, la composición, el color, la
// tipografía y el espaciado?
//
// **NO contesta:** ¿desborda la página en horizontal? Para eso está
// `npm run desborde`, y la distinción no es un matiz: `fullPage: true`
// **ensancha la imagen hasta el contenido**. Si la página mide 889 px en un
// móvil de 390, `fullPage` no da una captura de 390 px con la mitad cortada —
// da una de 889 px que **se ve perfectamente bien**. El desbordamiento
// horizontal es, por construcción, el defecto que `fullPage` vuelve invisible.
//
// Esto no es teoría: el armazón de la app privada estuvo sin maquetación móvil
// con las doce rutas desbordando, revisado fase tras fase con estas capturas,
// y ninguna lo mostró. Es el quinto caso del [[ADR-0014]] §6, y el peor: la
// herramienta de mirar construida de forma que ocultaba la clase entera de
// defecto que existía para detectar.
//
// `SEIS_ENCAJE=1` recorta al viewport en vez de ensanchar, así que el recorte se
// VE. Sigue sin ser la comprobación válida —una imagen no responde una pregunta
// numérica— pero al menos no miente.
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
// Con `SEIS_ENCAJE` la captura se recorta al viewport: el desbordamiento se ve
// cortado en vez de disimulado. Por defecto sigue siendo `fullPage`, porque para
// revisar CONTENIDO es lo correcto.
const ENCAJE = process.env.SEIS_ENCAJE === "1";

const ANCHURAS = [
  { nombre: "escritorio", width: 1440, height: 900 },
  { nombre: "movil", width: 390, height: 844 },
];

const PUBLICAS = ["/", "/ayuda", "/login", "/registro", "/recuperar", "/resetear", "/verificar"];
const PRIVADAS = ["/app", "/app/inversiones", "/app/nueva", "/app/alertas", "/app/subastas",
                  "/app/comparativa", "/app/mapa", "/app/equipo", "/app/reglas", "/app/parametros"];

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
    await p.waitForURL((u) => u.pathname.startsWith("/app"), { timeout: 15000 });
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
const desbordan = [];

for (const ruta of rutas) {
  for (const v of ANCHURAS) {
    const pagina = await contexto.newPage();
    await pagina.setViewportSize({ width: v.width, height: v.height });
    try {
      await pagina.goto(BASE + ruta, { waitUntil: "domcontentloaded", timeout: 20000 });
      // `networkidle` se cuelga si hay sondeos periódicos; una espera corta basta
      // para que entren fuentes y estilos.
      await pagina.waitForTimeout(700);
      const nombre = (ruta === "/" ? "landing" : ruta.slice(1).replaceAll("/", "-"));
      const sufijo = ENCAJE ? "--encaje" : "";
      await pagina.screenshot({ path: `${destino}/${nombre}--${v.nombre}${sufijo}.png`,
                                fullPage: !ENCAJE });
      // Aunque el objetivo sea el contenido, si la página desborda conviene decirlo
      // en voz alta: una captura `fullPage` no lo va a mostrar.
      const ancho = await pagina.evaluate(() => document.documentElement.scrollWidth);
      if (ancho > v.width + 1) {
        desbordan.push(`${ruta} (${v.nombre}): ${ancho} px en ${v.width}`);
      }
      capturadas++;
    } catch (e) {
      console.log(`  fallo en ${ruta} (${v.nombre}): ${e.message.split("\n")[0]}`);
    } finally {
      await pagina.close();
    }
  }
}

await navegador.close();
console.log(`${capturadas} capturas en ${destino}/${ENCAJE ? " (recortadas al viewport)" : ""}`);
if (desbordan.length) {
  console.log(`\n⚠️  ${desbordan.length} pantalla(s) DESBORDAN en horizontal, y estas capturas`);
  console.log("   no lo muestran si se tomaron con fullPage. Comprueba con `npm run desborde`:");
  for (const d of desbordan) console.log(`     · ${d}`);
}

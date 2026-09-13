#!/usr/bin/env node
// Comprueba que TODA ruta privada sigue exigiendo sesión, con un navegador real.
//
//   cd frontend && node scripts/guard-sesion.mjs
//
// Sale con código 1 si alguna ruta privada se deja ver sin sesión.
//
// POR QUÉ EXISTE. La Fase 15 movió la app de `/` a `/app` para dejar la raíz a la
// landing pública. Su propia ficha marca ese movimiento como «el cambio con más
// superficie de regresión de toda la fase», y con razón: el guard es un `useEffect`
// en el layout del grupo de rutas, así que **basta con que una ruta quede fuera del
// grupo para que se sirva sin sesión** — y se seguiría viendo bien.
//
// LO QUE NO CUBRE (ADR-0014):
//   · Comprueba el guard del NAVEGADOR, no la autorización del backend. Que una
//     pantalla redirija no prueba que su API rechace la petición; eso lo cubren los
//     tests de backend, que son los que de verdad protegen el dato.
//   · Solo las rutas listadas aquí. Una ruta nueva que nadie añada a esta lista no
//     se comprueba: la lista es el alcance, y hay que mantenerla.
//   · No prueba roles. Que un usuario sin permiso no pueda ENTRAR en /app/equipo es
//     otra cosa, y no se mira aquí.

import { chromium } from "playwright";

const EJECUTABLE = process.env.CHROMIUM_PATH
  ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const BASE = process.env.SEIS_BASE ?? "http://localhost:3000";

const PRIVADAS = ["/app", "/app/inversiones", "/app/nueva", "/app/alertas", "/app/subastas",
                  "/app/comparativa", "/app/mapa", "/app/equipo", "/app/reglas",
                  "/app/parametros", "/app/configuracion", "/app/administracion"];
// Contraprueba: si estas NO se vieran sin sesión, el guard estaría de más y esta
// comprobación pasaría por el motivo equivocado.
const PUBLICAS = ["/", "/ayuda", "/login", "/registro"];

const nav = await chromium.launch({ executablePath: EJECUTABLE });
// Contexto nuevo y sin almacenamiento: nada de sesión heredada.
const ctx = await nav.newContext();
const fallos = [];

for (const ruta of PRIVADAS) {
  const p = await ctx.newPage();
  try {
    await p.goto(BASE + ruta, { waitUntil: "domcontentloaded", timeout: 20000 });
    await p.waitForURL((u) => u.pathname.startsWith("/login"), { timeout: 8000 });
    console.log(`  ${ruta.padEnd(24)} → /login ✅`);
  } catch {
    const donde = new URL(p.url()).pathname;
    console.log(`  ${ruta.padEnd(24)} → ${donde} ❌ SE VE SIN SESIÓN`);
    fallos.push(ruta);
  }
  await p.close();
}

console.log("");
for (const ruta of PUBLICAS) {
  const p = await ctx.newPage();
  try {
    await p.goto(BASE + ruta, { waitUntil: "domcontentloaded", timeout: 20000 });
    await p.waitForTimeout(600);
    const donde = new URL(p.url()).pathname;
    if (donde.startsWith("/login") && ruta !== "/login") {
      console.log(`  ${ruta.padEnd(24)} → ${donde} ❌ una ruta PÚBLICA exige sesión`);
      fallos.push(ruta);
    } else {
      console.log(`  ${ruta.padEnd(24)} → ${donde} ✅ pública`);
    }
  } catch (e) {
    console.log(`  ${ruta.padEnd(24)} ❌ ${e.message.split("\n")[0]}`);
    fallos.push(ruta);
  }
  await p.close();
}

await nav.close();
console.log(`\n${PRIVADAS.length} privadas + ${PUBLICAS.length} públicas · ${fallos.length} fallos`);
if (fallos.length) process.exit(1);

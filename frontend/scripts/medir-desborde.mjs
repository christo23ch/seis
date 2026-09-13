#!/usr/bin/env node
// Comprueba que NINGUNA pantalla desborda en horizontal a 390 px, midiendo
// `scrollWidth` en el navegador en vez de mirar una captura.
//
//   cd frontend && node scripts/medir-desborde.mjs
//   SEIS_PASSWORD=… node scripts/medir-desborde.mjs     ← incluye las rutas privadas
//
// Sale con código 1 si alguna desborda, así que sirve de guarda en la CI.
//
// POR QUÉ EXISTE. El armazón de la app privada no tenía maquetación móvil —
// `aside.fixed.w-60` + `main.ml-60` sin un solo punto de ruptura— y **las doce
// rutas privadas desbordaban**: /inversiones medía 889 px de página en un móvil
// de 390. Nadie lo había visto porque las capturas de `capturar.mjs` se tomaban
// con `fullPage`, que ENSANCHA la imagen hasta el contenido y por tanto esconde
// justo el defecto que habría que ver. Una captura ancha parece correcta.
//
// LO QUE NO CUBRE (ADR-0014):
//   · Solo mide 390 px de ancho. Un desbordamiento que aparezca a 320 px o en
//     horizontal (844×390) no lo ve.
//   · Solo mide el estado INICIAL de cada ruta: no abre modales, no despliega
//     acordeones, no escribe en formularios. Un desbordamiento que aparezca al
//     interactuar pasa desapercibido.
//   · Necesita datos para que las tablas tengan filas. Contra una base vacía una
//     tabla ancha puede no desbordar y el verde no significaría nada.
//   · No dice si la pantalla es USABLE a 390 px, solo que no se sale. Un texto
//     ilegible o un botón de 20 px pasan esta comprobación.

import { chromium } from "playwright";
const EJ = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const BASE = process.env.SEIS_BASE ?? "http://localhost:3000";
const ANCHO = Number(process.env.SEIS_ANCHO ?? 390);
const PUBLICAS = ["/login", "/registro", "/recuperar", "/resetear", "/verificar"];
const PRIVADAS = ["/", "/inversiones", "/nueva", "/alertas", "/subastas",
                  "/comparativa", "/mapa", "/equipo", "/reglas", "/parametros",
                  "/configuracion", "/administracion"];

const nav = await chromium.launch({ executablePath: EJ });
const ctx = await nav.newContext({ viewport: { width: ANCHO, height: 844 } });

let conSesion = false;
{
  const p = await ctx.newPage();
  try {
    await p.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
    await p.fill('input[type="email"]', process.env.SEIS_EMAIL ?? "admin@seis.local");
    await p.fill('input[type="password"]', process.env.SEIS_PASSWORD ?? "admin");
    await p.click('button[type="submit"]');
    await p.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 15000 });
    conSesion = true;
  } catch (e) { console.log("sin sesión:", e.message.split("\n")[0]); }
  await p.close();
}
console.log(conSesion ? "sesión iniciada\n" : "solo públicas\n");

const filas = [];
for (const ruta of conSesion ? [...PUBLICAS, ...PRIVADAS] : PUBLICAS) {
  const p = await ctx.newPage();
  try {
    await p.goto(BASE + ruta, { waitUntil: "domcontentloaded", timeout: 20000 });
    await p.waitForTimeout(900);
    const m = await p.evaluate(() => {
      const d = document.documentElement;
      // Además del ancho total, quién lo provoca: el elemento más ancho que
      // se sale del viewport.
      let culpable = null, max = 0;
      for (const el of document.querySelectorAll("*")) {
        const r = el.getBoundingClientRect();
        if (r.right > window.innerWidth + 1 && r.width > max) {
          max = r.width;
          culpable = el.tagName.toLowerCase() + "." + String(el.className).slice(0, 45);
        }
      }
      return { ancho: d.scrollWidth, viewport: window.innerWidth, culpable, anchoCulpable: Math.round(max) };
    });
    filas.push({ ruta, ...m });
  } catch (e) {
    filas.push({ ruta, error: e.message.split("\n")[0] });
  }
  await p.close();
}
await nav.close();

const malas = filas.filter((f) => f.ancho > f.viewport + 1);
const erroneas = filas.filter((f) => f.error);
console.log(`${filas.length} rutas medidas · ${malas.length} desbordan a ${ANCHO} px\n`);
for (const f of filas) {
  if (f.error) { console.log(`  ${f.ruta.padEnd(16)} ERROR ${f.error}`); continue; }
  const mal = f.ancho > f.viewport + 1;
  console.log(`  ${f.ruta.padEnd(16)} ${String(f.ancho).padStart(5)} px ${mal ? "← DESBORDA" : ""}`);
  if (mal) console.log(`  ${"".padEnd(16)}   culpable: ${f.culpable} (${f.anchoCulpable} px)`);
}

// Sin sesión solo se miden cinco rutas públicas: un verde ahí NO dice nada de la
// app privada, que es donde estaba el problema. Se avisa en vez de callar.
if (!conSesion) {
  console.log("\n⚠️  solo se han medido las rutas públicas: sin sesión esta comprobación no cubre la app");
}
if (erroneas.length) {
  console.log(`\n⚠️  ${erroneas.length} ruta(s) no se pudieron medir: el verde no las incluye`);
}
if (malas.length || erroneas.length) process.exit(1);

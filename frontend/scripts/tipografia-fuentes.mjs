#!/usr/bin/env node
// Descarga las tipografías candidatas de la Fase 0' y arma un `fuentes.css` local.
// Se ejecuta UNA vez antes de `scripts/tipografia.mjs`.
//
// POR QUÉ SE DESCARGAN EN VEZ DE ENLAZAR EL CDN DE GOOGLE: servir tipografías desde
// `fonts.gstatic.com` manda la IP del visitante a un tercero fuera de la UE. Sea cual
// sea la opción que se elija en §2, en producción irá auto-alojada, así que el
// muestrario se hace ya en esas condiciones y no en otras más cómodas.
//
// ALCANCE DECLARADO (ADR-0014): descarga **solo el subconjunto latino**. Es suficiente
// para un producto en español, y NO cubre cirílico, griego ni vietnamita. Si algún día
// el producto se traduce, esto se queda corto en silencio — que es justo el modo de
// fallo que el proyecto persigue, así que queda escrito aquí.

import { mkdir, writeFile, readdir, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";

const DESTINO = process.env.SEIS_FUENTES ?? "/tmp/seis-tipografia";
// Google devuelve woff2 solo a navegadores modernos; con el UA de Node devuelve ttf.
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
  + "(KHTML, like Gecko) Chrome/120 Safari/537.36";

const FAMILIAS = {
  sourceserif: "Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700",
  inter:       "Inter:wght@400;500;600;700",
  intertight:  "Inter+Tight:wght@500;600;700",
  plexsans:    "IBM+Plex+Sans:wght@400;500;600;700",
  plexserif:   "IBM+Plex+Serif:wght@400;600;700",
  plexmono:    "IBM+Plex+Mono:wght@400;500;600",
  jetmono:     "JetBrains+Mono:wght@400;500;700",
  newsreader:  "Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700",
  publicsans:  "Public+Sans:wght@400;500;600;700",
};

await mkdir(join(DESTINO, "fuentes"), { recursive: true });
const bloques = [];

for (const [nombre, query] of Object.entries(FAMILIAS)) {
  const css = await (await fetch(
    `https://fonts.googleapis.com/css2?family=${query}&display=swap`,
    { headers: { "User-Agent": UA } })).text();

  let ficheros = 0;
  for (const bloque of css.split(/(?=\/\* )/).filter((b) => b.trim())) {
    if (!/^\/\* latin(-ext)? \*\//.test(bloque)) continue;   // ver alcance declarado
    let b = bloque;
    for (const url of bloque.match(/https:\/\/fonts\.gstatic\.com\/\S+?\.woff2/g) ?? []) {
      const h = createHash("md5").update(url).digest("hex").slice(0, 8);
      const rel = `fuentes/${nombre}-${h}.woff2`;
      if (!existsSync(join(DESTINO, rel))) {
        const r = await fetch(url, { headers: { "User-Agent": UA } });
        await writeFile(join(DESTINO, rel), Buffer.from(await r.arrayBuffer()));
      }
      b = b.replaceAll(url, rel);
      ficheros++;
    }
    bloques.push(b);
  }
  console.log(`${nombre}: ${ficheros} caras`);
}

await writeFile(join(DESTINO, "fuentes.css"), bloques.join("\n"));
const nombres = await readdir(join(DESTINO, "fuentes"));
let bytes = 0;
for (const n of nombres) bytes += (await stat(join(DESTINO, "fuentes", n))).size;
console.log(`${nombres.length} ficheros woff2 · ${Math.round(bytes / 1024)} kB en ${DESTINO}`);

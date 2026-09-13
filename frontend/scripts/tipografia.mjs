#!/usr/bin/env node
// Genera el muestrario tipográfico de la Fase 0' y lo captura con Playwright.
// Procedimiento y criterio: docs/DESIGN_SYSTEM.md §2.
//
//   node scripts/tipografia-fuentes.mjs   ← una vez: descarga los .woff2 y arma fuentes.css
//   node scripts/tipografia.mjs           ← genera el HTML y lo captura
//
// POR QUÉ ES UN MUESTRARIO Y NO UNA ELECCIÓN: la decisión tipográfica la toma el
// responsable del producto mirando, no el modelo argumentando. Este script existe
// para que haya algo que mirar.
//
// LO QUE EL MUESTRARIO **NO** DEMUESTRA, y conviene tenerlo delante al decidir:
//   · Es una pantalla, no el producto: no dice nada de cómo envejecen las cuatro
//     opciones en veinte pantallas ni en el PDF del informe.
//   · Todas las opciones comparten LA MISMA escala, los mismos colores y el mismo
//     espaciado, a propósito: así la comparación es de letra, no de maquetación.
//     Eso significa que una opción puede mejorar mucho con una escala ajustada a
//     ella —las serifas suelen pedir un cuerpo algo mayor— y aquí no se ve.
//   · Las capturas salen de Chromium en Linux. El renderizado en macOS y en
//     Windows NO es idéntico, sobre todo en los pesos finos.
//   · No mide legibilidad: ningún test sustituye a leer la tabla densa con los
//     ojos del que la va a usar.

import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const EJECUTABLE = process.env.CHROMIUM_PATH
  ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const FUENTES = process.env.SEIS_FUENTES ?? "/tmp/seis-tipografia";
const DESTINO = process.env.SEIS_DESTINO ?? "capturas/tipografia";

// ── Las cuatro opciones ────────────────────────────────────────────────────
// Todas son de licencia libre (SIL OFL / Apache) y auto-alojables: ninguna
// obliga a servir desde un CDN de terceros, que en la UE es además un problema
// de RGPD (la IP del visitante viaja a Google).
const OPCIONES = [
  {
    id: "A", nombre: "Editorial técnica",
    display: "'Source Serif 4', Georgia, serif",
    texto: "'Inter', system-ui, sans-serif",
    cifra: "'IBM Plex Mono', ui-monospace, monospace",
    pie: "Source Serif 4 · Inter · IBM Plex Mono",
  },
  {
    id: "B", nombre: "Superfamilia de ingeniería",
    display: "'IBM Plex Serif', Georgia, serif",
    texto: "'IBM Plex Sans', system-ui, sans-serif",
    cifra: "'IBM Plex Mono', ui-monospace, monospace",
    pie: "IBM Plex Serif · IBM Plex Sans · IBM Plex Mono",
  },
  {
    id: "C", nombre: "Neutra suiza",
    display: "'Inter Tight', system-ui, sans-serif",
    texto: "'Inter', system-ui, sans-serif",
    cifra: "'JetBrains Mono', ui-monospace, monospace",
    pie: "Inter Tight · Inter · JetBrains Mono",
  },
  {
    id: "D", nombre: "Carácter editorial",
    display: "'Newsreader', Georgia, serif",
    texto: "'Public Sans', system-ui, sans-serif",
    cifra: "'IBM Plex Mono', ui-monospace, monospace",
    pie: "Newsreader · Public Sans · IBM Plex Mono",
  },
];

// ── Contenido: números REALES del caso dorado §19, no cifras inventadas ────
const CASO = {
  ref: "SEIS-2026-0184", sitio: "Ciudad Ejemplo (Ejemplo)",
  tipo: "Vivienda · 82 m² · 1975 · estado malo · ocupada en precario",
  semaforo: "AMARILLO", ico: 64, ra: 40, ici: 63, icu: 66,
  vm: 135378.72, vs: 188026, rvc: 1.077, padj: 63840, ms: 0.248,
  escalera: [
    ["P_ideal", 51317, "Entrada excelente; margen por encima del objetivo"],
    ["P_objetivo", 60011, "Precio de trabajo: el que se carga en la interfaz"],
    ["P_máximo", 68731, "Último precio con margen mínimo aceptable"],
    ["P_límite", 80022, "Infranqueable por software (§9.1)"],
  ],
  escenarios: [
    ["Pesimista", "25 %", 160837.44, 151559.46, 9277.98, "6,1 %", "4,0 %", "18,2 m"],
    ["Base", "55 %", 176744.44, 141395.76, 35348.68, "25,0 %", "22,9 %", "13,0 m"],
    ["Optimista", "20 %", 186995.62, 133995.70, 52999.92, "39,6 %", "43,6 %", "11,0 m"],
  ],
  condiciones: [
    "Judicial: depósito del 5 % y pago del remate en plazo legal sin condición suspensiva; cesión de remate solo por el ejecutante (§3.2)",
    "Solicitar certificado de deuda de la comunidad antes de la puja (deuda estimada al alza mientras tanto, P5)",
    "Verificar la situación posesoria in situ antes de pujar; dotar provisión de desalojo P80",
  ],
  riesgos: [["jurídico", 6, "medio"], ["documental", 6, "medio"], ["ocupación", 12, "alto"],
            ["urbanístico", 4, "bajo"], ["técnico", 9, "medio"], ["financiero", 2, "bajo"],
            ["comercial", 6, "medio"], ["liquidez", 4, "bajo"], ["mercado", 6, "medio"]],
};

const eur = (n) => n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
const eur0 = (n) => n.toLocaleString("es-ES", { maximumFractionDigits: 0 }) + " €";

// Escala compartida por las cuatro opciones, a propósito (ver cabecera).
const ESCALA = `
  --t-micro: 12px; --t-menor: 13px; --t-base: 15px; --t-guia: 17px;
  --t-h3: 19px; --t-h2: 24px; --t-h1: 32px;
  --lh-apretado: 1.25; --lh-normal: 1.5; --lh-tabla: 1.35;
`;

function fragmento(o) {
  return `
<section class="opcion" style="--display:${o.display}; --texto:${o.texto}; --cifra:${o.cifra}">
  <div class="etiqueta"><b>Opción ${o.id} · ${o.nombre}</b><span>${o.pie}</span></div>
  <article class="carta">
    <nav class="miga">Inversiones › ${CASO.ref}</nav>
    <h1>Vivienda en ${CASO.sitio}</h1>
    <p class="guia">${CASO.tipo}</p>

    <div class="veredicto">
      <span class="sem">${CASO.semaforo}</span>
      ${[["ICO", CASO.ico], ["RA", CASO.ra], ["ICI", CASO.ici], ["ICU", CASO.icu]]
        .map(([k, v]) => `<span class="indice"><i>${k}</i><b>${v}</b></span>`).join("")}
      <span class="indice"><i>Margen de seguridad</i><b>${(CASO.ms * 100).toFixed(1).replace(".", ",")} %</b></span>
    </div>

    <h2>Escalera de precios</h2>
    <table class="densa">
      <thead><tr><th>Peldaño</th><th class="n">Importe</th><th>Qué significa</th></tr></thead>
      <tbody>${CASO.escalera.map(([k, v, d]) =>
        `<tr><td class="clave">${k}</td><td class="n">${eur0(v)}</td><td class="nota">${d}</td></tr>`).join("")}
      </tbody>
    </table>

    <h2>Escenarios</h2>
    <table class="densa">
      <thead><tr><th>Escenario</th><th class="n">Prob.</th><th class="n">VS</th><th class="n">Coste total</th>
      <th class="n">Beneficio</th><th class="n">ROI</th><th class="n">ROI a.</th><th class="n">Plazo</th></tr></thead>
      <tbody>${CASO.escenarios.map(([n, p, vs, c, b, roi, roia, pl]) =>
        `<tr><td class="clave">${n}</td><td class="n">${p}</td><td class="n">${eur(vs)}</td>
         <td class="n">${eur(c)}</td><td class="n">${eur(b)}</td><td class="n">${roi}</td>
         <td class="n">${roia}</td><td class="n">${pl}</td></tr>`).join("")}
      </tbody>
    </table>

    <h2>Riesgos</h2>
    <div class="riesgos">${CASO.riesgos.map(([d, s, n]) =>
      `<span class="chip n-${n}">${d} <b>${s}</b></span>`).join("")}</div>

    <h2>Condiciones de la puja</h2>
    <ul class="condiciones">${CASO.condiciones.map((c) => `<li>${c}</li>`).join("")}</ul>
    <p class="letrapequena">RVC ${String(CASO.rvc).replace(".", ",")} · adjudicación esperada
      ${eur0(CASO.padj)} · VM ${eur(CASO.vm)} · VS ${eur0(CASO.vs)}. Base imponible del impuesto
      calculada sobre la puja, como suelo: no consta valor de referencia del Catastro.</p>
  </article>
</section>`;
}

const HTML = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>SEIS · muestrario tipográfico (Fase 0')</title>
<link rel="stylesheet" href="fuentes.css">
<style>
  :root { ${ESCALA}
    --tinta:#101828; --tinta-suave:#1D2939; --borde:#E4E7EC; --papel:#F5F6F8;
    --carta:#FFFFFF; --primario:#2E4B8F; --suave:#667085;
    --am:#B45309; --ambg:#FDF3E3; --verde:#15803D; --rojo:#B91C1C; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--papel); color:var(--tinta);
         font-family:'Inter',system-ui,sans-serif; }
  .rejilla { display:grid; grid-template-columns:repeat(2,1fr); gap:20px; padding:20px; }
  @media (max-width:900px){ .rejilla{ grid-template-columns:1fr; } }
  .opcion { font-family:var(--texto); }
  .etiqueta { display:flex; justify-content:space-between; align-items:baseline;
              font-size:var(--t-micro); color:var(--suave); padding:0 2px 8px;
              font-family:'Inter',system-ui,sans-serif; letter-spacing:.02em; }
  .etiqueta b { color:var(--tinta); font-size:var(--t-menor); }
  .carta { background:var(--carta); border:1px solid var(--borde); border-radius:8px;
           padding:20px 22px 22px; box-shadow:0 1px 3px rgba(16,24,40,.08); }
  .miga { font-size:var(--t-micro); color:var(--suave); margin-bottom:10px; }
  h1 { font-family:var(--display); font-size:var(--t-h1); line-height:var(--lh-apretado);
       margin:0 0 4px; font-weight:600; letter-spacing:-.01em; }
  h2 { font-family:var(--display); font-size:var(--t-h3); line-height:var(--lh-apretado);
       margin:22px 0 8px; font-weight:600; }
  .guia { font-size:var(--t-guia); line-height:var(--lh-normal); color:var(--tinta-suave); margin:0 0 14px; }
  .veredicto { display:flex; align-items:center; gap:14px; flex-wrap:wrap;
               border-top:1px solid var(--borde); border-bottom:1px solid var(--borde); padding:12px 0; }
  .sem { background:var(--ambg); color:var(--am); font-weight:700; font-size:var(--t-menor);
         letter-spacing:.06em; padding:5px 9px; border-radius:4px; }
  .indice { display:flex; flex-direction:column; gap:1px; }
  .indice i { font-style:normal; font-size:var(--t-micro); color:var(--suave); }
  .indice b { font-family:var(--cifra); font-size:var(--t-guia); font-weight:600;
              font-variant-numeric:tabular-nums; }
  table.densa { width:100%; border-collapse:collapse; font-size:var(--t-menor);
                line-height:var(--lh-tabla); }
  .densa th { text-align:left; font-weight:600; font-size:var(--t-micro); color:var(--suave);
              border-bottom:1px solid var(--borde); padding:6px 8px 6px 0; white-space:nowrap; }
  .densa td { border-bottom:1px solid #F2F4F7; padding:6px 8px 6px 0; vertical-align:top; }
  .densa .n { text-align:right; font-family:var(--cifra); font-variant-numeric:tabular-nums;
              white-space:nowrap; padding-left:14px; padding-right:14px; }
  .densa th:last-child, .densa td:last-child { padding-right:0; }
  .densa .clave { font-weight:600; white-space:nowrap; }
  .densa .nota { color:var(--suave); font-size:var(--t-micro); }
  .riesgos { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { font-size:var(--t-micro); border:1px solid var(--borde); border-radius:99px;
          padding:3px 9px; color:var(--tinta-suave); }
  .chip b { font-family:var(--cifra); font-variant-numeric:tabular-nums; margin-left:3px; }
  .chip.n-alto { border-color:#F3C0C0; color:var(--rojo); background:#FBEAEA; }
  .chip.n-medio { border-color:#F0D9AE; color:var(--am); background:var(--ambg); }
  .condiciones { margin:0; padding-left:18px; font-size:var(--t-menor);
                 line-height:var(--lh-normal); color:var(--tinta-suave); }
  .condiciones li { margin-bottom:4px; }
  .letrapequena { font-size:var(--t-micro); line-height:var(--lh-normal); color:var(--suave);
                  margin:14px 0 0; padding-top:10px; border-top:1px solid var(--borde); }
</style></head><body>
<div class="rejilla">${OPCIONES.map(fragmento).join("")}</div>
</body></html>`;

await mkdir(DESTINO, { recursive: true });
await writeFile(`${FUENTES}/muestrario.html`, HTML);

const navegador = await chromium.launch({ executablePath: EJECUTABLE });
const contexto = await navegador.newContext({ deviceScaleFactor: 2 });

// 1 · Las cuatro juntas, que es como se comparan de un vistazo.
{
  const p = await contexto.newPage();
  await p.setViewportSize({ width: 1440, height: 1000 });
  await p.goto(`file://${FUENTES}/muestrario.html`, { waitUntil: "load" });
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(400);
  await p.screenshot({ path: `${DESTINO}/comparativa.png`, fullPage: true });
  await p.close();
}

// 2 · Cada una a solas, en escritorio y en móvil. El móvil no es un extra: la
// tabla densa de escenarios es donde una tipografía se rompe, y se rompe a 390 px.
const soloUna = (id) => {
  document.querySelectorAll(".opcion").forEach((s) => {
    if (!s.querySelector(".etiqueta b").textContent.includes(`Opción ${id} `)) s.remove();
  });
  document.querySelector(".rejilla").style.gridTemplateColumns = "1fr";
};
for (const o of OPCIONES) {
  for (const v of [{ n: "", w: 820 }, { n: "-movil", w: 390 }]) {
    const p = await contexto.newPage();
    await p.setViewportSize({ width: v.w, height: 1000 });
    await p.goto(`file://${FUENTES}/muestrario.html`, { waitUntil: "load" });
    await p.evaluate(() => document.fonts.ready);
    await p.evaluate(soloUna, o.id);
    await p.waitForTimeout(300);
    // En móvil se captura SIN fullPage a propósito: `fullPage` ensancha la imagen
    // hasta el contenido y esconde justamente lo que hay que ver —que la tabla
    // densa no cabe—. Se mide el desbordamiento y se dice en voz alta.
    const movil = v.n === "-movil";
    if (movil) {
      const ancho = await p.evaluate(() => document.documentElement.scrollWidth);
      if (ancho > v.w) console.log(`  ${o.id}: la página mide ${ancho} px en un móvil de ${v.w} px`);
    }
    await p.screenshot({ path: `${DESTINO}/opcion-${o.id}${v.n}.png`, fullPage: !movil });
    await p.close();
  }
}

await navegador.close();
console.log(`capturas en ${DESTINO}/ (comparativa + opcion-A…D, escritorio y móvil)`);

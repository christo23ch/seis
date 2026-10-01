/**
 * Simulaciones e informes oficiales de punta a punta: navegador real → frontend →
 * backend → base de datos (Fase 5F.7.9).
 *
 * Existe por la misma razón que `alta-real.mjs`: la UI de 5F.7.4-5F.7.8 y la API de
 * 5F.6-5F.7.3 se probaron cada una contra su propia idea del contrato. Esto recorre
 * el flujo entero donde se rompe si no encajan:
 *   análisis → simulación (editor) → comparación → validar → informe oficial →
 *   volver a la original → otro informe → el primero no ha cambiado → PDF → lector.
 *
 * Uso:  bash e2e/correr_simulaciones.sh   (levanta backend y frontend propios,
 *       ejecuta esto y comprueba la base con `e2e/comprobar_simulaciones.py`).
 *
 * LO QUE NO CUBRE (ADR-0014):
 *   · Errores: ni 409 (transiciones, configuración inconsistente) ni 422 (overrides
 *     mal formados). Los cubren los tests del backend y las pruebas de cada subfase.
 *   · Concurrencia: dos usuarios a la vez, o validar y descartar en paralelo.
 *   · Navegadores distintos de Chromium, ni tamaños distintos de 390 y 1440 px.
 *   · Parámetros de tipo estructura: el editor no los edita (solo lectura).
 *   · Que el PDF sea legible o contenga el texto: solo que es un PDF no vacío con
 *     el nombre esperado. El contenido lo prueba la suite (`test_informe_api`).
 */
import { chromium } from "playwright";
import { readFile, stat, writeFile } from "node:fs/promises";

const FRONTEND = process.env.E2E_FRONTEND ?? "http://localhost:3010";
const BACKEND = process.env.E2E_BACKEND ?? "http://localhost:8010/api/v1";
const DIR = process.env.E2E_DIR ?? ".";
const EJECUTABLE = process.env.PLAYWRIGHT_CHROMIUM ?? process.env.CHROMIUM_PATH
  ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const ADMIN = { email: process.env.E2E_ADMIN_EMAIL ?? "admin@seis.local",
                password: process.env.E2E_ADMIN_PASSWORD ?? "admin-de-e2e" };
const LECTOR = { email: `lector-e2e-${Date.now()}@ejemplo.com`, password: "LectorE2e-5F79" };
const PARAMETRO = "capital.coste_capital_anual";

const fallos = [];
function comprobar(condicion, descripcion) {
  if (condicion) console.log(`  ✓ ${descripcion}`);
  else { console.log(`  ✗ ${descripcion}`); fallos.push(descripcion); }
}
const id8 = (s) => s.slice(0, 8);
const plano = (s) => s.replace(/\s+/g, " ").trim();

// ─────────────────────────── API (solo preparación y lector) ───────────────────────────

async function token(email, password) {
  const r = await fetch(`${BACKEND}/auth/login`, { method: "POST", body: new URLSearchParams({ username: email, password }) });
  if (!r.ok) throw new Error(`login ${email}: HTTP ${r.status}`);
  return (await r.json()).access_token;
}
async function api(tok, metodo, ruta, cuerpo) {
  const r = await fetch(`${BACKEND}${ruta}`, { method: metodo,
    headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
  if (!r.ok) throw new Error(`${metodo} ${ruta}: HTTP ${r.status} ${await r.text()}`);
  return r.json();
}

// ─────────────────────────── navegador ───────────────────────────

const navegador = await chromium.launch({ executablePath: EJECUTABLE });
const incidencias = [];
async function sesion(cred, ancho) {
  const ctx = await navegador.newContext({ viewport: { width: ancho, height: ancho > 500 ? 900 : 844 }, acceptDownloads: true });
  const p = await ctx.newPage();
  // Diagnóstico permanente, como en alta-real: sin la consola ni la red, un fallo
  // futuro se depura a ciegas.
  p.on("console", (m) => { if (m.type() === "error") incidencias.push(`consola: ${m.text()}`); });
  // Con la URL: «Failed to load resource: 404» a secas no dice qué recurso.
  p.on("response", (r) => { if (r.status() >= 400) incidencias.push(`respuesta ${r.status()}: ${r.url()}`); });
  await p.goto(`${FRONTEND}/login`);
  await p.fill('input[type="email"]', cred.email);
  await p.fill('input[type="password"]', cred.password);
  await p.click('button[type="submit"]');
  await p.waitForURL((u) => u.pathname.startsWith("/app"), { timeout: 20000 });
  return p;
}
const pestana = async (p, nombre) => {
  await p.getByRole("button", { name: nombre, exact: true }).click();
  await p.waitForTimeout(400);
};
const aviso = async (p) => plano(await p.locator('section[aria-label="Configuración mostrada"]').innerText());
const fila = (p, id) => p.locator(`[data-fila="${id}"]:visible`);
const panelCmp = (p) => p.locator('section[aria-label="Comparación con el original"]');
const detalleInf = (p) => p.locator('section[aria-label="Informe oficial"]');
const desborde = (p) => p.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
async function esperarTextoEn(p, selector, texto) {
  await p.waitForFunction(({ s, t }) => [...document.querySelectorAll(s)].some((e) => e.offsetParent && e.innerText.includes(t)),
    { s: selector, t: texto }, { timeout: 15000 });
}
async function emitir(p) {
  await p.getByRole("button", { name: "Emitir informe oficial" }).click();
  const dlg = p.locator("dialog[open]");
  await dlg.waitFor();
  const texto = plano(await dlg.innerText());
  const [r] = await Promise.all([
    p.waitForResponse((x) => x.request().method() === "POST" && /\/informes$/.test(new URL(x.url()).pathname)),
    dlg.getByRole("button", { name: "Emitir" }).click(),
  ]);
  await detalleInf(p).locator("[data-markdown]").waitFor({ timeout: 15000 });
  return { texto, status: r.status(), informe: await r.json() };
}

const ids = {};
let pagina;
try {
  const tAdmin = await token(ADMIN.email, ADMIN.password);
  const entrada = JSON.parse(await readFile(process.env.E2E_ENTRADA, "utf8"));
  entrada.activo.municipio = "E2E simulaciones";
  ids.analisis = (await api(tAdmin, "POST", "/analisis", entrada)).id;
  await api(tAdmin, "POST", "/organizacion/miembros", { email: LECTOR.email, password: LECTOR.password, nombre: "Lector e2e", rol: "lector" });
  console.log(`\nSimulaciones e informes de punta a punta · análisis ${id8(ids.analisis)}\n`);

  const p = pagina = await sesion(ADMIN, 1440);
  // 1. Detalle con la configuración original.
  await p.goto(`${FRONTEND}/app/inversiones/${ids.analisis}`, { waitUntil: "networkidle" });
  comprobar((await aviso(p)).includes("Configuración original del análisis"), "1. el aviso dice «Configuración original»");

  // 2. Nueva simulación con coma decimal.
  await pestana(p, "Simulaciones");
  await p.getByRole("button", { name: "Nueva simulación" }).click();
  const campo = p.locator(`[data-parametro="${PARAMETRO}"] input`);
  if (!(await campo.isVisible())) {
    await p.locator('section[aria-label="Nueva simulación"] details[data-grupo]',
      { has: p.locator(`[data-parametro="${PARAMETRO}"]`) }).locator(":scope > summary").click();
  }
  await campo.fill("0,12");
  const [rCrear] = await Promise.all([
    p.waitForResponse((x) => x.request().method() === "POST" && /\/simulaciones$/.test(new URL(x.url()).pathname)),
    p.getByRole("button", { name: /^Crear simulación/ }).click(),
  ]);
  comprobar(rCrear.status() === 201, `2. POST /simulaciones → ${rCrear.status()}`);
  comprobar(rCrear.request().postData() === JSON.stringify({ overrides: { [PARAMETRO]: 0.12 } }),
    `2. se envía el número convertido: ${rCrear.request().postData()}`);
  ids.simulacion = (await rCrear.json()).id;
  await esperarTextoEn(p, `[data-fila="${ids.simulacion}"]`, "pendiente");
  comprobar(true, "2. la nueva fila aparece «pendiente»");
  comprobar((await aviso(p)).includes("Configuración original"), "2. el aviso no cambia al crear");

  // 3. Comparar con el original.
  await fila(p, ids.simulacion).getByRole("button", { name: "Comparar con original" }).click();
  await panelCmp(p).locator(`[data-comparacion="${PARAMETRO}"]`).waitFor({ timeout: 15000 });
  comprobar(plano(await panelCmp(p).locator(`[data-comparacion="${PARAMETRO}"]`).innerText()).includes("Cambio pedido en esta simulación"),
    "3. la comparación marca el parámetro como «Cambio pedido en esta simulación»");

  // 4. Validar con confirmación → «En uso» en la lista y en el aviso.
  await fila(p, ids.simulacion).getByRole("button", { name: "Validar" }).click();
  const dlg = p.locator("dialog[open]");
  await dlg.waitFor();
  comprobar(plano(await dlg.innerText()).includes("configuración en uso"), "4. la validación pide confirmación");
  await dlg.getByRole("button", { name: "Validar" }).click();
  await esperarTextoEn(p, `[data-fila="${ids.simulacion}"]`, "En uso");
  comprobar(true, "4. la simulación queda «En uso» en la lista");
  comprobar((await aviso(p)).includes(`Mostrando la simulación ${id8(ids.simulacion)}`), "4. el aviso muestra la simulación");

  // 5. Informe oficial desde la simulación.
  await pestana(p, "Informes oficiales");
  const e1 = await emitir(p);
  comprobar(e1.status === 201, `5. POST /informes → ${e1.status}`);
  comprobar(e1.texto.includes(`de la simulación ${id8(ids.simulacion)}`), "5. la confirmación nombra la simulación");
  ids.informe1 = e1.informe.id;
  const proc1 = plano(await detalleInf(p).locator("[data-procedencia]").innerText());
  comprobar(proc1.includes(`Simulación ${id8(ids.simulacion)}`), `5. procedencia «${proc1}»`);
  const md1 = await detalleInf(p).locator("[data-markdown]").innerText();

  // 6. Volver a la original y emitir otro.
  await p.getByRole("button", { name: "Volver a la configuración original" }).click();
  await p.waitForFunction(() => document.querySelector('section[aria-label="Configuración mostrada"]')?.innerText.includes("original del análisis"), null, { timeout: 15000 });
  const e2 = await emitir(p);
  comprobar(e2.texto.includes("original del análisis"), "6. la confirmación dice «original del análisis»");
  ids.informe2 = e2.informe.id;
  comprobar(plano(await detalleInf(p).locator("[data-procedencia]").innerText()) === "Original", "6. procedencia «Original»");

  // 7. El primer informe no ha cambiado.
  await p.locator(`[data-informe="${ids.informe1}"]:visible`).getByRole("button", { name: "Abrir" }).click();
  await p.waitForFunction((id) => document.querySelector('section[aria-label="Informe oficial"] h3')?.innerText.includes(id), id8(ids.informe1), { timeout: 15000 });
  await detalleInf(p).locator("[data-markdown]").waitFor();
  const md1b = await detalleInf(p).locator("[data-markdown]").innerText();
  comprobar(md1b === md1, `7. el Markdown del primer informe es idéntico (${md1b.length} = ${md1.length} caracteres)`);
  comprobar(plano(await detalleInf(p).locator("[data-procedencia]").innerText()) === proc1, "7. y su procedencia también");

  // 8. PDF oficial.
  const [descarga] = await Promise.all([
    p.waitForEvent("download", { timeout: 20000 }),
    detalleInf(p).getByRole("button", { name: "Descargar PDF oficial" }).click(),
  ]);
  const nombre = descarga.suggestedFilename();
  const destino = `${DIR}/${nombre}`;
  await descarga.saveAs(destino);
  const bytes = await readFile(destino);
  const esperado = `SEIS_informe_oficial_${id8(ids.informe1)}_${e1.informe.generado_en.slice(0, 10)}.pdf`;
  comprobar(nombre === esperado, `8. nombre del PDF: ${nombre}`);
  comprobar(bytes.subarray(0, 4).toString() === "%PDF", "8. empieza por %PDF");
  comprobar((await stat(destino)).size > 0, `8. tamaño ${(await stat(destino)).size} bytes`);
  await p.context().close();

  // 9. Lector: ve todo y no puede escribir.
  const l = pagina = await sesion(LECTOR, 1440);
  await l.goto(`${FRONTEND}/app/inversiones/${ids.analisis}`, { waitUntil: "networkidle" });
  await pestana(l, "Simulaciones");
  comprobar(await fila(l, ids.simulacion).isVisible(), "9. el lector ve la lista de simulaciones");
  comprobar((await l.getByRole("button", { name: /Nueva simulación|Validar|Descartar|Usar esta configuración|Volver a la/ }).count()) === 0,
    "9. el lector no ve ningún botón de escritura en la pestaña ni en el aviso");
  await fila(l, ids.simulacion).getByRole("button", { name: "Comparar con original" }).click();
  await panelCmp(l).locator(`[data-comparacion="${PARAMETRO}"]`).waitFor({ timeout: 15000 });
  comprobar(true, "9. el lector abre la comparación");
  await pestana(l, "Informes oficiales");
  comprobar((await l.getByRole("button", { name: "Emitir informe oficial" }).count()) === 0, "9. el lector no ve «Emitir informe oficial»");
  comprobar((await l.locator("[data-informe]:visible").count()) === 2, "9. el lector ve los 2 informes");
  await l.context().close();

  // 10. Sin desbordamiento horizontal, pestaña a pestaña y con los paneles abiertos.
  for (const ancho of [390, 1440]) {
    const v = pagina = await sesion(ADMIN, ancho);
    await v.goto(`${FRONTEND}/app/inversiones/${ids.analisis}`, { waitUntil: "networkidle" });
    const nombres = await v.locator("button.border-b-2").allInnerTexts();
    const malas = [];
    for (const n of nombres) {
      await pestana(v, n.trim());
      const [sw, iw] = await desborde(v);
      if (sw !== iw) malas.push(`${n.trim()} (${sw}/${iw})`);
    }
    await pestana(v, "Simulaciones");
    await v.getByRole("button", { name: "Nueva simulación" }).click();
    await v.locator('section[aria-label="Nueva simulación"]').waitFor();
    let [sw, iw] = await desborde(v); if (sw !== iw) malas.push(`editor (${sw}/${iw})`);
    await v.getByRole("button", { name: "Cerrar", exact: true }).first().click();
    await fila(v, ids.simulacion).getByRole("button", { name: "Comparar con original" }).click();
    await panelCmp(v).locator(`[data-comparacion="${PARAMETRO}"]`).waitFor();
    [sw, iw] = await desborde(v); if (sw !== iw) malas.push(`comparación (${sw}/${iw})`);
    await pestana(v, "Informes oficiales");
    await v.locator(`[data-informe="${ids.informe1}"]:visible`).getByRole("button", { name: "Abrir" }).click();
    await detalleInf(v).locator("[data-markdown]").waitFor();
    [sw, iw] = await desborde(v); if (sw !== iw) malas.push(`informe (${sw}/${iw})`);
    await v.screenshot({ path: `${DIR}/informe-${ancho}.png`, fullPage: true });
    comprobar(malas.length === 0, `10. a ${ancho} px, ${nombres.length} pestañas + editor + comparación + informe sin desbordar${malas.length ? `: ${malas.join(", ")}` : ""}`);
    await v.context().close();
  }
} catch (e) {
  console.log(`  ✗ excepción: ${e.message.split("\n")[0]}`);
  fallos.push(e.message);
  if (pagina) await pagina.screenshot({ path: `${DIR}/e2e-simulaciones-fallo.png`, fullPage: true }).catch(() => {});
} finally {
  if (incidencias.length) {
    console.log("\n  Incidencias del navegador:");
    for (const i of incidencias) console.log(`    · ${i}`);
  }
  await navegador.close();
}

// Los ids van a un fichero para que `comprobar_simulaciones.py` verifique la base
// DESECHABLE directamente, sin un endpoint de apoyo que no debería existir.
await writeFile(process.env.E2E_IDS ?? `${DIR}/ids.json`, JSON.stringify(ids));
console.log(fallos.length ? `\nFALLOS EN EL NAVEGADOR: ${fallos.length}\n` : "\nNavegador: todo correcto.\n");
process.exit(fallos.length ? 1 : 0);

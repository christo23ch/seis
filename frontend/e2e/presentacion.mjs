/**
 * Fase 5K — presentación de punta a punta: recorre las pantallas cambiadas con un
 * navegador real, en escritorio (1440 px) y en móvil (390 px).
 *
 * Comprueba:
 *   · A: la vista previa y el informe oficial pintan el Markdown (títulos, tablas, casillas)
 *     sin «**» ni «|---|» en crudo, y sus tablas no desbordan la página a 390 px.
 *   · B: «Datos de entrada» y «Árbol completo vigente» sin JSON crudo ni Textarea, con
 *     nombres, unidades y valores en español; «Ver JSON» sigue disponible; el editor libre
 *     muestra el valor vigente de la clave escrita.
 *   · C: el informe sin símbolos con barra baja (desde la 5J-2a los redacta el motor) y las
 *     fórmulas de «Ver cálculo» con subíndice.
 *   · D: «Ver cálculo» con fórmula, sustitución y resultado del motor, y «Cálculo no
 *     disponible aún» donde falta el dato.
 *   · E: el desglose del ICO toma sus pesos del catálogo («/ 25» en rentabilidad).
 *   · Accesibilidad básica: un solo h1, títulos del informe desde h2, tablas enfocables.
 *
 * Con E2E_CAPTURAS=<directorio> guarda capturas de cada pantalla en los dos anchos.
 * Uso: lo ejecuta `e2e/correr_simulaciones.sh` (necesita su E2E_ENTRADA, el caso §19).
 *
 * LO QUE NO CUBRE (ADR-0014): contraste de color medido (se revisó a mano con los tokens
 * de la app), lectores de pantalla reales, otros navegadores distintos de Chromium.
 */
import { chromium } from "playwright";
import { readFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { rutaNavegador } from "../scripts/navegador.mjs";

const FRONTEND = process.env.E2E_FRONTEND ?? "http://localhost:3010";
const BACKEND = process.env.E2E_BACKEND ?? "http://localhost:8010/api/v1";
const ADMIN = { email: process.env.E2E_ADMIN_EMAIL ?? "admin@seis.local", password: process.env.E2E_ADMIN_PASSWORD ?? "admin-de-e2e" };
const CAPTURAS = process.env.E2E_CAPTURAS;
const MONO_ANCHA = '.cifra, .font-cifra { font-family: "DejaVu Sans Mono", "Courier New", monospace !important; }';

const fallos = [];
function comprobar(condicion, descripcion) {
  if (condicion) console.log(`  ✓ ${descripcion}`);
  else { console.log(`  ✗ ${descripcion}`); fallos.push(descripcion); }
}
const plano = (s) => s.replace(/\s+/g, " ").trim();

async function api(tok, metodo, ruta, cuerpo) {
  const r = await fetch(`${BACKEND}${ruta}`, { method: metodo,
    headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
  if (!r.ok) throw new Error(`${metodo} ${ruta}: HTTP ${r.status} ${await r.text()}`);
  return r.json();
}

const navegador = await chromium.launch({ executablePath: rutaNavegador() });
const incidencias = [];

async function sesion(ancho) {
  const ctx = await navegador.newContext({ viewport: { width: ancho, height: ancho > 500 ? 900 : 844 } });
  await ctx.addInitScript((css) => {
    document.addEventListener("DOMContentLoaded", () => {
      const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
    });
  }, MONO_ANCHA);
  const p = await ctx.newPage();
  p.on("console", (m) => { if (m.type() === "error" && !m.text().includes("favicon")) incidencias.push(`consola: ${m.text()}`); });
  p.on("response", async (r) => { if (r.status() >= 500) incidencias.push(`${r.status()}: ${r.url()}`); });
  await p.goto(`${FRONTEND}/login`);
  await p.fill('input[type="email"]', ADMIN.email);
  await p.fill('input[type="password"]', ADMIN.password);
  await p.click('button[type="submit"]');
  await p.waitForURL((u) => u.pathname.startsWith("/app"), { timeout: 20000 });
  return p;
}
const pestana = async (p, nombre) => { await p.getByRole("button", { name: nombre, exact: true }).click(); };
const sinDesborde = (p) => p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
async function captura(p, nombre) {
  if (!CAPTURAS) return;
  await mkdir(CAPTURAS, { recursive: true });
  await p.screenshot({ path: join(CAPTURAS, `${nombre}.png`), fullPage: true });
}

try {
  const tok = (await (await fetch(`${BACKEND}/auth/login`, { method: "POST",
    body: new URLSearchParams({ username: ADMIN.email, password: ADMIN.password }) })).json()).access_token;
  const entrada = JSON.parse(await readFile(process.env.E2E_ENTRADA, "utf8"));
  const { id } = await api(tok, "POST", "/analisis", entrada);
  const informe = await api(tok, "POST", `/analisis/${id}/informes`);
  console.log(`\nPresentación (5K) · análisis ${id.slice(0, 8)}\n`);

  for (const ancho of [1440, 390]) {
    const p = await sesion(ancho);
    const sufijo = ancho === 390 ? "390" : "escritorio";
    console.log(`  — ${ancho} px —`);
    await p.goto(`${FRONTEND}/app/inversiones/${id}`, { waitUntil: "networkidle" });

    // E · pesos del ICO del catálogo (valor original del análisis: 25 en rentabilidad).
    const ico = p.locator('[data-componente-ico="rentabilidad"]');
    await ico.waitFor({ timeout: 10000 });
    await p.waitForFunction(() => document.querySelector('[data-componente-ico="rentabilidad"]')?.innerText.includes("/ 25"),
      null, { timeout: 10000 }).catch(() => {});
    comprobar(plano(await ico.innerText()).includes("/ 25"), `E · rentabilidad del ICO con su peso del catálogo (${plano(await ico.innerText())})`);

    // D · «Ver cálculo» en Costes y en la escalera.
    const verCostes = p.locator("[data-ver-calculo]", { has: p.locator('[data-calculo="cf_p50"]') });
    await verCostes.locator("summary").click();
    const cf = plano(await p.locator('[data-calculo="cf_p50"]').innerText());
    comprobar(cf.includes("suma de las partidas") && cf.includes("78.144"), `D · C_F P50: fórmula y resultado del motor («${cf.slice(0, 70)}…»)`);
    // 5J-2b (ADR-0026): el plazo suma la inmovilización entre el cierre y la posesión.
    const plazo = plano(await p.locator('[data-calculo="plazo"]').innerText());
    comprobar(plazo.includes("inmovilización") && plazo.includes("P50 = 7 + 3 + 3 + 2,5") && plazo.includes("15,5 × 1,4"),
      `D · plazo con la inmovilización sustituida (5J-2b) («${plazo.slice(0, 90)}…»)`);
    const verEscalera = p.locator("[data-ver-calculo]", { has: p.locator('[data-calculo="p_max"]') });
    await verEscalera.locator("summary").click();
    comprobar(plano(await p.locator('[data-calculo="p_max"]').innerText()).includes("68.533"), "D · P_max con sus dos candidatos sustituidos");
    // 5J-2a: el motor emite el margen excepcional: P_ideal ya tiene su cálculo.
    comprobar(await p.locator('[data-calculo="p_ideal"] [data-no-disponible]').count() === 0
              && plano(await p.locator('[data-calculo="p_ideal"]').innerText()).includes("0,3375"),
      "D · P_ideal con su margen excepcional sustituido (5J-2a)");
    comprobar(await p.locator('[data-calculo="p_max"] var').count() > 0, "C · las fórmulas de «Ver cálculo» con subíndice");
    const verMetricas = p.locator("[data-ver-calculo]", { has: p.locator('[data-calculo="tir"]') });
    await verMetricas.locator("summary").click();
    comprobar(plano(await p.locator('[data-calculo="tir"]').innerText()).includes("Mes 0 (compra)")
              && await p.locator('[data-calculo="colchon"] [data-no-disponible]').count() === 0,
      "D · TIR con sus flujos mensuales y colchón con sus operandos (5J-2a)");
    comprobar(await sinDesborde(p), "el resumen con los cálculos abiertos no desborda");
    await captura(p, `resumen-ver-calculo-${sufijo}`);

    // A + C · vista previa.
    await pestana(p, "Vista previa (no oficial)");
    const md = p.locator("[data-markdown]");
    await md.waitFor({ timeout: 10000 });
    const texto = await md.innerText();
    comprobar(!texto.includes("**") && !/\|\s*-{3,}/.test(texto), "A · la vista previa no muestra «**» ni «|---|»");
    comprobar(await md.locator("h2").first().innerText() === "Informe de análisis SEIS", "A · el título del informe es un h2");
    comprobar(await md.locator("table").count() >= 5, `A · tablas maquetadas (${await md.locator("table").count()})`);
    comprobar(await md.locator('[role="img"][aria-label="Pendiente"]').count() > 0, "A · los bloqueantes del checklist como casillas");
    // 5J-2a: el motor redacta los nombres; el informe ya no trae símbolos con barra baja.
    // `innerText` respeta el `uppercase` de las cabeceras de tabla: se compara sin mayúsculas.
    comprobar(texto.toLowerCase().includes("partida de costes fijos (p50)"),
      "C · el informe nombra los costes fijos en vez de «C_F» (5J-2a)");
    const conBarra = texto.match(/[^\W_]+_[^\W_]+/gu) ?? [];
    comprobar(conBarra.length === 0, `C · el informe sin identificadores con barra baja (${conBarra.join(", ") || "ninguno"})`);
    comprobar(!/judicial_boe|ocupacion_desalojo|una_alta/.test(texto), "C · sin claves internas con barra baja");
    comprobar(await p.locator("h1").count() === 1, "accesibilidad · un solo h1 en la página");
    comprobar(await md.locator('[role="region"][tabindex="0"]').count() >= 5, "accesibilidad · las tablas son regiones enfocables");
    comprobar(await sinDesborde(p), `A · la vista previa no desborda a ${ancho} px`);
    await captura(p, `vista-previa-${sufijo}`);

    // A · informe oficial (Markdown congelado), mismo componente.
    await pestana(p, "Informes oficiales");
    await p.locator(`[data-informe="${informe.id}"]:visible`).getByRole("button", { name: "Abrir" }).click();
    const oficial = p.locator('section[aria-label="Informe oficial"] [data-markdown]');
    await oficial.waitFor({ timeout: 15000 });
    comprobar(!(await oficial.innerText()).includes("**"), "A · el informe oficial tampoco muestra Markdown en crudo");
    comprobar(await sinDesborde(p), `A · el informe oficial no desborda a ${ancho} px`);

    // B · datos de entrada.
    await pestana(p, "Datos de entrada");
    await p.locator("details", { hasText: "Datos generales" }).first().waitFor({ timeout: 10000 });
    const datos = plano(await p.locator("main").innerText());
    comprobar(!datos.includes('"valor_subasta"'), "B · Datos de entrada sin JSON crudo");
    comprobar(/Valor de subasta 152\.000 €/.test(datos), "B · «Valor de subasta 152.000 €»");
    comprobar(/Depósito 5 %/.test(datos), "B · el depósito en porcentaje (0,05 → 5 %)");
    await p.getByRole("button", { name: "Ver JSON" }).click();
    comprobar((await p.locator("[data-json]").innerText()).includes('"valor_subasta"'), "B · «Ver JSON» muestra la entrada en JSON");
    await p.getByRole("button", { name: "Ver presentación" }).click();
    comprobar(await sinDesborde(p), `B · Datos de entrada no desborda a ${ancho} px`);
    await captura(p, `datos-entrada-${sufijo}`);

    // B · Parámetros (T3).
    await p.goto(`${FRONTEND}/app/parametros`, { waitUntil: "networkidle" });
    const arbol = p.locator(".rounded-lg", { hasText: "Árbol completo vigente" }).last();
    await arbol.waitFor({ timeout: 10000 });
    comprobar(await arbol.locator("textarea").count() === 0, "B · el árbol vigente ya no usa Textarea");
    const proc = arbol.locator("details", { hasText: /^\s*Procedimiento/ }).first();
    await proc.locator("summary").click();
    comprobar(plano(await proc.innerText()).includes("20 %") && plano(await proc.innerText()).includes("LEC, art. 669"),
      "B · los datos legales del procedimiento, con su valor y artículo");
    await arbol.getByRole("button", { name: "Ver JSON" }).click();
    comprobar(await arbol.locator("[data-json]").count() === 1, "B · el árbol tiene «Ver JSON»");
    await arbol.getByRole("button", { name: "Ver presentación" }).click();
    const clave = p.getByPlaceholder("reforma.baremos_m2.media");
    if (await clave.count()) {
      await clave.fill("tenencia.mensual_defecto");
      comprobar(await p.getByText("Valor vigente: 240").count() === 1, "B · el editor libre muestra el valor vigente de la clave");
    } else comprobar(false, "B · el editor libre está disponible para el administrador");
    comprobar(await sinDesborde(p), `B · Parámetros no desborda a ${ancho} px`);
    await captura(p, `parametros-${sufijo}`);
    await p.context().close();
  }
} catch (e) {
  console.log(`  ✗ excepción: ${e.message}`);
  fallos.push(e.message);
} finally {
  if (incidencias.length) {
    console.log("\n  Incidencias del navegador:");
    for (const i of incidencias) console.log(`    · ${i.slice(0, 400)}`);
  }
  await navegador.close();
}

console.log(fallos.length ? `\nFALLOS EN LA PRESENTACIÓN: ${fallos.length}\n` : "\nPresentación: todo correcto.\n");
process.exit(fallos.length ? 1 : 0);

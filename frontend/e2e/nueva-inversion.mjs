/**
 * Alta de una inversión de punta a punta con SOLO los campos obligatorios (Fase 5I):
 * navegador real → asistente de 11 pasos → /analisis/simular → guardar → detalle.
 *
 * Existe por la prueba manual que abrió la fase: al calcular con los opcionales
 * vacíos, el backend respondía 422 («activo.anio_construccion: Input should be a
 * valid integer, unable to parse string…»). El formulario enviaba `""` en cada
 * campo numérico vacío, porque construía el cuerpo con `getValues()` —el texto
 * crudo de los campos— en vez de con los valores ya validados. Ninguna prueba lo
 * veía: la suite del backend y la e2e de simulaciones crean el análisis por la
 * API, con un JSON correcto, y nunca pasaban por el formulario.
 *
 * Comprueba además:
 *   · Coma decimal y punto de miles («82,5», «152.000», «2.293»).
 *   · La antigüedad de un comparable no baja de 0 con la flecha ↓ (punto 3 de la
 *     prueba manual: con `type="number"` sin mínimo, ↓ o la rueda daban −1, −2…).
 *   · El depósito como importe (5I-C): equivalente visible y guardado como % más
 *     el importe escrito.
 *   · Coordenadas desde la provincia (5I-E): relleno, marca de aproximada y que no
 *     pisa una escrita a mano.
 *
 * Uso: lo ejecuta `e2e/correr_simulaciones.sh`, con su backend y su frontend propios.
 *
 * LO QUE NO CUBRE (ADR-0014):
 *   · Los opcionales rellenados: aquí se dejan vacíos a propósito. Su conversión la
 *     prueban `tests/schema.test.ts` y `tests/formulario.test.ts`.
 *   · Otros perfiles distintos del inicial (flip integral) ni la hipoteca.
 *   · Solo Chromium y 1440 px de ancho.
 */
import { chromium } from "playwright";
import { rutaNavegador } from "../scripts/navegador.mjs";

const FRONTEND = process.env.E2E_FRONTEND ?? "http://localhost:3010";
const BACKEND = process.env.E2E_BACKEND ?? "http://localhost:8010/api/v1";
const EJECUTABLE = rutaNavegador();
const ADMIN = { email: process.env.E2E_ADMIN_EMAIL ?? "admin@seis.local",
                password: process.env.E2E_ADMIN_PASSWORD ?? "admin-de-e2e" };
const MUNICIPIO = `E2E alta mínima ${Date.now()}`;

const fallos = [];
function comprobar(condicion, descripcion) {
  if (condicion) console.log(`  ✓ ${descripcion}`);
  else { console.log(`  ✗ ${descripcion}`); fallos.push(descripcion); }
}
const campo = (p, nombre) => p.locator(`[name="${nombre}"]`);

const navegador = await chromium.launch({ executablePath: EJECUTABLE });
const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } });
const incidencias = [];
const respuestasSimular = [];
pagina.on("console", (m) => { if (m.type() === "error") incidencias.push(`consola: ${m.text()}`); });
pagina.on("response", async (r) => {
  if (r.url().includes("/analisis/simular")) respuestasSimular.push(r.status());
  if (r.status() >= 400) incidencias.push(`respuesta ${r.status()}: ${r.url()} ${await r.text().catch(() => "")}`);
});

async function siguiente() {
  await pagina.getByRole("button", { name: "Siguiente" }).click();
}

try {
  console.log(`\nAlta de inversión con solo los obligatorios (${MUNICIPIO})\n`);
  await pagina.goto(`${FRONTEND}/login`);
  await pagina.fill('input[type="email"]', ADMIN.email);
  await pagina.fill('input[type="password"]', ADMIN.password);
  await pagina.click('button[type="submit"]');
  await pagina.waitForURL((u) => u.pathname.startsWith("/app"), { timeout: 20000 });
  await pagina.goto(`${FRONTEND}/app/nueva`, { waitUntil: "networkidle" });

  // 1 · Datos generales: el valor de subasta, con punto de miles, y (5I-C) el
  // depósito como importe, que el formulario muestra en su equivalente en %.
  await campo(pagina, "subasta.valor_subasta").fill("152.000");
  await campo(pagina, "subasta.deposito_modo").selectOption("importe");
  await campo(pagina, "subasta.deposito_importe").fill("7.600");
  const equivalente = pagina.getByText("7.600 € = 5 % del valor de subasta");
  await equivalente.waitFor({ timeout: 5000 }).catch(() => {});
  comprobar(await equivalente.count() === 1, "el depósito en euros muestra su equivalente: «7.600 € = 5 %»");
  await siguiente();
  // 2 · Tipo de activo: solo la superficie, con coma decimal.
  await campo(pagina, "activo.superficie_m2").fill("82,5");
  await siguiente();
  // 3 · Registrales y 4 · Urbanísticos: nada.
  await siguiente();
  await siguiente();
  // 5 · Ubicación: el municipio y (5I-E) la provincia, que rellena lat/lng con la
  // capital y las marca como aproximadas; una escrita a mano no se pisa.
  await campo(pagina, "activo.municipio").fill(MUNICIPIO);
  await campo(pagina, "activo.provincia").selectOption("Madrid");
  await campo(pagina, "activo.lat").fill("40,5");
  await campo(pagina, "activo.lng").fill("");
  await campo(pagina, "activo.provincia").selectOption("Teruel");
  comprobar(await campo(pagina, "activo.lat").inputValue() === "40,5",
    "elegir provincia no pisa una latitud escrita a mano");
  await campo(pagina, "activo.lat").fill("");
  await campo(pagina, "activo.provincia").selectOption("Madrid");
  await campo(pagina, "activo.provincia").selectOption("Teruel");
  comprobar(await campo(pagina, "activo.lat").inputValue() === "40,3416"
            && await campo(pagina, "activo.lng").inputValue() === "-1,1048",
    `con lat/lng vacías se rellenan con la capital (Teruel: ${await campo(pagina, "activo.lat").inputValue()}, `
    + `${await campo(pagina, "activo.lng").inputValue()})`);
  comprobar(await pagina.getByText("Latitud — aproximada (provincia)").count() === 1,
    "la coordenada se marca «aproximada (provincia)»");
  // Quitar la provincia quita su aproximada (no se queda como si fuera exacta).
  await campo(pagina, "activo.provincia").selectOption("");
  comprobar(await campo(pagina, "activo.lat").inputValue() === "" && await campo(pagina, "activo.lng").inputValue() === "",
    "al volver a «Seleccione…» se quitan las coordenadas aproximadas");
  await campo(pagina, "activo.provincia").selectOption("Teruel");
  await siguiente();
  // 6 · Valoraciones: el €/m² del comparable que trae el asistente.
  await campo(pagina, "comparables.0.precio_m2").fill("2.293");
  const antiguedad = campo(pagina, "comparables.0.meses_antiguedad");
  // La causa del negativo era el control: `type="number"` sin mínimo (flechas y
  // rueda). Se comprueba el control y, además, el efecto de la flecha ↓.
  comprobar(await antiguedad.getAttribute("type") === "text"
            && await antiguedad.getAttribute("inputmode") === "decimal",
    "la antigüedad es un campo de texto con teclado decimal, sin flechas ni rueda");
  await antiguedad.focus();
  await pagina.keyboard.press("ArrowDown");
  await pagina.keyboard.press("ArrowDown");
  const valorAntiguedad = await antiguedad.inputValue();
  comprobar(!valorAntiguedad.startsWith("-"),
    `la flecha ↓ no vuelve negativa la antigüedad del comparable (vale «${valorAntiguedad}»)`);
  await siguiente();
  // 7 · Costes, 8 · Reforma, 9 · Financiación: nada.
  await siguiente();
  await siguiente();
  await siguiente();
  // 10 · Validación → calcular.
  await pagina.getByRole("button", { name: "Calcular decisión" }).click();
  await pagina.getByRole("button", { name: "Guardar análisis" }).waitFor({ timeout: 30000 });

  comprobar(respuestasSimular.length > 0 && respuestasSimular.every((s) => s === 200),
    `el cálculo responde 200 (respuestas de /simular: ${respuestasSimular.join(", ") || "ninguna"})`);
  const textoResultado = await pagina.locator("main").innerText();
  comprobar(/Precio objetivo|Escalera de precios/i.test(textoResultado), "se muestra el resultado del motor");
  comprobar(!/unable to parse|Input should be/i.test(textoResultado), "no aparece ningún mensaje en bruto de Pydantic");

  await pagina.getByRole("button", { name: "Guardar análisis" }).click();
  await pagina.waitForURL((u) => /\/app\/inversiones\/[0-9a-f-]{36}/.test(u.pathname), { timeout: 20000 });
  const id = new URL(pagina.url()).pathname.split("/").pop();
  // `hasText` compara el contenido, no `innerText`: el <h1> lleva `capitalize`, y
  // `innerText` devolvería «Alta Mínima» en vez de lo escrito.
  const titulo = pagina.locator("h1", { hasText: MUNICIPIO });
  await titulo.waitFor({ timeout: 15000 }).catch(() => {});
  comprobar(await titulo.count() === 1, "el detalle guardado muestra el municipio");

  // El análisis existe de verdad, con lo que se escribió convertido a número.
  const tok = (await (await fetch(`${BACKEND}/auth/login`, { method: "POST",
    body: new URLSearchParams({ username: ADMIN.email, password: ADMIN.password }) })).json()).access_token;
  const r = await fetch(`${BACKEND}/analisis/${id}`, { headers: { Authorization: `Bearer ${tok}` } });
  const det = await r.json();
  comprobar(r.status === 200, `el análisis ${id.slice(0, 8)} está guardado`);
  comprobar(det.entrada?.activo?.superficie_m2 === 82.5,
    `superficie guardada como 82,5 (es ${det.entrada?.activo?.superficie_m2})`);
  comprobar(det.entrada?.subasta?.valor_subasta === 152000,
    `valor de subasta guardado como 152.000 (es ${det.entrada?.subasta?.valor_subasta})`);
  comprobar(det.entrada?.activo?.lat === 40.3416 && det.entrada?.activo?.lng === -1.1048
            && det.entrada?.activo?.provincia === "Teruel",
    `la coordenada aproximada se guarda como número (${det.entrada?.activo?.lat}, ${det.entrada?.activo?.lng})`);
  // 5I-D (ADR-0020): sin tocar el estado de conservación, el alta va con «No consta».
  comprobar(det.entrada?.activo?.estado_conservacion === "desconocido",
    `el estado de conservación sin tocar se guarda como «No consta» (es ${det.entrada?.activo?.estado_conservacion})`);
  comprobar(Math.abs((det.entrada?.subasta?.deposito_pct ?? 0) - 0.05) < 1e-12
            && det.entrada?.subasta?.deposito_importe === 7600,
    `depósito guardado como 5 % con el importe escrito (pct ${det.entrada?.subasta?.deposito_pct}, `
    + `importe ${det.entrada?.subasta?.deposito_importe})`);
} catch (e) {
  console.log(`  ✗ excepción: ${e.message}`);
  fallos.push(e.message);
  const visible = await pagina.locator("body").innerText().catch(() => "");
  if (visible) console.log(`\n  Texto en pantalla:\n${visible.split("\n").slice(0, 60).map((l) => `    | ${l}`).join("\n")}`);
} finally {
  if (incidencias.length) {
    console.log("\n  Incidencias del navegador:");
    for (const i of incidencias) console.log(`    · ${i.slice(0, 600)}`);
  }
  await navegador.close();
}

console.log(fallos.length ? `\nFALLOS EN EL ALTA DE INVERSIÓN: ${fallos.length}\n` : "\nAlta de inversión: todo correcto.\n");
process.exit(fallos.length ? 1 : 0);

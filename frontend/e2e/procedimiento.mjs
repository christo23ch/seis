/**
 * Fase 5J-1 (ADR-0022) — datos del procedimiento de punta a punta: navegador real →
 * preguntas del alta → /analisis/simular → panel del resultado → guardar → detalle
 * y base de datos.
 *
 * Comprueba:
 *   · Valores por defecto visibles: procedimiento preseleccionado con el de la fuente,
 *     «No sé» y vivienda habitual «No consta».
 *   · El procedimiento sigue a la fuente mientras no se toque a mano, y el régimen solo
 *     aparece en la vía judicial.
 *   · Validación guiada en español de la cantidad reclamada.
 *   · El panel «Procedimiento y umbrales legales» con las cifras del régimen anterior a
 *     la LO 1/2025 (depósito del 5 %, 40 días, aprobación por cubrir la deuda) y el aviso
 *     orientativo, en el asistente y en la pestaña «Estrategia de puja».
 *   · Lo respondido llega a la entrada guardada y al resultado.
 *
 * Uso: lo ejecuta `e2e/correr_simulaciones.sh`, con su backend y su frontend propios.
 *
 * LO QUE NO CUBRE (ADR-0014): el resto de procedimientos (sus cifras las fijan
 * `backend/tests/test_procedimiento_5j1.py`), el informe en PDF ni anchos de móvil.
 */
import { chromium } from "playwright";
import { rutaNavegador } from "../scripts/navegador.mjs";

const FRONTEND = process.env.E2E_FRONTEND ?? "http://localhost:3010";
const BACKEND = process.env.E2E_BACKEND ?? "http://localhost:8010/api/v1";
const EJECUTABLE = rutaNavegador();
const ADMIN = { email: process.env.E2E_ADMIN_EMAIL ?? "admin@seis.local",
                password: process.env.E2E_ADMIN_PASSWORD ?? "admin-de-e2e" };
const MUNICIPIO = `E2E procedimiento ${Date.now()}`;

const fallos = [];
function comprobar(condicion, descripcion) {
  if (condicion) console.log(`  ✓ ${descripcion}`);
  else { console.log(`  ✗ ${descripcion}`); fallos.push(descripcion); }
}
const campo = (p, nombre) => p.locator(`[name="${nombre}"]`);
/** Texto de una fila del panel, sin espacios duros (el € de Intl lleva uno). */
const fila = async (p, clave) =>
  (await p.locator(`[data-procedimiento] [data-fila="${clave}"]`).innerText()).replace(/\s+/g, " ");

const navegador = await chromium.launch({ executablePath: EJECUTABLE });
const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } });
const incidencias = [];
pagina.on("console", (m) => { if (m.type() === "error") incidencias.push(`consola: ${m.text()}`); });
pagina.on("response", async (r) => {
  if (r.status() >= 400) incidencias.push(`respuesta ${r.status()}: ${r.url()} ${await r.text().catch(() => "")}`);
});
const siguiente = () => pagina.getByRole("button", { name: "Siguiente" }).click();

try {
  console.log(`\nDatos del procedimiento de punta a punta (${MUNICIPIO})\n`);
  await pagina.goto(`${FRONTEND}/login`);
  await pagina.fill('input[type="email"]', ADMIN.email);
  await pagina.fill('input[type="password"]', ADMIN.password);
  await pagina.click('button[type="submit"]');
  await pagina.waitForURL((u) => u.pathname.startsWith("/app"), { timeout: 20000 });
  await pagina.goto(`${FRONTEND}/app/nueva`, { waitUntil: "networkidle" });

  // 1 · Datos generales: valores por defecto visibles.
  comprobar(await campo(pagina, "subasta.procedimiento").inputValue() === "judicial",
    "el procedimiento parte del de la fuente inicial: judicial");
  comprobar(await campo(pagina, "subasta.regimen_judicial").inputValue() === "no_se",
    "el régimen judicial parte de «No sé»");

  // El procedimiento sigue a la fuente, y el régimen solo existe en la vía judicial.
  await campo(pagina, "subasta.fuente").selectOption("aeat");
  await pagina.waitForFunction(() =>
    document.querySelector('[name="subasta.procedimiento"]')?.value === "aeat", null, { timeout: 5000 }).catch(() => {});
  comprobar(await campo(pagina, "subasta.procedimiento").inputValue() === "aeat",
    "al elegir la fuente AEAT, el procedimiento pasa a AEAT");
  comprobar(await campo(pagina, "subasta.regimen_judicial").count() === 0,
    "fuera de la vía judicial no se pregunta el régimen");
  await campo(pagina, "subasta.fuente").selectOption("judicial_boe");
  await pagina.waitForFunction(() =>
    document.querySelector('[name="subasta.procedimiento"]')?.value === "judicial", null, { timeout: 5000 }).catch(() => {});
  comprobar(await campo(pagina, "subasta.procedimiento").inputValue() === "judicial",
    "al volver a la fuente judicial, el procedimiento vuelve a judicial");
  // Una elección hecha a mano no se pisa al cambiar la fuente.
  await campo(pagina, "subasta.procedimiento").selectOption("notarial");
  await campo(pagina, "subasta.fuente").selectOption("tgss");
  await pagina.waitForTimeout(300);   // margen para un efecto que NO debe ocurrir
  comprobar(await campo(pagina, "subasta.procedimiento").inputValue() === "notarial",
    "un procedimiento elegido a mano no cambia al cambiar la fuente");
  await campo(pagina, "subasta.fuente").selectOption("judicial_boe");
  await campo(pagina, "subasta.procedimiento").selectOption("judicial");

  await campo(pagina, "subasta.valor_subasta").fill("152.000");
  await campo(pagina, "subasta.regimen_judicial").selectOption("anterior");
  // Validación guiada: una cantidad que no es un número se marca en español.
  await campo(pagina, "subasta.cantidad_reclamada").fill("mucho");
  await siguiente();
  const error = pagina.getByText("Introduzca un número");
  await error.first().waitFor({ timeout: 5000 }).catch(() => {});
  comprobar(await error.count() >= 1, "una cantidad reclamada no numérica se marca «Introduzca un número»");
  await campo(pagina, "subasta.cantidad_reclamada").fill("30.000");
  // 5J-4 (ADR-0028): la ayuda explica que informar la deuda puede bajar la mínima aprobable.
  comprobar(await pagina.getByText("Informarla puede bajar la puja mínima aprobable").count() === 1,
    "la ayuda de la cantidad reclamada explica que puede bajar la puja mínima aprobable");
  await siguiente();

  // 2 · Tipo de activo: vivienda habitual «No consta» de partida; se responde «No».
  comprobar(await campo(pagina, "activo.vivienda_habitual_ejecutado").inputValue() === "no_consta",
    "la vivienda habitual del ejecutado parte de «No consta»");
  await campo(pagina, "activo.superficie_m2").fill("82");
  await campo(pagina, "activo.vivienda_habitual_ejecutado").selectOption("no");
  await siguiente();
  await siguiente();                                      // 3 · Registrales
  await siguiente();                                      // 4 · Urbanísticos
  await campo(pagina, "activo.municipio").fill(MUNICIPIO); // 5 · Ubicación
  await siguiente();
  await campo(pagina, "comparables.0.precio_m2").fill("2.293"); // 6 · Valoraciones
  await siguiente();
  await siguiente();                                      // 7 · Costes
  await siguiente();                                      // 8 · Reforma
  await siguiente();                                      // 9 · Financiación
  await pagina.getByRole("button", { name: "Calcular decisión" }).click();
  await pagina.getByRole("button", { name: "Guardar análisis" }).waitFor({ timeout: 30000 });

  // Panel del resultado del asistente: régimen anterior, deuda informada, no vivienda habitual.
  const panel = pagina.locator("[data-procedimiento]");
  comprobar(await panel.count() === 1, "el resultado muestra el panel «Procedimiento y umbrales legales»");
  comprobar((await fila(pagina, "deposito")).includes("7.600 €") && (await fila(pagina, "deposito")).includes("5 % del valor de subasta"),
    `depósito exigido del régimen anterior: 7.600 € (${await fila(pagina, "deposito")})`);
  comprobar((await fila(pagina, "plazo")).includes("40 días naturales"), `pago del resto en 40 días (${await fila(pagina, "plazo")})`);
  // 5J-2b (ADR-0026): los meses que se suman al plazo de la operación, con su origen.
  comprobar((await fila(pagina, "inmovilizacion")).includes("2,5 meses") && (await fila(pagina, "inmovilizacion")).includes("Plazo legal máximo"),
    `inmovilización del régimen anterior: 2,5 meses, plazo legal máximo (${await fila(pagina, "inmovilizacion")})`);
  comprobar((await fila(pagina, "minima")).includes("30.000 €"),
    `con la deuda informada, la puja mínima aprobable es la deuda (${await fila(pagina, "minima")})`);
  comprobar((await fila(pagina, "suelo")).includes("No consta"), "sin vivienda habitual no hay suelo absoluto");
  comprobar(await pagina.locator("[data-aviso-orientativo]").innerText().then((t) => t.startsWith("Cálculo orientativo")),
    "se muestra el aviso de cálculo orientativo");
  // 5J-3 (ADR-0027): con la deuda informada (30.000 €, 40 %) la puja máxima supera la mínima
  // aprobable y no la segura (70 %): franja «sujeta a mejora», sin techo.
  const aviso = pagina.locator('[data-aviso-aprobacion="sujeta_a_mejora"]');
  comprobar(await aviso.count() === 1 && (await aviso.innerText()).includes("Aprobación del remate sujeta a mejora")
            && (await aviso.innerText()).includes("No limita el semáforo"),
    "el panel destaca el aviso de la franja «sujeta a mejora» (5J-3)");
  // 5J-4 (ADR-0028): la mínima aprobable (30.000 €) queda por debajo del objetivo: veredicto viable,
  // con las tres cifras y la puja recomendada.
  const veredicto = pagina.locator('[data-veredicto="viable"]');
  const cifra = async (c) => (await veredicto.locator(`[data-cifra="${c}"]`).innerText()).replace(/\s+/g, " ");
  comprobar(await veredicto.count() === 1 && (await cifra("minima")).includes("30.000 €")
            && (await cifra("segura")).includes("106.400 €") && (await cifra("p_max")).includes("€"),
    `el panel del veredicto muestra las tres cifras (${await veredicto.innerText().then((t) => t.replace(/\s+/g, " ").slice(0, 160)).catch(() => "sin panel")})`);
  comprobar(await veredicto.locator("[data-puja-recomendada]").count() === 1, "veredicto viable: se ofrece la puja recomendada");

  await pagina.getByRole("button", { name: "Guardar análisis" }).click();
  await pagina.waitForURL((u) => /\/app\/inversiones\/[0-9a-f-]{36}/.test(u.pathname), { timeout: 20000 });
  const id = new URL(pagina.url()).pathname.split("/").pop();
  await veredicto.waitFor({ timeout: 10000 }).catch(() => {});
  comprobar(await veredicto.count() === 1, "el resumen del detalle muestra el panel del veredicto");
  await pagina.getByRole("button", { name: "Estrategia de puja" }).click();
  await panel.waitFor({ timeout: 10000 }).catch(() => {});
  comprobar(await panel.count() === 1 && (await fila(pagina, "deposito")).includes("7.600 €"),
    "la pestaña «Estrategia de puja» del detalle muestra el mismo panel");
  // 5J-2b: régimen anterior ⇒ pujas visibles con prórroga (ADR-0025) y su depósito legal (ADR-0024).
  const estrategia = await pagina.locator("main").innerText();
  comprobar(estrategia.includes("Entrar tarde con límites precargados") && estrategia.includes("Depósito requerido: 7.600 €"),
    "el plan de puja usa la táctica y el depósito del régimen anterior");
  const baseLegal = panel.locator("details", { hasText: "Base legal aplicada" });
  await baseLegal.locator("summary").click();
  const legal = await baseLegal.innerText();
  comprobar(legal.includes("Forma de puja (pujas visibles; el cierre se prorroga tras la última puja):")
            && legal.includes("LEC, art. 648, regla 6.ª, y art. 649, apdo. 1 (redacción de 2015)"),
    "la base legal incluye la forma de puja con su artículo (5J-2b)");

  // Lo respondido llega a la entrada guardada y al resultado.
  const tok = (await (await fetch(`${BACKEND}/auth/login`, { method: "POST",
    body: new URLSearchParams({ username: ADMIN.email, password: ADMIN.password }) })).json()).access_token;
  const det = await (await fetch(`${BACKEND}/analisis/${id}`, { headers: { Authorization: `Bearer ${tok}` } })).json();
  const s = det.entrada?.subasta ?? {}, a = det.entrada?.activo ?? {};
  comprobar(s.procedimiento === "judicial" && s.regimen_judicial === "anterior" && s.cantidad_reclamada === 30000,
    `entrada guardada: ${s.procedimiento} · ${s.regimen_judicial} · ${s.cantidad_reclamada}`);
  comprobar(a.vivienda_habitual_ejecutado === "no" && a.es_vivienda_habitual === false,
    `vivienda habitual guardada como «no» y el booleano derivado falso (${a.vivienda_habitual_ejecutado}, ${a.es_vivienda_habitual})`);
  const proc = det.resultado?.procedimiento ?? {};
  comprobar(proc.regimen === "judicial_lec_2015" && !proc.regimen_asumido && proc.puja_minima_aprobable === 30000,
    `resultado: régimen ${proc.regimen}, puja mínima aprobable ${proc.puja_minima_aprobable}`);
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

console.log(fallos.length ? `\nFALLOS EN LOS DATOS DEL PROCEDIMIENTO: ${fallos.length}\n` : "\nDatos del procedimiento: todo correcto.\n");
process.exit(fallos.length ? 1 : 0);

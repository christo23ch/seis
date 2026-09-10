/**
 * Alta de punta a punta: navegador real → frontend → backend → base de datos.
 *
 * Existe por un bloqueo concreto. La Fase 14 hizo obligatorios los
 * consentimientos en `/auth/registro`; el backend quedó verde con 474 tests y
 * el alta REAL estaba rota, porque el frontend no los enviaba y recibía un 422.
 * Ninguna batería de las que había podía verlo: cada lado se probaba contra su
 * propia idea del contrato.
 *
 * Esto lo comprueba donde se rompe: rellenando el formulario de verdad.
 *
 * Uso:  bash e2e/correr.sh   (levanta backend, frontend, ejecuta esto y comprueba la BD)
 *
 * Vive aquí y no en `e2e/` porque Node resuelve los imports de un `.mjs` desde
 * la carpeta del propio fichero: playwright es devDependency del frontend y solo
 * se encuentra desde dentro de él.
 *
 * Este fichero cubre el NAVEGADOR. Que el dato llegara a la base lo comprueba
 * `e2e/comprobar_alta.py`, sobre el SQLite desechable de la ejecución.
 */
import { chromium } from "playwright";

const FRONTEND = process.env.E2E_FRONTEND ?? "http://localhost:3000";
const BACKEND = process.env.E2E_BACKEND ?? "http://localhost:8000/api/v1";
const EJECUTABLE = process.env.PLAYWRIGHT_CHROMIUM
  ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";

const fallos = [];
function comprobar(condicion, descripcion) {
  if (condicion) console.log(`  ✓ ${descripcion}`);
  else { console.log(`  ✗ ${descripcion}`); fallos.push(descripcion); }
}

// `.test` NO sirve: es un TLD reservado y `EmailStr` lo rechaza (bien
// rechazado). Un dominio de ejemplo normal es lo que usaría una persona.
const email = `e2e-${Date.now()}@ejemplo.com`;
const navegador = await chromium.launch({ executablePath: EJECUTABLE });
const pagina = await navegador.newPage();

// Diagnóstico permanente, no andamio de depuración: cuando esto falle en el
// futuro, el fallo será «no apareció la pantalla de confirmación» y sin el
// motivo de la consola o de la red se depura a ciegas.
const incidencias = [];
pagina.on("console", (m) => { if (m.type() === "error") incidencias.push(`consola: ${m.text()}`); });
pagina.on("requestfailed", (r) =>
  incidencias.push(`petición fallida: ${r.method()} ${r.url()} — ${r.failure()?.errorText}`));
pagina.on("response", async (r) => {
  if (r.url().includes("/auth/registro")) {
    incidencias.push(`respuesta de /auth/registro: ${r.status()} ${await r.text().catch(() => "")}`);
  } else if (r.status() >= 400) {
    // Con la URL: «Failed to load resource: 404» a secas no dice qué recurso, y
    // un 404 en una página pública puede ser un icono que falta o una ruta rota.
    incidencias.push(`respuesta ${r.status()}: ${r.url()}`);
  }
});

try {
  console.log(`\nAlta de punta a punta con ${email}\n`);
  await pagina.goto(`${FRONTEND}/registro`, { waitUntil: "networkidle" });

  await pagina.fill('input[type="email"]', email);
  await pagina.fill('input[type="password"]', "unaClaveLarga-14");

  const casillas = pagina.locator('input[type="checkbox"]');
  comprobar(await casillas.count() === 3, "hay tres casillas de consentimiento");

  // Ninguna premarcada: una casilla marcada de fábrica no recoge consentimiento,
  // porque dejarla como estaba no es un acto de quien se registra.
  const marcadasDeInicio = await casillas.evaluateAll(
    (c) => c.filter((x) => x.checked).length);
  comprobar(marcadasDeInicio === 0, "ninguna casilla viene premarcada");

  // Sin marcar los obligatorios, el navegador no deja enviar: quien se registra
  // no llega a ver un 422.
  await pagina.click('button[type="submit"]');
  comprobar(await pagina.locator("text=Revise su correo").count() === 0,
            "sin aceptar lo obligatorio, el alta no se envía");

  await casillas.nth(0).check();
  await casillas.nth(1).check();
  // La tercera se deja SIN marcar a propósito: es opcional, y su «no» también
  // tiene que guardarse.
  await pagina.click('button[type="submit"]');

  await pagina.waitForSelector("text=Revise su correo", { timeout: 15000 });
  comprobar(true, "el alta se completa y muestra la pantalla de confirmación");

  // Y el texto legal se puede LEER, sin cuenta y navegando de verdad: aceptar
  // algo que no se puede leer no es consentimiento, es un clic.
  const legal = await navegador.newPage();
  await legal.goto(`${FRONTEND}/legal/terminos`, { waitUntil: "networkidle" });
  const textoLegal = await legal.locator("body").innerText();
  comprobar(textoLegal.includes("Condiciones del servicio"),
            "la página de condiciones se abre sin tener cuenta");
  comprobar(textoLegal.includes("Versión"), "la página muestra la versión del texto");
  comprobar(textoLegal.toLowerCase().includes("pendiente de redacción"),
            "se avisa de que el texto aún no es definitivo, en vez de aparentar que lo es");
  await legal.close();
} catch (e) {
  console.log(`  ✗ excepción: ${e.message}`);
  fallos.push(e.message);
  const visible = await pagina.locator("body").innerText().catch(() => "");
  if (visible) console.log(`\n  Texto en pantalla:\n${visible.split("\n").map((l) => `    | ${l}`).join("\n")}`);
  await pagina.screenshot({ path: "/tmp/e2e-alta-fallo.png" }).catch(() => {});
} finally {
  if (incidencias.length) {
    console.log("\n  Incidencias del navegador:");
    for (const i of incidencias) console.log(`    · ${i}`);
  }
  await navegador.close();
}

// La comprobación de la base de datos la hace `comprobar_alta.py` sobre el
// fichero SQLite desechable, y NO un endpoint de apoyo. Añadir a la API una ruta
// que diga si un correo está registrado sería justamente el oráculo de
// enumeración que `/registro` evita respondiendo 201 exista o no la cuenta: un
// atajo para los tests que abre en producción el agujero que el producto cerró.
await (await import("node:fs/promises")).writeFile(
  process.env.E2E_EMAIL_FICHERO ?? "/tmp/e2e-email.txt", email);

console.log(fallos.length ? `\nFALLOS EN EL NAVEGADOR: ${fallos.length}\n`
                          : "\nNavegador: todo correcto.\n");
process.exit(fallos.length ? 1 : 0);

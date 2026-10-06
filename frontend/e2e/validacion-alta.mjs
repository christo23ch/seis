/**
 * Validación guiada del alta de inversión (Fase 5I-B), con un navegador real.
 *
 * Comprueba lo que pidió la prueba manual: si falta información, el formulario
 * lleva al primer campo pendiente y muestra un mensaje en rojo en TODOS los
 * obligatorios sin rellenar; y un 422 del backend se traduce a cada campo, en
 * español, en vez de mostrarse el texto de Pydantic.
 *
 *   1. Avanzar con obligatorios vacíos o no numéricos: mensaje bajo cada campo,
 *      `aria-invalid`, foco en el primero y el paso no avanza.
 *   2. Dos comparables sin €/m²: los dos marcados, el foco en el primero.
 *   3. Un 422 del backend (simulado con `page.route`: el formulario ya no deja
 *      enviar datos inválidos, así que no hay otra forma de provocarlo): el
 *      asistente vuelve al paso del campo, con el mensaje traducido y el foco.
 *   4. Nada de lo anterior crea un análisis.
 *   5. A 390 px, con los mensajes visibles, la página no desborda.
 *
 * Uso: lo ejecuta `e2e/correr_simulaciones.sh`, con su backend y su frontend.
 *
 * LO QUE NO CUBRE (ADR-0014):
 *   · El traductor contra TODOS los tipos de error de Pydantic: eso lo prueba
 *     `tests/errores-validacion.test.ts`. Aquí solo uno de campo y uno general.
 *   · Lectores de pantalla reales: se comprueban los atributos ARIA, no cómo
 *     los anuncia un lector.
 */
import { chromium } from "playwright";
import { rutaNavegador } from "../scripts/navegador.mjs";

const FRONTEND = process.env.E2E_FRONTEND ?? "http://localhost:3010";
const BACKEND = process.env.E2E_BACKEND ?? "http://localhost:8010/api/v1";
const ADMIN = { email: process.env.E2E_ADMIN_EMAIL ?? "admin@seis.local",
                password: process.env.E2E_ADMIN_PASSWORD ?? "admin-de-e2e" };

const fallos = [];
function comprobar(condicion, descripcion) {
  if (condicion) console.log(`  ✓ ${descripcion}`);
  else { console.log(`  ✗ ${descripcion}`); fallos.push(descripcion); }
}
const campo = (p, nombre) => p.locator(`[name="${nombre}"]`);
const enfocado = (p) => p.evaluate(() => document.activeElement?.getAttribute("name") ?? null);
/** Espera a que el foco llegue al campo y devuelve dónde está (Fase 5I.1-B). El formulario
 * lo mueve en un `requestAnimationFrame` tras pintar: leerlo nada más ver el error en rojo
 * era una carrera (falló 1 de 5 en la 5I.1). Si no llega, el `comprobar` falla legible. */
async function focoEn(p, nombre) {
  await p.waitForFunction((n) => document.activeElement?.getAttribute("name") === n, nombre, { timeout: 10000 })
    .catch(() => {});
  return enfocado(p);
}
const tituloPaso = async (p) => (await p.locator("h3", { hasText: /^Paso \d+ de 11/ }).textContent()) ?? "";
/** Mensaje de error asociado al campo por `aria-describedby` (que puede citar
 * también la ayuda: se toma el nodo marcado como error). */
async function errorDe(p, nombre) {
  const c = campo(p, nombre);
  if (await c.getAttribute("aria-invalid") !== "true") return null;
  const ids = ((await c.getAttribute("aria-describedby")) ?? "").split(/\s+/).filter(Boolean);
  for (const id of ids) {
    const nodo = p.locator(`[id="${id}"][data-error-campo]`);
    if (await nodo.count()) return (await nodo.textContent())?.trim() ?? null;
  }
  return null;
}
/** Espera a que el campo quede marcado como inválido (sin pausas fijas). */
const esperarInvalido = (p, nombre) =>
  p.locator(`[name="${nombre}"][aria-invalid="true"]`).waitFor({ timeout: 10000 });
/** Pulsa «Siguiente» y comprueba que se llega al paso esperado (el fallo se ve
 * donde ocurre, no varios pasos después). */
async function avanzarA(p, n) {
  await siguiente(p);
  await p.locator("h3", { hasText: new RegExp(`^Paso ${n} de 11`) }).waitFor({ timeout: 10000 });
}
async function entrar(ctx) {
  const p = await ctx.newPage();
  await p.goto(`${FRONTEND}/login`);
  await p.fill('input[type="email"]', ADMIN.email);
  await p.fill('input[type="password"]', ADMIN.password);
  await p.click('button[type="submit"]');
  await p.waitForURL((u) => u.pathname.startsWith("/app"), { timeout: 20000 });
  await p.goto(`${FRONTEND}/app/nueva`, { waitUntil: "networkidle" });
  return p;
}
const siguiente = (p) => p.getByRole("button", { name: "Siguiente" }).click();
async function contarAnalisis() {
  const tok = (await (await fetch(`${BACKEND}/auth/login`, { method: "POST",
    body: new URLSearchParams({ username: ADMIN.email, password: ADMIN.password }) })).json()).access_token;
  return (await (await fetch(`${BACKEND}/analisis`, { headers: { Authorization: `Bearer ${tok}` } })).json()).length;
}

const navegador = await chromium.launch({ executablePath: rutaNavegador() });
const incidencias = [];
const creaciones = [];
let pagina;
try {
  console.log("\nValidación guiada del alta de inversión\n");
  const antes = await contarAnalisis();
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
  const p = pagina = await entrar(ctx);
  p.on("console", (m) => { if (m.type() === "error") incidencias.push(`consola: ${m.text()}`); });
  p.on("request", (r) => {
    if (r.method() === "POST" && new URL(r.url()).pathname.endsWith("/analisis")) creaciones.push(r.url());
  });

  // 1 · Obligatorio vacío.
  await siguiente(p);
  await esperarInvalido(p, "subasta.valor_subasta");
  comprobar((await tituloPaso(p)).startsWith("Paso 1 de 11"), "con el valor de subasta vacío, el paso no avanza");
  comprobar(await errorDe(p, "subasta.valor_subasta") === "Campo obligatorio",
    "«Campo obligatorio» en rojo bajo el valor de subasta, enlazado por aria-describedby");
  comprobar(await focoEn(p, "subasta.valor_subasta") === "subasta.valor_subasta", "el foco va al campo pendiente");
  // Con el texto: Next.js ya pinta su propio `role="alert"` (el anunciador de rutas).
  comprobar(await p.locator('[role="alert"]', { hasText: "Revise los campos marcados" }).count() === 1,
    "un aviso con role=alert resume el problema");
  comprobar(await p.locator("label", { hasText: "Valor de subasta" }).locator("text=*").count() === 1,
    "el obligatorio está marcado con «*»");
  await campo(p, "subasta.valor_subasta").fill("152.000");
  // Depósito en euros sin importe: error; al volver a «Porcentaje», el campo se
  // oculta y su error se retira (sin aviso «fantasma» ni paso bloqueado).
  await campo(p, "subasta.deposito_modo").selectOption("importe");
  await siguiente(p);
  await esperarInvalido(p, "subasta.deposito_importe");
  comprobar(await errorDe(p, "subasta.deposito_importe") === "Campo obligatorio",
    "en modo importe, el importe del depósito es obligatorio");
  await campo(p, "subasta.deposito_modo").selectOption("porcentaje");
  await p.locator('[role="alert"]', { hasText: "Revise los campos marcados" }).waitFor({ state: "detached", timeout: 5000 })
    .catch(() => {});
  comprobar(await p.locator('[role="alert"]', { hasText: "Revise los campos marcados" }).count() === 0,
    "al ocultarse el importe, su error y el aviso desaparecen");
  await avanzarA(p, 2);

  // Texto que no es un número.
  await campo(p, "activo.superficie_m2").fill("ochenta");
  await siguiente(p);
  await esperarInvalido(p, "activo.superficie_m2");
  comprobar(await errorDe(p, "activo.superficie_m2") === "Introduzca un número",
    "«Introduzca un número» si la superficie no es un número");
  // Ir y volver con un error a la vista no roba el foco: el foco solo se mueve
  // cuando una validación falla, no en cada cambio de paso.
  await p.getByRole("button", { name: "Atrás" }).click();
  await p.locator("h3", { hasText: /^Paso 1 de 11/ }).waitFor();
  await campo(p, "subasta.identificador_externo").focus();
  await avanzarA(p, 2);
  await p.waitForFunction(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  comprobar(await enfocado(p) !== "activo.superficie_m2",
    "volver a un paso con un error no se lleva el foco a ese campo sin pedirlo");
  await campo(p, "activo.superficie_m2").fill("82");
  await avanzarA(p, 3);
  await avanzarA(p, 4);
  await avanzarA(p, 5);
  // 5 · Municipio vacío.
  await siguiente(p);
  await esperarInvalido(p, "activo.municipio");
  comprobar(await errorDe(p, "activo.municipio") === "Campo obligatorio", "«Campo obligatorio» bajo el municipio");
  await campo(p, "activo.municipio").fill("E2E validación");
  await avanzarA(p, 6);

  // 2 · Dos comparables sin €/m²: los dos marcados, foco en el primero.
  await p.getByRole("button", { name: "Añadir comparable" }).click();
  await siguiente(p);
  await esperarInvalido(p, "comparables.0.precio_m2");
  comprobar(await errorDe(p, "comparables.0.precio_m2") === "Campo obligatorio"
            && await errorDe(p, "comparables.1.precio_m2") === "Campo obligatorio",
    "los DOS comparables sin €/m² muestran «Campo obligatorio»");
  comprobar(await focoEn(p, "comparables.0.precio_m2") === "comparables.0.precio_m2", "el foco va al primero de ellos");
  await campo(p, "comparables.0.precio_m2").fill("2.293");
  await campo(p, "comparables.1.precio_m2").fill("2.310");
  await avanzarA(p, 7);
  await avanzarA(p, 8);
  await avanzarA(p, 9);
  await avanzarA(p, 10);

  // 3 · Un 422 del backend se traduce y lleva al campo de otro paso.
  await p.route("**/analisis/simular", (ruta) => ruta.fulfill({
    status: 422, contentType: "application/json",
    body: JSON.stringify({ detail: [
      { type: "int_parsing", loc: ["body", "activo", "anio_construccion"],
        msg: "Input should be a valid integer, unable to parse string as an integer", input: "x" },
      { type: "literal_error", loc: ["body", "activo", "atributos", "banos"], msg: "Input should be 'a'" },
    ] }),
  }));
  await p.getByRole("button", { name: "Calcular decisión" }).click();
  await p.locator("h3", { hasText: /^Paso 2 de 11/ }).waitFor({ timeout: 15000 });
  await esperarInvalido(p, "activo.anio_construccion");
  comprobar((await tituloPaso(p)).startsWith("Paso 2 de 11"), "ante el 422, el asistente vuelve al paso del campo (2)");
  comprobar(await errorDe(p, "activo.anio_construccion") === "Introduzca un número entero",
    "el error del backend aparece bajo su campo, en español");
  comprobar(await focoEn(p, "activo.anio_construccion") === "activo.anio_construccion", "con el foco en ese campo");
  const textoAviso = (await p.locator('[role="alert"]', { hasText: "servidor" }).first().innerText()).replace(/\s+/g, " ");
  comprobar(textoAviso.includes("Activo › atributos › banos: valor no válido"),
    "el error sin campo se muestra como mensaje general legible");
  comprobar(!/Input should be|unable to parse/.test(await p.locator("body").innerText()),
    "ningún texto de Pydantic en bruto en pantalla");
  await p.unroute("**/analisis/simular");

  // 4 · Nada creado.
  comprobar(creaciones.length === 0, `no se ha enviado ninguna creación de análisis (${creaciones.length})`);
  comprobar(await contarAnalisis() === antes, "la lista de análisis no ha cambiado");
  await ctx.close();

  // 5 · 390 px con los mensajes visibles.
  const movil = await navegador.newContext({ viewport: { width: 390, height: 844 } });
  const m = await entrar(movil);
  await siguiente(m);
  await esperarInvalido(m, "subasta.valor_subasta");
  const [ancho, visible] = await m.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  comprobar(await errorDe(m, "subasta.valor_subasta") === "Campo obligatorio", "a 390 px el mensaje se muestra");
  comprobar(ancho <= visible, `a 390 px con mensajes no desborda (${ancho} ≤ ${visible})`);
  await movil.close();
} catch (e) {
  console.log(`  ✗ excepción: ${e.message}`);
  fallos.push(e.message);
  const t = await pagina?.locator("body").innerText().catch(() => "");
  if (t) console.log(t.split("\n").slice(0, 50).map((l) => `    | ${l}`).join("\n"));
} finally {
  if (incidencias.length) {
    console.log("\n  Incidencias del navegador:");
    for (const i of incidencias) console.log(`    · ${i.slice(0, 400)}`);
  }
  await navegador.close();
}

console.log(fallos.length ? `\nFALLOS EN LA VALIDACIÓN GUIADA: ${fallos.length}\n` : "\nValidación guiada: todo correcto.\n");
process.exit(fallos.length ? 1 : 0);

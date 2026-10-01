// Ruta del navegador para TODOS los guiones de Playwright (Fase 5G.4-C).
//
// Antes cada guion la resolvía a su manera: unos leían `CHROMIUM_PATH`, otros
// `PLAYWRIGHT_CHROMIUM`, y `simulaciones.mjs` las dos en el orden contrario. Con
// una sola función, el orden de preferencia es el mismo en todos:
//
//   1. CHROMIUM_PATH        — la variable del proyecto (CI, Windows, sandbox).
//   2. PLAYWRIGHT_CHROMIUM  — solo por compatibilidad con lanzadores antiguos.
//   3. el Chromium del sandbox de Linux, como último recurso.
//
// Una variable definida pero vacía cuenta como no definida.
export function rutaNavegador() {
  return process.env.CHROMIUM_PATH
    || process.env.PLAYWRIGHT_CHROMIUM
    || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
}

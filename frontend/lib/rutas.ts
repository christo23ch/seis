// Único sitio que sabe dónde vive la aplicación privada.
//
// Decisión de la Fase 15 (2026-09-13): la landing pública ocupa la raíz y la app
// pasa a `/app`. Se eligió frente a un subdominio porque un subdominio **depende
// del dominio, que es la hipótesis H11 y sigue sin decidir**, además de DNS,
// certificados y el dominio de la cookie de sesión: habría dejado la fase a medias
// esperando infraestructura.
//
// Por qué una constante y no `/app` escrito en cada enlace: si algún día se va al
// subdominio, cambia este fichero y nada más. Escribirlo cuarenta veces es
// exactamente el patrón que produjo los nueve tamaños de fuente del diagnóstico.
export const BASE_APP = "/app";

/** Ruta absoluta dentro de la app privada. `rutaApp()` es su portada. */
export const rutaApp = (camino: string = "/"): string =>
  camino === "/" ? BASE_APP : `${BASE_APP}${camino}`;

/** Rutas públicas, que NO llevan prefijo. Se listan para que el guard las conozca. */
export const RUTAS_PUBLICAS = [
  "/", "/login", "/registro", "/recuperar", "/resetear", "/verificar", "/ayuda", "/baja",
] as const;

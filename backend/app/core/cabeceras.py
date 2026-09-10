"""Cabeceras de seguridad (Fase 16, hallazgo M-1).

La aplicación devuelve JSON casi siempre, así que el margen para XSS reflejado es
pequeño. Pero **casi siempre no es siempre**: `/analisis/{id}/informe` devuelve
`PlainTextResponse` y `/informe.pdf` un binario, y sin `nosniff` un navegador
puede decidir por su cuenta qué son.

QUÉ CUBRE: las cinco cabeceras que se pueden emitir desde la aplicación sin
saber nada del despliegue.

QUÉ NO CUBRE, y va aquí junto al mecanismo (ADR-0014):

- **HSTS no lo pone esto de forma efectiva.** Se emite, pero un navegador solo lo
  respeta sobre HTTPS, y quien termina TLS es el borde. Si el borde no fuerza
  HTTPS, esta cabecera no salva nada: requisito R-3 del informe.
- **La CSP es la de una API, no la de una aplicación web.** `default-src 'none'`
  vale porque estas respuestas no cargan nada; **no protege al frontend**, que es
  otro despliegue y necesita la suya.
- **No sustituye a las cabeceras del borde.** Un proxy puede añadir o quitar; lo
  que se emite aquí es el suelo, no el techo.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware

# `default-src 'none'` porque una respuesta de API no carga scripts, estilos ni
# imágenes. Si algún día se sirve HTML desde aquí, esta política hay que
# revisarla: rompería la página en vez de protegerla.
CSP_DE_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

CABECERAS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": CSP_DE_API,
    # Dos años y subdominios, que es lo que piden las listas de precarga. No se
    # incluye `preload`: eso es un compromiso que se solicita a mano y del que
    # cuesta salir, y no es decisión de un middleware.
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


class CabecerasDeSeguridad(BaseHTTPMiddleware):
    """Añade las cabeceras sin pisar las que ya venga trayendo la respuesta.

    `setdefault` y no asignación: si un endpoint decide su propia CSP —o el borde
    la reescribe— este middleware no debe deshacerlo.
    """

    async def dispatch(self, peticion, siguiente):
        respuesta = await siguiente(peticion)
        for nombre, valor in CABECERAS.items():
            respuesta.headers.setdefault(nombre, valor)
        return respuesta

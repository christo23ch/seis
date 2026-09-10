"""Detección de datos personales en JSON libre (Fase 16, hallazgo 1.3).

Vive en `core` y **no depende de nada de la aplicación** por un motivo concreto:
así `app/models.py` puede importarlo para registrar su oyente sin crear un ciclo,
y la barrera queda activa **allí donde se importen los modelos** — la API, el
worker de Celery, los scripts, una consola de depuración. Colgarla de un import
en `main.py` la habría dejado ausente en el worker, que es justamente donde
corren las tareas que más auditan.

QUÉ CUBRE: la forma de una dirección de correo, dentro de cadenas, de listas, de
diccionarios anidados y de las CLAVES de un diccionario.

QUÉ NO CUBRE: teléfonos, DNI, direcciones postales, nombres de persona,
coordenadas. Solo el correo, que es el identificador con el que este sistema
nombra personas de hecho. Esto no es una detección de PII general y no debe
usarse como si lo fuera.
"""
from __future__ import annotations

import re

# Deliberadamente laxa: se prefiere un falso positivo ruidoso —que obliga a
# mirar— a un falso negativo silencioso.
FORMA_DE_CORREO = re.compile(r"[^\s@]+@[^\s@]+\.[A-Za-z]{2,}")


class DatoPersonalEnAuditoria(AssertionError):
    """Un `delta` de auditoría contiene algo con forma de dirección de correo."""


def buscar_correo(valor, ruta: str = "delta") -> str | None:
    """Recorre el JSON entero. Devuelve la RUTA del primer correo, o None.

    Devuelve la ruta y no un booleano porque el mensaje de error tiene que decir
    dónde está: «hay un correo en el delta» obliga a buscarlo a mano.
    """
    if isinstance(valor, str):
        return ruta if FORMA_DE_CORREO.search(valor) else None
    if isinstance(valor, dict):
        for clave, sub in valor.items():
            # También la CLAVE: `{"juan@ejemplo.com": "activo"}` esconde la
            # dirección donde nadie la busca.
            if isinstance(clave, str) and FORMA_DE_CORREO.search(clave):
                return f"{ruta}.<clave {clave!r}>"
            encontrado = buscar_correo(sub, f"{ruta}.{clave}")
            if encontrado:
                return encontrado
        return None
    if isinstance(valor, (list, tuple)):
        for i, sub in enumerate(valor):
            encontrado = buscar_correo(sub, f"{ruta}[{i}]")
            if encontrado:
                return encontrado
    return None


def mensaje_de_veto(accion: str, donde: str) -> str:
    """El texto que explica por qué no se escribe. Compartido por las dos vías."""
    return (
        f"El `delta` de la auditoría «{accion}» contiene algo con forma de "
        f"dirección de correo en {donde}. No se escribe.\n\n"
        "El borrado por RGPD limpia `quien` y `entidad_id` por nombre de columna, "
        "pero NO puede limpiar `delta`: su contenido es arbitrario. Un correo "
        "aquí sobreviviría a un borrado que el sistema declara completo, y el "
        "test que deriva las tablas hijas del esquema no lo vería nunca, porque "
        "`auditoria` no tiene clave foránea a `usuario`.\n\n"
        "Use el identificador (UUID) de la persona, que el borrado sí sabe "
        "seudonimizar.")

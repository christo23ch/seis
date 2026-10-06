"""Fase 5I-D — estado de conservación «No consta» (ADR-0020).

Un único sitio decide qué estado se usa cuando el del inmueble no consta: el que
fija el parámetro T3 `conservacion.desconocido_usa` («malo» de fábrica, P5). Es el
mismo patrón que `ocupacion.desconocida.usa` (precario): el dato ausente no se
rellena con el valor optimista (P4), se sustituye por uno prudente y se declara.

M01 publica el estado efectivo como hecho; M03 (k_estado del valor actual) y M05
(nivel de reforma) lo piden aquí. Ningún peso ni fórmula cambia: con «No consta»
el cálculo es idéntico al del estado asumido (`tests/test_conservacion_no_consta_5i.py`).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.params.store import Parametros

NO_CONSTA = "desconocido"


class EstadoAsumidoInvalidoError(ValueError):
    """`conservacion.desconocido_usa` no es un estado que M03 y M05 sepan usar."""


def estados_validos(params: "Parametros") -> list[str]:
    """Estados que admiten A LA VEZ M03 (`valoracion.k_estado`) y M05
    (`reforma.nivel_por_estado`), en el orden de `k_estado`."""
    nivel = params.seccion("reforma.nivel_por_estado")
    return [e for e in params.seccion("valoracion.k_estado") if e in nivel and e != NO_CONSTA]


def validar_estado_asumido(params: "Parametros") -> str:
    """El estado asumido si es válido; si no, `EstadoAsumidoInvalidoError` con los
    valores admitidos. La usan el motor y `set_parametro` (al ESCRIBIR el parámetro,
    para que un valor erróneo no se descubra al analizar)."""
    asumido = params.get("conservacion.desconocido_usa", None)
    validos = estados_validos(params)
    if asumido not in validos:
        raise EstadoAsumidoInvalidoError(
            f"conservacion.desconocido_usa = {asumido!r} no es un estado de conservación válido; "
            f"valores admitidos: {', '.join(validos)}")
    return asumido


def estado_efectivo(estado: str, params: "Parametros") -> str:
    """El estado declarado, o el asumido por el parámetro si no consta."""
    return estado if estado != NO_CONSTA else validar_estado_asumido(params)

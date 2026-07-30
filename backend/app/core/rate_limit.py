"""Limitador anti-abuso de ventana deslizante (Fase 10).

Cuenta intentos por clave dentro de una ventana temporal y responde si la clave
está bloqueada. Lo usan el login (fuerza bruta de credenciales) y los tres
endpoints públicos que envían correo, que sin límite convertirían a SEIS en un
cañón de email contra buzones ajenos.

**Redis es el almacén real; la memoria es un respaldo, no un igual.** El backend
arranca con `uvicorn --workers 2` (`docker-compose.yml`), así que con el respaldo
en memoria cada proceso lleva su propio contador y el límite efectivo se
multiplica por el número de workers. Es aceptable en tests y en desarrollo, donde
hay un solo proceso; en producción, quedarse sin Redis degrada la protección.
Por eso la degradación se registra en el log con nivel WARNING una sola vez, en
lugar de pasar inadvertida.

El módulo nunca lanza: un fallo del almacén degrada a memoria, jamás tumba un
login.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid

from app.core.config import get_settings

log = logging.getLogger("seis.rate_limit")

_PREFIJO = "seis:rl:"

# Respaldo en memoria: clave → lista de marcas de tiempo (segundos epoch).
_memoria: dict[str, list[float]] = {}
_cerrojo = threading.Lock()

# Cliente de Redis resuelto una sola vez. `False` significa «se intentó y no hay»
# —distinto de `None`, que significa «aún no se ha intentado»—, y evita repetir
# el intento de conexión en cada petición de login.
_cliente_redis: object | None | bool = None


def _ahora() -> float:
    """Reloj del limitador.

    Aislado en una función a propósito: los tests lo sustituyen para envejecer
    los intentos y comprobar que la ventana se cierra, sin dormir de verdad.
    """
    return time.time()


def _ventana_segundos() -> int:
    return get_settings().login_ventana_min * 60


def _maximo() -> int:
    return get_settings().login_max_intentos


def _redis():
    """Devuelve el cliente de Redis, o `None` si hay que usar el respaldo."""
    global _cliente_redis
    if _cliente_redis is not None:
        return _cliente_redis or None
    try:
        import redis as redis_lib

        cliente = redis_lib.Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            decode_responses=True,
        )
        cliente.ping()
        _cliente_redis = cliente
        return cliente
    except Exception:                                    # noqa: BLE001 — nunca rompe
        log.warning(
            "Rate limit sin Redis: se usa el respaldo en memoria. Con más de un "
            "worker el contador es por proceso y el límite efectivo se multiplica.")
        _cliente_redis = False
        return None


def registrar_intento(clave: str) -> None:
    """Anota un intento para `clave`.

    El login solo anota los **fallidos** —un acceso correcto no debe acercarte al
    bloqueo—, mientras que los endpoints que envían correo anotan **todos**: ahí
    lo que se limita es el envío en sí, salga bien o mal.
    """
    ahora = _ahora()
    cliente = _redis()
    if cliente is not None:
        try:
            nombre = _PREFIJO + clave
            tuberia = cliente.pipeline()
            tuberia.zremrangebyscore(nombre, 0, ahora - _ventana_segundos())
            # El miembro debe ser único o el ZADD sobrescribiría el intento
            # anterior en vez de sumar uno nuevo: dos fallos en el mismo
            # milisegundo contarían como uno solo.
            tuberia.zadd(nombre, {uuid.uuid4().hex: ahora})
            tuberia.expire(nombre, _ventana_segundos())
            tuberia.execute()
            return
        except Exception:                                # noqa: BLE001
            log.warning("Fallo escribiendo en Redis; se degrada a memoria")
    with _cerrojo:
        intentos = [t for t in _memoria.get(clave, [])
                    if t > ahora - _ventana_segundos()]
        intentos.append(ahora)
        _memoria[clave] = intentos


def bloqueado(clave: str) -> bool:
    """True si `clave` ha agotado los intentos permitidos en la ventana."""
    ahora = _ahora()
    cliente = _redis()
    if cliente is not None:
        try:
            nombre = _PREFIJO + clave
            cliente.zremrangebyscore(nombre, 0, ahora - _ventana_segundos())
            return int(cliente.zcard(nombre)) >= _maximo()
        except Exception:                                # noqa: BLE001
            log.warning("Fallo leyendo de Redis; se degrada a memoria")
    with _cerrojo:
        intentos = [t for t in _memoria.get(clave, [])
                    if t > ahora - _ventana_segundos()]
        _memoria[clave] = intentos
        return len(intentos) >= _maximo()


def limpiar(clave: str) -> None:
    """Borra el contador de `clave`. Lo llama el login tras un acceso correcto."""
    cliente = _redis()
    if cliente is not None:
        try:
            cliente.delete(_PREFIJO + clave)
        except Exception:                                # noqa: BLE001
            log.warning("Fallo borrando en Redis; se degrada a memoria")
    with _cerrojo:
        _memoria.pop(clave, None)


def limpiar_todo() -> None:
    """Vacía el limitador entero. Uso previsto: aislamiento entre tests."""
    cliente = _redis()
    if cliente is not None:
        try:
            claves = list(cliente.scan_iter(match=_PREFIJO + "*"))
            if claves:
                cliente.delete(*claves)
        except Exception:                                # noqa: BLE001
            log.warning("Fallo vaciando Redis; se degrada a memoria")
    with _cerrojo:
        _memoria.clear()

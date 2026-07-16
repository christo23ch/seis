"""Rate limiting (Fase 10): anti fuerza-bruta en /auth/login, doble cubo.

Un intento de login solo se permite si NINGUNO de los dos cubos está
bloqueado: uno por email (evita que ataquen una cuenta concreta) y otro por
IP (evita que una sola IP pruebe muchas cuentas). Un fallo incrementa ambos;
un éxito limpia ambos.

Redis si `REDIS_URL` responde; si no (dev/test sin Redis), fallback a un
diccionario en memoria de proceso — mismo comportamiento observable, solo
que no sobrevive a un reinicio ni se comparte entre workers (aceptable fuera
de producción real, donde Redis siempre está disponible).
"""
from __future__ import annotations

import time
from collections import defaultdict

import redis

from app.core.config import get_settings

_KEY_PREFIX = "seis:ratelimit:"
_memoria: dict[str, list[float]] = defaultdict(list)

_redis_cliente_cache: redis.Redis | None = None
_redis_comprobado = False


def _redis_cliente() -> redis.Redis | None:
    """Cliente Redis si el servidor responde; None en caso contrario.

    El resultado (incl. el fallo) se cachea para el proceso: en tests sin
    Redis evita reintentar la conexión en cada llamada.
    """
    global _redis_cliente_cache, _redis_comprobado
    if not _redis_comprobado:
        _redis_comprobado = True
        try:
            candidato = redis.from_url(get_settings().redis_url, decode_responses=True,
                                       socket_connect_timeout=1, socket_timeout=1)
            candidato.ping()
            _redis_cliente_cache = candidato
        except Exception:
            _redis_cliente_cache = None
    return _redis_cliente_cache


def _clave(bucket: str, valor: str) -> str:
    return f"{_KEY_PREFIX}{bucket}:{valor}"


def registrar_fallo(bucket: str, valor: str) -> None:
    ventana_seg = get_settings().login_ventana_min * 60
    clave = _clave(bucket, valor)
    ahora = time.time()
    r = _redis_cliente()
    if r is not None:
        pipe = r.pipeline()
        pipe.rpush(clave, ahora)
        pipe.expire(clave, ventana_seg)
        pipe.execute()
        return
    _memoria[clave] = [t for t in _memoria[clave] if ahora - t < ventana_seg]
    _memoria[clave].append(ahora)


def bloqueado(bucket: str, valor: str) -> bool:
    s = get_settings()
    ventana_seg = s.login_ventana_min * 60
    clave = _clave(bucket, valor)
    ahora = time.time()
    r = _redis_cliente()
    if r is not None:
        vals = r.lrange(clave, 0, -1)
        recientes = [v for v in vals if ahora - float(v) < ventana_seg]
        return len(recientes) >= s.login_max_intentos
    recientes = [t for t in _memoria.get(clave, []) if ahora - t < ventana_seg]
    _memoria[clave] = recientes
    return len(recientes) >= s.login_max_intentos


def limpiar(bucket: str, valor: str) -> None:
    clave = _clave(bucket, valor)
    r = _redis_cliente()
    if r is not None:
        r.delete(clave)
    _memoria.pop(clave, None)


def limpiar_todo() -> None:
    """Solo para tests: vacía el fallback de memoria y las claves de Redis en uso."""
    r = _redis_cliente()
    if r is not None:
        claves = r.keys(f"{_KEY_PREFIX}*")
        if claves:
            r.delete(*claves)
    _memoria.clear()

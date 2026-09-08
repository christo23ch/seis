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

# Cliente de Redis vivo, o `None` si ahora mismo no lo hay.
#
# Hasta la Fase 11 esto se cacheaba como `False` al primer fallo y **no se
# reintentaba en toda la vida del proceso**: una caída de Redis degradaba la
# protección a memoria de forma silenciosa y PERMANENTE, de modo que recuperar
# Redis no servía de nada hasta reiniciar, y con `--workers 2` el límite efectivo
# quedaba multiplicado por el número de workers para siempre. Ahora el fallo solo
# abre una ventana de espera, y pasada esa ventana se vuelve a intentar.
_cliente_redis: object | None = None

# Instante (reloj monótono) a partir del cual se puede reintentar la conexión.
_proximo_reintento: float = 0.0
_espera_actual: float = 0.0

# Última caída de Redis, en el reloj de `_ahora()` —no en el monótono— porque se
# compara con la ventana del limitador. Ver `_degradacion_reciente`.
_ultima_degradacion: float = 0.0

# El reintento va con retroceso exponencial acotado: si Redis está caído de
# verdad, no tiene sentido pagar el timeout de conexión en cada petición de
# login; y si vuelve, treinta segundos es un plazo razonable para notarlo.
_ESPERA_INICIAL_SEG = 1.0
_ESPERA_MAXIMA_SEG = 30.0

# Protege el estado de conexión. Separado de `_cerrojo` (que guarda `_memoria`)
# para que una reconexión, que puede tocar red, no bloquee a quien solo quiere
# contar intentos. Uvicorn ejecuta los endpoints síncronos en un threadpool, así
# que aquí hay concurrencia real y no teórica.
_cerrojo_conexion = threading.Lock()

# ¿Estamos ahora mismo degradados a memoria? Solo sirve para registrar en el log
# las TRANSICIONES —caída y recuperación— en lugar de repetir el mismo aviso en
# cada petición, que es la forma más rápida de que nadie lea los logs.
_degradado = False


def _reloj_backoff() -> float:
    """Reloj del retroceso exponencial.

    A propósito `time.monotonic()` y no `_ahora()`: los tests sustituyen `_ahora`
    para envejecer intentos y cerrar la ventana del limitador, y no deben
    arrastrar consigo la política de reconexión, que es un asunto distinto.
    """
    return time.monotonic()


def _marcar_caida() -> None:
    """Cierra el cliente actual y abre la ventana de espera antes del reintento."""
    global _cliente_redis, _proximo_reintento, _espera_actual, _degradado
    global _ultima_degradacion
    with _cerrojo_conexion:
        anterior, _cliente_redis = _cliente_redis, None
        _ultima_degradacion = _ahora()
        _espera_actual = min(max(_espera_actual * 2, _ESPERA_INICIAL_SEG),
                             _ESPERA_MAXIMA_SEG)
        _proximo_reintento = _reloj_backoff() + _espera_actual
        primera_vez = not _degradado
        _degradado = True
        espera = _espera_actual
    # Cerrar fuera del cerrojo: `close()` puede tocar red y no debe bloquear a
    # otro hilo que solo quiera consultar el estado.
    if anterior is not None:
        try:
            anterior.close()
        except Exception:                                # noqa: BLE001
            log.debug("No se pudo cerrar el cliente de Redis", exc_info=True)
    if primera_vez:
        log.warning(
            "Rate limit sin Redis: se usa el respaldo en memoria. Con más de un "
            "worker el contador es por proceso y el límite efectivo se "
            "multiplica. Se reintentará la conexión en %.0f s.", espera)


def _marcar_operacion_correcta() -> None:
    """Da por recuperado a Redis tras una OPERACIÓN correcta, no tras un `ping`.

    La distinción importa: un Redis que responde al `PING` pero rechaza escrituras
    —memoria agotada con `noeviction`, réplica en solo lectura, `MISCONF`— dejaba
    el retroceso permanentemente en su valor inicial, porque cada reconexión lo
    reiniciaba. El resultado era un ciclo de un segundo: fallo, aviso, reconexión,
    «recuperado», fallo… con un cliente nuevo y dos líneas de log por vuelta,
    indefinidamente. Reiniciar solo cuando una operación real funciona hace que
    el retroceso crezca también en ese caso, que es el más probable de todos.
    """
    global _espera_actual, _degradado
    with _cerrojo_conexion:
        _espera_actual = 0.0
        recuperado = _degradado
        _degradado = False
    if recuperado:
        log.info("Rate limit: Redis recuperado; el contador vuelve a ser "
                 "compartido entre workers.")


def reiniciar_conexion() -> None:
    """Olvida el cliente y la ventana de espera. Uso previsto: tests.

    Deliberadamente **fuera** de `limpiar_todo()`: aquella se ejecuta antes y
    después de cada test, y reiniciar aquí la conexión haría que la suite entera
    pagase un intento de conexión —con su timeout— por test.
    """
    global _cliente_redis, _proximo_reintento, _espera_actual, _degradado
    global _ultima_degradacion
    with _cerrojo_conexion:
        _cliente_redis = None
        _proximo_reintento = 0.0
        _espera_actual = 0.0
        _ultima_degradacion = 0.0
        _degradado = False


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


# Techo del respaldo en memoria. Las claves las elige quien llama —y en
# `/recuperar` van por email, que el atacante controla—, así que sin tope una
# ventana de degradación permite crecer el diccionario sin límite mandando una
# dirección distinta en cada petición. Al llegar al techo se desaloja la clave
# más antigua: perder el contador de la más vieja es preferible a agotar memoria.
_MAX_CLAVES_MEMORIA = 10_000


def _anotar_en_memoria(clave: str, ahora: float) -> None:
    with _cerrojo:
        intentos = [t for t in _memoria.get(clave, [])
                    if t > ahora - _ventana_segundos()]
        intentos.append(ahora)
        _memoria[clave] = intentos
        while len(_memoria) > _MAX_CLAVES_MEMORIA:
            _memoria.pop(next(iter(_memoria)))


def _cuenta_en_memoria(clave: str, ahora: float) -> int:
    """Intentos vivos de `clave`. **No crea la entrada si no existe.**

    Antes se reasignaba `_memoria[clave]` al consultar, de modo que cada sondeo
    de una clave inexistente dejaba una entrada permanente: leer hacía crecer la
    estructura, que es justo lo que no debe hacer una lectura.
    """
    with _cerrojo:
        intentos = _memoria.get(clave)
        if not intentos:
            return 0
        vivos = [t for t in intentos if t > ahora - _ventana_segundos()]
        if vivos:
            _memoria[clave] = vivos
        else:
            _memoria.pop(clave, None)
        return len(vivos)


def _construir_cliente():
    """Crea el cliente de Redis sin comprobarlo.

    Aislado en una función para que los tests puedan ejercitar la política de
    reconexión —caída, ventana de espera, recuperación— sin levantar un Redis de
    verdad. Sin esta costura, la deuda 7 solo sería comprobable con un servidor
    real que además hubiera que tirar y levantar a mitad de test.
    """
    import redis as redis_lib

    return redis_lib.Redis.from_url(
        get_settings().redis_url,
        socket_connect_timeout=0.25,
        socket_timeout=0.25,
        decode_responses=True,
    )


def _redis():
    """Devuelve el cliente de Redis, o `None` si hay que usar el respaldo.

    Si no hay cliente y aún no ha vencido la ventana de espera, devuelve `None`
    **sin intentar conectar**: es lo que evita pagar el timeout de conexión en
    cada petición mientras Redis está caído.
    """
    global _cliente_redis
    if _cliente_redis is not None:
        return _cliente_redis
    if _reloj_backoff() < _proximo_reintento:
        return None
    try:
        cliente = _construir_cliente()
        cliente.ping()
        # Se guarda el cliente, pero NO se da por recuperado el servicio: eso lo
        # decide `_marcar_operacion_correcta()` cuando una operación real
        # funcione. Un `ping` que responde no garantiza que se pueda escribir.
        _cliente_redis = cliente
        return cliente
    except Exception:                                    # noqa: BLE001 — nunca rompe
        _marcar_caida()
        return None


def registrar_intento(clave: str) -> None:
    """Anota un intento para `clave`.

    El login solo anota los **fallidos** —un acceso correcto no debe acercarte al
    bloqueo—, mientras que los endpoints que envían correo anotan **todos**: ahí
    lo que se limita es el envío en sí, salga bien o mal.
    """
    ahora = _ahora()
    # Se anota SIEMPRE en memoria, además de en Redis. No es redundancia: los dos
    # almacenes no se sincronizan jamás, así que si solo se escribiera en el que
    # esté disponible, el instante en que Redis cae o vuelve **pondría a cero el
    # contador de la víctima**. Con el retroceso de esta misma fase eso pasó de
    # ocurrir una vez a poder ocurrir cada pocos segundos, y un atacante solo
    # tendría que espaciar sus intentos alrededor de cada parpadeo para no llegar
    # nunca al límite. Escribir en ambos y leer en OR cierra esa ventana.
    _anotar_en_memoria(clave, ahora)
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
            _marcar_operacion_correcta()
            return
        except Exception:                                # noqa: BLE001
            # `_marcar_caida()` y no solo un log: si Redis muere a mitad de vida
            # del proceso, el cliente cacheado sigue apuntando a un servidor que
            # no responde y CADA petición pagaría su timeout de conexión antes
            # de degradar. Soltarlo aquí hace que la ventana de espera entre en
            # juego y el coste por petición vuelva a ser cero.
            log.debug("Fallo escribiendo en Redis", exc_info=True)
            _marcar_caida()


def _degradacion_reciente(ahora: float) -> bool:
    """¿Ha habido una caída de Redis dentro de la ventana del limitador?

    Pasada la ventana, cualquier intento anotado solo en memoria durante la caída
    ya habría caducado, así que la memoria no aporta nada y consultarla solo
    puede hacer daño (ver `bloqueado`).
    """
    return ahora - _ultima_degradacion < _ventana_segundos()


def bloqueado(clave: str) -> bool:
    """True si `clave` ha agotado los intentos permitidos en la ventana.

    Con Redis sano y sin caídas recientes, **Redis manda**. La memoria solo se
    consulta en OR mientras una degradación siga siendo relevante.

    Esa condición no es una optimización, es una corrección: `limpiar()` borra la
    clave en Redis —que es global— pero de la memoria **solo la del proceso que
    atiende la petición**, y el backend corre con `uvicorn --workers 2`. Con la
    memoria consultada siempre, un acceso correcto atendido por el worker B no
    limpiaba el contador que el worker A guardaba en su memoria, y la víctima
    seguía bloqueada: la política efectiva pasaba a ser «N intentos por worker
    que un acceso correcto no reinicia», más dura que la documentada y contraria
    a la garantía que fijó la Fase 10.

    Durante la ventana posterior a una caída sí se consulta, porque los intentos
    anotados mientras Redis no respondía nunca llegaron a Redis y regalárselos al
    atacante al recuperarse es justo el agujero que la escritura dual cierra.
    """
    ahora = _ahora()
    cliente = _redis()
    if cliente is None:
        # Sin Redis la memoria es el único almacén que hay.
        return _cuenta_en_memoria(clave, ahora) >= _maximo()
    if _degradacion_reciente(ahora) and _cuenta_en_memoria(clave, ahora) >= _maximo():
        return True
    try:
        nombre = _PREFIJO + clave
        cliente.zremrangebyscore(nombre, 0, ahora - _ventana_segundos())
        bloqueada = int(cliente.zcard(nombre)) >= _maximo()
        _marcar_operacion_correcta()
        return bloqueada
    except Exception:                                    # noqa: BLE001
        log.debug("Fallo leyendo de Redis", exc_info=True)
        _marcar_caida()
        return _cuenta_en_memoria(clave, ahora) >= _maximo()


def limpiar(clave: str) -> None:
    """Borra el contador de `clave`. Lo llama el login tras un acceso correcto."""
    cliente = _redis()
    if cliente is not None:
        try:
            cliente.delete(_PREFIJO + clave)
        except Exception:                                # noqa: BLE001
            log.debug("Fallo borrando en Redis", exc_info=True)
            _marcar_caida()
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
            log.debug("Fallo vaciando Redis", exc_info=True)
            _marcar_caida()
    with _cerrojo:
        _memoria.clear()

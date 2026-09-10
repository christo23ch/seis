"""Fase 11 · Bloque A — Salud por componente.

Tres sondas y no una, porque tienen tres audiencias con necesidades opuestas:

``GET /health`` — **liveness**. Vive en `app/api/routes.py` y no se toca: O(1) y
sin I/O. La plataforma de hosting lo consulta cada pocos segundos y por réplica;
si tocara la base de datos, una base lenta bastaría para que la plataforma matase
y reiniciase los procesos web, convirtiendo una degradación en una caída total.

``GET /health/listo`` — **readiness**, público. Comprueba de verdad la base de
datos y Redis, con un timeout corto tomado de configuración, y responde **503**
si algo falla, para que el balanceador retire esta réplica del reparto. Es
deliberadamente **mudo** sobre el motivo: el valor por componente es exactamente
``"ok"`` o ``"error"``, sin una sola palabra más. El texto de una excepción de
SQLAlchemy o de redis-py arrastra la cadena de conexión completa —usuario y
contraseña incluidos—, de modo que devolverlo publicaría las credenciales a
cualquiera capaz de consultar una URL pública. El detalle real se registra en el
log del servidor, que es del operador.

``GET /health/detalle`` — **diagnóstico**, solo superadministrador de plataforma.
Añade entorno, revisión de Alembic aplicada, versiones del conocimiento T2/T3 y
la latencia medida de cada sonda. Va autenticado porque esa información es huella
útil para un atacante: la revisión de migraciones y las versiones de reglas
identifican la build desplegada y, con ella, qué defectos conocidos le aplican.
Lo máximo que puede ver un anónimo es `estado` + `componentes`.

**Por qué `/health/detalle` responde 200 aunque haya un componente caído:** su
lector es una persona que está diagnosticando, no un balanceador que decide
enrutar. El veredicto viaja en el campo `estado`; devolver un 5xx solo
conseguiría que los clientes HTTP que abortan ante un error de servidor
escondieran justo el cuerpo que se ha ido a buscar. El contrato de máquina —el
que sí cambia de código de estado— es `/health/listo`.

**Alcance real del timeout (honestidad sobre lo que acota):** en Redis, los
`socket_connect_timeout`/`socket_timeout` acotan la sonda entera. En la base de
datos, `statement_timeout` acota la *consulta*, no el establecimiento de la
conexión TCP, que depende de los `connect_args` del motor (`app/core/db.py`) y es
configuración global de la aplicación, no de esta sonda. En SQLite no hay nada
que acotar: `SELECT 1` es una llamada en proceso.
"""
from __future__ import annotations

import logging
import time
from threading import Lock

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models
from app.api.deps import require_superadmin
from app.core import red
from app.core.config import entorno_normalizado, get_settings
from app.core.db import get_db
from app.services import conocimiento_service

log = logging.getLogger("seis.salud")

router = APIRouter(prefix="/health", tags=["salud"])

# Vocabulario cerrado de la respuesta pública. Que sean constantes y no literales
# sueltos es lo que hace evidente que NO existe un tercer valor con matices.
COMPONENTE_OK = "ok"
COMPONENTE_ERROR = "error"
ESTADO_OK = "ok"
ESTADO_DEGRADADO = "degradado"

DESCONOCIDA = "desconocida"

# Tabla de contabilidad interna de Alembic. Coincide con el `version_table` por
# defecto, que `alembic/env.py` no sobrescribe; si algún día lo hiciera, este
# nombre debe seguirlo.
TABLA_VERSION_ALEMBIC = "alembic_version"

# Único dialecto en el que se sabe acotar la consulta por sentencia.
DIALECTO_CON_STATEMENT_TIMEOUT = "postgresql"

CODIGO_NO_DISPONIBLE = 503


# ─────────────────────────── Utilidades internas ───────────────────────────

def _milisegundos_desde(inicio: float) -> float:
    return round((time.perf_counter() - inicio) * 1000, 2)


def _etiqueta(ok: bool) -> str:
    """Traduce el resultado de una sonda al vocabulario público (sin matices)."""
    return COMPONENTE_OK if ok else COMPONENTE_ERROR


def _rollback_silencioso(db: Session) -> None:
    """Revierte la sesión tras un fallo de sonda, sin propagar nada.

    En PostgreSQL, una sentencia fallida deja la transacción **abortada**: toda
    consulta posterior en esa misma sesión falla con `InFailedSqlTransaction`.
    Sin este rollback, un fallo al leer `alembic_version` arrastraría consigo la
    lectura de las versiones del conocimiento, y el diagnóstico culparía a tres
    cosas cuando solo falla una.
    """
    try:
        db.rollback()
    except Exception:                                    # noqa: BLE001 — nunca rompe
        log.debug("No se pudo revertir la sesión tras un fallo de sonda", exc_info=True)


def _aplicar_timeout_bd(db: Session, segundos: float) -> None:
    """Acota la duración de la consulta de sonda en PostgreSQL.

    `SET LOCAL` vive dentro de la transacción en curso y se descarta al cerrarla,
    así que no contamina la conexión que vuelve al pool. El valor se interpola en
    el texto porque PostgreSQL no admite parámetros ligados en `SET`; es seguro
    porque procede de la configuración y se fuerza a entero antes de escribirlo.
    """
    if db.get_bind().dialect.name != DIALECTO_CON_STATEMENT_TIMEOUT:
        return
    milisegundos = max(1, int(segundos * 1000))
    db.execute(text(f"SET LOCAL statement_timeout = {milisegundos}"))


# ─────────────────────────── Sondas por componente ───────────────────────────
#
# Dos funciones separadas y sustituibles a propósito: en la suite no hay Redis
# (`tests/conftest.py` no lo levanta), de modo que sin esta costura el caso «todo
# arriba» no sería comprobable y el resultado dependería de si la máquina que
# ejecuta los tests tiene por casualidad un Redis escuchando.

def _comprobar_bd(db: Session) -> tuple[bool, float]:
    """`SELECT 1` contra la base. Devuelve (correcto, milisegundos)."""
    inicio = time.perf_counter()
    try:
        _aplicar_timeout_bd(db, get_settings().health_timeout_segundos)
        db.execute(text("SELECT 1")).scalar_one()
        return True, _milisegundos_desde(inicio)
    except Exception as exc:                             # noqa: BLE001 — nunca rompe
        _rollback_silencioso(db)
        # El detalle va AQUÍ y solo aquí: el log del servidor es del operador,
        # la respuesta HTTP es de cualquiera.
        log.warning("Sonda de salud: la base de datos no responde (%s)",
                    type(exc).__name__, exc_info=True)
        return False, _milisegundos_desde(inicio)


def _comprobar_redis() -> tuple[bool, float]:
    """`PING` contra Redis con cliente propio. Devuelve (correcto, milisegundos).

    No reutiliza el cliente de `app/core/rate_limit.py` a propósito: aquel cachea
    «no hay Redis» de forma permanente para no reintentar la conexión en cada
    login, y una sonda que recordase el primer fallo jamás volvería a declararse
    sana cuando Redis se recuperase, que es justo lo que una sonda de readiness
    tiene que detectar.
    """
    inicio = time.perf_counter()
    cliente = None
    try:
        import redis as redis_lib

        timeout = get_settings().health_timeout_segundos
        cliente = redis_lib.Redis.from_url(get_settings().redis_url,
                                           socket_connect_timeout=timeout,
                                           socket_timeout=timeout)
        cliente.ping()
        return True, _milisegundos_desde(inicio)
    except Exception as exc:                             # noqa: BLE001 — nunca rompe
        log.warning("Sonda de salud: Redis no responde (%s)",
                    type(exc).__name__, exc_info=True)
        return False, _milisegundos_desde(inicio)
    finally:
        if cliente is not None:
            try:
                cliente.close()
            except Exception:                            # noqa: BLE001
                log.debug("No se pudo cerrar el cliente de la sonda de Redis",
                          exc_info=True)


# ─────────────────────────── Datos de diagnóstico ───────────────────────────

def _revision_alembic(db: Session) -> str:
    """Revisión realmente aplicada, leída de `alembic_version`.

    Se consulta la tabla en vez de importar el identificador del código porque lo
    que importa en producción es qué migración corrió **esa base**, no cuál cree
    el binario que debería haber corrido: la discrepancia entre ambas es
    exactamente el fallo que esta sonda debe hacer visible.

    Devuelve «desconocida» si la tabla no existe —esquema creado con
    `create_all`, como en la suite— en lugar de reventar: una sonda de
    diagnóstico que falla no diagnostica nada.
    """
    try:
        version = db.execute(
            text(f"SELECT version_num FROM {TABLA_VERSION_ALEMBIC}")).scalar()
    except Exception:                                    # noqa: BLE001 — nunca rompe
        _rollback_silencioso(db)
        log.info("No se pudo leer %s; se informa revisión desconocida",
                 TABLA_VERSION_ALEMBIC, exc_info=True)
        return DESCONOCIDA
    return str(version) if version else DESCONOCIDA


def _versiones_conocimiento(db: Session) -> tuple[str, str]:
    """Versiones vigentes de reglas (T2) y parámetros (T3), o «desconocida»."""
    try:
        _reglas, version_reglas = conocimiento_service.reglas_vigentes(db)
        version_parametros = conocimiento_service.parametros_vigentes(db).version
        return str(version_reglas), str(version_parametros)
    except Exception:                                    # noqa: BLE001 — nunca rompe
        _rollback_silencioso(db)
        log.warning("No se pudieron leer las versiones del conocimiento", exc_info=True)
        return DESCONOCIDA, DESCONOCIDA


# ─────────────────────────── Endpoints ───────────────────────────

@router.get("/listo")
def salud_listo(db: Session = Depends(get_db)):
    """Readiness pública: ¿puede esta réplica atender tráfico ahora mismo?

    200 con todo arriba; 503 si algún componente falla. El cuerpo no dice **por
    qué** falla, y no es una omisión: ver el encabezado del módulo.
    """
    bd_ok, redis_ok = _sondas_con_cache(db)
    componentes = {"bd": _etiqueta(bd_ok), "redis": _etiqueta(redis_ok)}
    if bd_ok and redis_ok:
        return {"estado": ESTADO_OK, "componentes": componentes}
    return JSONResponse(status_code=CODIGO_NO_DISPONIBLE,
                        content={"estado": ESTADO_DEGRADADO, "componentes": componentes})


# ───────────── Cota de trabajo de la sonda pública (Fase 16, M-2) ─────────────
#
# `/health/listo` es público y no autenticado, y cada llamada obligaba a un
# `SELECT 1` contra PostgreSQL y un `PING` a Redis: el amplificador más barato
# del sistema.
#
# LA CORRECCIÓN NO ES UN LÍMITE DE TASA, y la desviación respecto al informe es
# deliberada. Un 429 —o un 503— en una sonda de readiness lo lee el orquestador
# como «esta réplica no está lista», y como la configuración sería idéntica en
# todas, **sacaría de rotación a réplicas sanas**. El remedio habría sido peor
# que la enfermedad.
#
# Lo que se acota es el TRABAJO, no las peticiones: el resultado de las sondas se
# reutiliza durante un segundo. Diez mil peticiones por segundo pasan a costar
# una consulta, y el orquestador nunca recibe un código que no espera.
#
# QUÉ NO CUBRE (ADR-0014):
# - No limita el ancho de banda ni el coste de atender la petición HTTP en sí;
#   para eso hace falta el borde.
# - Un segundo de retardo en detectar una caída real. Con sondas cada 5-10 s es
#   ruido; si alguien baja el intervalo por debajo de un segundo, esta caché deja
#   de ser transparente y hay que revisar el valor.
# - La caché es POR PROCESO. Con varias réplicas cada una tiene la suya, que es
#   justamente lo que se quiere: cada réplica informa de su propio estado.

SEGUNDOS_DE_CACHE_SONDA = 1.0
_ultima_sonda: tuple[float, bool, bool] | None = None
_cerrojo_sonda = Lock()


def _reloj_sonda() -> float:
    """Aislado en una función a propósito, igual que `rate_limit._ahora`: los
    tests lo sustituyen para envejecer la caché y comprobar que CADUCA, sin
    dormir de verdad.

    Hizo falta porque una mutación sobrevivió: con la caché puesta a no caducar
    nunca, la suite entera seguía verde. Una caché eterna convierte una caída
    real de la base en un 200 permanente, que es peor que no tener caché.
    """
    return time.monotonic()


def _sondas_con_cache(db: Session) -> tuple[bool, bool]:
    """(bd_ok, redis_ok), reutilizando el resultado durante un segundo."""
    global _ultima_sonda
    ahora = _reloj_sonda()
    with _cerrojo_sonda:
        if _ultima_sonda is not None and ahora - _ultima_sonda[0] < SEGUNDOS_DE_CACHE_SONDA:
            return _ultima_sonda[1], _ultima_sonda[2]
    # Fuera del cerrojo: las sondas hacen E/S y no deben serializar peticiones.
    # El precio es que dos peticiones simultáneas pueden sondear las dos; es
    # aceptable y preferible a encolar a todo el mundo tras una consulta lenta.
    bd_ok, _ = _comprobar_bd(db)
    redis_ok, _ = _comprobar_redis()
    with _cerrojo_sonda:
        _ultima_sonda = (ahora, bd_ok, redis_ok)
    return bd_ok, redis_ok


def reiniciar_cache_sonda() -> None:
    """Solo para los tests: el estado es de proceso y se filtraría entre ellos."""
    global _ultima_sonda
    with _cerrojo_sonda:
        _ultima_sonda = None


def _diagnostico_de_red(peticion: Request) -> dict:
    """Par TCP, IP resuelta y política de proxies vigente.

    Cierra lo que el ADR-0006 dejó pendiente. Una política mal declarada —la
    cabecera equivocada, saltos que no coinciden con la topología— **no da
    ningún síntoma**: el sistema responde con normalidad y el límite por origen
    vuelve a ser un cupo global. Sin este apartado, eso solo se descubre cuando
    alguien ya ha eludido el limitador. Comparar `par_tcp` con `ip_resuelta` en
    una petición real es la comprobación que lo delata en un vistazo.

    No se vuelcan las cabeceras crudas: el diagnóstico no debe convertirse en un
    espejo de lo que envía quien llama.
    """
    politica = red.politica_actual()
    return {
        "par_tcp": peticion.client.host if peticion.client else red.IP_DESCONOCIDA,
        "ip_resuelta": red.ip_cliente(peticion),
        # A-2: sin esto, que este módulo dejara de resolver la IP no producía
        # ningún síntoma. `sin_resolver` cerca de 1 con la política activa
        # significa que la cabecera no está llegando y que los límites por
        # origen han vuelto a ser un cupo global compartido.
        "resolucion_ip": {
            "politica_activa": red.politica_actual().activa,
            "sin_resolver": round(red.proporcion_sin_resolver(), 4),
            "por_motivo": red.recuento_resoluciones(),
        },
        "politica_activa": politica.activa,
        "cabecera": politica.cabecera or None,
        "saltos": politica.saltos,
        "redes_de_confianza": len(politica.redes),
    }


@router.get("/detalle")
def salud_detalle(peticion: Request,
                  _admin: models.Usuario = Depends(require_superadmin),
                  db: Session = Depends(get_db)) -> dict:
    """Diagnóstico completo para el superadministrador de plataforma.

    Consecuencia buscada del orden: `_comprobar_bd` deja fijado el
    `statement_timeout` de la transacción, de modo que las lecturas de
    diagnóstico posteriores heredan ese techo y el endpoint entero queda acotado.
    Si alguna tardase más, se informa «desconocida» en vez de colgar la petición.
    """
    bd_ok, bd_ms = _comprobar_bd(db)
    redis_ok, redis_ms = _comprobar_redis()
    version_reglas, version_parametros = _versiones_conocimiento(db)
    return {
        "estado": ESTADO_OK if (bd_ok and redis_ok) else ESTADO_DEGRADADO,
        "componentes": {"bd": _etiqueta(bd_ok), "redis": _etiqueta(redis_ok)},
        "latencias_ms": {"bd": bd_ms, "redis": redis_ms},
        "entorno": entorno_normalizado(get_settings().seis_env),
        "revision_alembic": _revision_alembic(db),
        "version_reglas": version_reglas,
        "version_parametros": version_parametros,
        "red": _diagnostico_de_red(peticion),
    }

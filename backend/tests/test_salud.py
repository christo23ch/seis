"""Fase 11 · Bloque A — Sondas de salud por componente.

Se prueban tres endpoints con audiencias deliberadamente distintas:

- ``/health``          *liveness*: trivial y sin I/O. Lo consulta la plataforma de
                       hosting cada pocos segundos y por réplica; si tocara la
                       base, una base lenta haría que la plataforma matara y
                       reiniciara los procesos web, convirtiendo una degradación
                       en una caída total.
- ``/health/listo``    *readiness*: estado real de BD y Redis, público pero **mudo**
                       sobre el detalle del fallo.
- ``/health/detalle``  diagnóstico: solo superadministrador de plataforma, porque
                       la revisión de Alembic y las versiones del conocimiento son
                       huella útil para un atacante.

Las sondas se sustituyen por dobles en casi todos los casos. En la suite **no hay
Redis** (`conftest.py` no lo levanta), así que sin esa costura el caso «todo
arriba» no sería comprobable; peor aún, el resultado dependería de si la máquina
que ejecuta los tests tiene por casualidad un Redis escuchando en el puerto por
defecto, justo lo contrario del determinismo que exige P1.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from tests.conftest import token_headers

URL_VIVO = "/api/v1/health"
URL_LISTO = "/api/v1/health/listo"
URL_DETALLE = "/api/v1/health/detalle"

EMAIL_ANALISTA = "analista.salud@example.com"
PASSWORD_ANALISTA = "analista-salud-123"

# Cadena de conexión falsa, con la forma exacta que SQLAlchemy y redis-py incrustan
# en el texto de sus excepciones: usuario y contraseña incluidos. Ninguna de sus
# partes puede aparecer jamás en una respuesta HTTP pública.
DSN_FALSO = "postgresql://usuario:CONTRASEÑA_SECRETA@bd-interna.seis.local:5432/seis"
ERROR_BD_CON_DSN = OperationalError(
    f"(psycopg2.OperationalError) no se pudo conectar a {DSN_FALSO}",
    None,
    Exception("connection refused"),
)


# ─────────────────────────── Utilidades de test ───────────────────────────

def _simular_sondas(monkeypatch, *, bd_ok: bool = True, redis_ok: bool = True,
                    ms: float = 1.5) -> None:
    """Sustituye las dos sondas por dobles deterministas.

    Es la costura que hace testeable el caso «todo arriba» sin levantar Redis.
    """
    from app.api import salud

    monkeypatch.setattr(salud, "_comprobar_bd", lambda _db: (bd_ok, ms))
    monkeypatch.setattr(salud, "_comprobar_redis", lambda: (redis_ok, ms))


class _MotorFalso:
    """Doble mínimo de `Engine`: la sonda solo le pregunta el dialecto."""

    dialect = SimpleNamespace(name="postgresql")


class _SesionRota:
    """Sesión cuyo `execute` revienta con el mensaje típico de SQLAlchemy.

    Se declara dialecto `postgresql` a propósito: así el fallo se produce ya en el
    intento de acotar la consulta con `statement_timeout`, que es el primer punto
    del camino real donde una base caída se manifiesta.
    """

    def get_bind(self):
        return _MotorFalso()

    def execute(self, *_args, **_kwargs):
        raise ERROR_BD_CON_DSN

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


@pytest.fixture(scope="module")
def headers_analista(api) -> dict:
    """Cabecera de un usuario autenticado que NO es superadmin de plataforma."""
    from app.core.db import SessionLocal
    from app.services import usuario_service

    db = SessionLocal()
    try:
        if not usuario_service.obtener_por_email(db, EMAIL_ANALISTA):
            org = usuario_service.crear_organizacion(db, "Organización Salud")
            usuario_service.crear_usuario(db, EMAIL_ANALISTA, PASSWORD_ANALISTA,
                                          "Ana Salud", rol="analista",
                                          organizacion_id=org.id, rol_org="miembro",
                                          es_superadmin=False)
    finally:
        db.close()
    return token_headers(api, EMAIL_ANALISTA, PASSWORD_ANALISTA)


# ─────────────────────────── 1 · Liveness intacta ───────────────────────────

def test_health_sigue_siendo_liveness_y_no_toca_bd_ni_redis(api, monkeypatch):
    """`/health` debe responder aunque BD y Redis estén inservibles.

    Se sabotean las dos dependencias: abrir una sesión de base de datos o invocar
    una sonda desde este endpoint hace estallar el test. Es el guardarraíl que
    impide que alguien «mejore» la sonda de liveness añadiéndole I/O.
    """
    from app.api import salud
    from app.core import db as db_module

    def _sesion_prohibida(*_args, **_kwargs):
        raise AssertionError("/health abrió una sesión de base de datos")

    def _sonda_prohibida(*_args, **_kwargs):
        raise AssertionError("/health ejecutó una sonda de componente")

    monkeypatch.setattr(db_module, "SessionLocal", _sesion_prohibida)
    monkeypatch.setattr(salud, "_comprobar_bd", _sonda_prohibida)
    monkeypatch.setattr(salud, "_comprobar_redis", _sonda_prohibida)

    r = api.get(URL_VIVO)

    assert r.status_code == 200, r.text
    # Contrato literal: la plataforma de hosting consume este cuerpo.
    assert r.json() == {"status": "ok", "servicio": "seis-backend"}


# ─────────────────────────── 2-4 · Readiness ───────────────────────────

def test_listo_con_todos_los_componentes_arriba_responde_200(api, monkeypatch):
    _simular_sondas(monkeypatch, bd_ok=True, redis_ok=True)

    r = api.get(URL_LISTO)

    assert r.status_code == 200, r.text
    assert r.json() == {"estado": "ok", "componentes": {"bd": "ok", "redis": "ok"}}


def test_listo_con_redis_caido_responde_503_y_señala_solo_a_redis(api, monkeypatch):
    """Un componente caído degrada la respuesta sin contaminar el diagnóstico del otro."""
    _simular_sondas(monkeypatch, bd_ok=True, redis_ok=False)

    r = api.get(URL_LISTO)

    assert r.status_code == 503, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "degradado"
    assert cuerpo["componentes"]["redis"] == "error"
    assert cuerpo["componentes"]["bd"] == "ok"


def test_listo_con_bd_caida_responde_503(api, monkeypatch):
    _simular_sondas(monkeypatch, bd_ok=False, redis_ok=True)

    r = api.get(URL_LISTO)

    assert r.status_code == 503, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "degradado"
    assert cuerpo["componentes"]["bd"] == "error"
    assert cuerpo["componentes"]["redis"] == "ok"


# ─────────────── 5 · No filtrar credenciales en la respuesta ───────────────

def test_listo_no_filtra_la_cadena_de_conexion_ni_el_texto_de_la_excepcion(api):
    """Test negativo capital: el fallo se cuenta, nunca se explica.

    El texto de una excepción de SQLAlchemy o de redis-py suele arrastrar la
    cadena de conexión completa —con usuario y contraseña—. Como `/health/listo`
    es público y lo consultan monitores externos, cualquier detalle del fallo en
    el cuerpo sería una filtración de credenciales a Internet.

    Se ejercita la sonda REAL (no un doble) sustituyendo la sesión por una rota,
    para que el camino de manejo de errores que se prueba sea el de producción.
    """
    from app.core.db import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: _SesionRota()
    try:
        r = api.get(URL_LISTO)
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 503, r.text
    cuerpo = r.json()
    assert cuerpo["componentes"]["bd"] == "error"

    # El cuerpo serializado completo, tal y como viaja por el cable.
    serializado = r.text
    # «CONTRASEÑA_SECRETA» lleva un carácter no ASCII: si algún día el
    # serializador escapara a \uXXXX, la comprobación de la cadena entera dejaría
    # de detectar la fuga. Por eso se comprueba también el fragmento ASCII.
    for secreto in ("CONTRASEÑA_SECRETA", "SECRETA", "postgresql://",
                    "bd-interna.seis.local", DSN_FALSO, str(ERROR_BD_CON_DSN)):
        assert secreto not in serializado, f"La respuesta filtró «{secreto}»"

    # Contrato cerrado: exactamente estas claves y exactamente estos valores. Si
    # mañana alguien añade un campo «motivo» o «detalle», este test lo detiene.
    assert set(cuerpo) == {"estado", "componentes"}
    assert set(cuerpo["componentes"]) == {"bd", "redis"}
    assert set(cuerpo["componentes"].values()) <= {"ok", "error"}


# ─────────────────────────── 6-9 · Detalle autenticado ───────────────────────────

def test_detalle_sin_token_responde_401(api):
    r = api.get(URL_DETALLE)

    assert r.status_code == 401, r.text


def test_detalle_con_usuario_no_superadmin_responde_403(api, headers_analista, monkeypatch):
    """Estar autenticado no basta: el diagnóstico es gobierno de plataforma."""
    _simular_sondas(monkeypatch)

    r = api.get(URL_DETALLE, headers=headers_analista)

    assert r.status_code == 403, r.text


def test_detalle_con_superadmin_devuelve_entorno_revision_y_versiones(api, headers, monkeypatch):
    from app.core.config import ENTORNOS_SOPORTADOS

    _simular_sondas(monkeypatch, bd_ok=True, redis_ok=True, ms=4.2)

    r = api.get(URL_DETALLE, headers=headers)

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["componentes"] == {"bd": "ok", "redis": "ok"}
    # Qué entorno concreto se reporta se comprueba fijándolo, en el test de más
    # abajo; aquí solo se exige que sea uno de los soportados.
    assert cuerpo["entorno"] in ENTORNOS_SOPORTADOS
    assert isinstance(cuerpo["revision_alembic"], str) and cuerpo["revision_alembic"]
    assert isinstance(cuerpo["version_reglas"], str) and cuerpo["version_reglas"]
    assert isinstance(cuerpo["version_parametros"], str) and cuerpo["version_parametros"]
    assert cuerpo["latencias_ms"] == {"bd": 4.2, "redis": 4.2}


@pytest.mark.parametrize("configurado, esperado", [
    ("development", "development"),
    ("Development", "development"),
    ("  DEVELOPMENT  ", "development"),
    ("test", "test"),
    ("TEST", "test"),
])
def test_detalle_reporta_el_entorno_efectivo_normalizado(
        api, headers, monkeypatch, configurado, esperado):
    """El diagnóstico reporta el entorno EFECTIVO, ya normalizado.

    Antes esto afirmaba el literal «development», dando por hecho que la suite
    corre con SEIS_ENV sin definir. Eso es falso en la CI, que corre —y debe
    correr— con SEIS_ENV=test: el test fallaba por dar por supuesto el entorno,
    no por un defecto del código. Clavar «test» en su lugar solo habría movido
    el mismo error de sitio, y habría vuelto a romperse en la máquina de
    cualquiera que exportase otro valor.

    Fijar el valor aquí evita las dos trampas a la vez: no recalcula en el test
    la misma expresión que usa el endpoint —la tautología que el comentario
    original quería esquivar— y no depende del entorno ambiente. De paso
    ejercita la normalización (mayúsculas y espacios) que introduce esta misma
    fase, que era justo lo que el literal ocultaba.

    Solo se usan entornos no estrictos: fijar «production» o «staging» activaría
    la guardia de secretos fuertes del arranque, que es objeto de su propia
    batería en test_seguridad_arranque.py.
    """
    from app.core.config import get_settings

    _simular_sondas(monkeypatch, bd_ok=True, redis_ok=True, ms=4.2)
    monkeypatch.setenv("SEIS_ENV", configurado)
    get_settings.cache_clear()
    try:
        r = api.get(URL_DETALLE, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["entorno"] == esperado
    finally:
        get_settings.cache_clear()


def test_detalle_publica_la_politica_de_red_vigente(api, headers, monkeypatch):
    """El apartado que el ADR-0006 dejó pendiente y que el Bloque H cerró.

    Es el único instrumento para detectar en producción una política de proxies
    mal declarada, cuyo modo de fallo es **mudo**: el sistema responde con
    normalidad y el límite por origen vuelve a ser un cupo global. Comparar
    `par_tcp` con `ip_resuelta` en una petición real lo delata en un vistazo.
    """
    _simular_sondas(monkeypatch)

    cuerpo = api.get(URL_DETALLE, headers=headers).json()

    assert set(cuerpo["red"]) == {"par_tcp", "ip_resuelta", "politica_activa",
                                  "cabecera", "saltos", "redes_de_confianza",
                                  "resolucion_ip"}
    assert cuerpo["red"]["politica_activa"] is False      # sin proxies declarados
    assert cuerpo["red"]["par_tcp"] == cuerpo["red"]["ip_resuelta"]

    # Fase 16 (A-2). Comparar `par_tcp` con `ip_resuelta` delata la política mal
    # declarada en UNA petición; lo que no dice es si el problema es constante o
    # esporádico, y esa diferencia es la que distingue «el proxy nunca envía la
    # cabecera» de «alguien manda cabeceras raras». De ahí la proporción.
    resolucion = cuerpo["red"]["resolucion_ip"]
    assert set(resolucion) == {"politica_activa", "sin_resolver", "por_motivo"}
    assert 0.0 <= resolucion["sin_resolver"] <= 1.0
    assert isinstance(resolucion["por_motivo"], dict)


def test_detalle_no_vuelca_las_cabeceras_crudas(api, headers, monkeypatch):
    """El diagnóstico no debe convertirse en un espejo de lo que envía quien llama."""
    _simular_sondas(monkeypatch)

    r = api.get(URL_DETALLE, headers={**headers, "X-Forwarded-For": "6.6.6.6"})

    assert "6.6.6.6" not in r.text


def test_detalle_refleja_la_revision_real_de_la_tabla_alembic_version(api, headers, monkeypatch):
    """La revisión se lee de `alembic_version`, no de una constante del código.

    La suite crea el esquema con `create_all`, que **nunca** escribe esa tabla
    (CLAUDE.md §6.9), así que se siembra aquí y se retira al terminar para no
    dejar estado compartido a los demás tests.
    """
    from app.core.db import engine

    _simular_sondas(monkeypatch)
    with engine.begin() as con:
        con.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        con.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0006')"))
    try:
        r = api.get(URL_DETALLE, headers=headers)

        assert r.status_code == 200, r.text
        assert r.json()["revision_alembic"] == "0006"
    finally:
        with engine.begin() as con:
            con.execute(text("DROP TABLE alembic_version"))


def test_detalle_sin_tabla_alembic_no_rompe_y_declara_revision_desconocida(api, headers, monkeypatch):
    """Sin `alembic_version` (esquema creado con `create_all`) el endpoint informa,
    no revienta: una sonda de diagnóstico que falla no diagnostica nada."""
    _simular_sondas(monkeypatch)

    r = api.get(URL_DETALLE, headers=headers)

    assert r.status_code == 200, r.text
    assert r.json()["revision_alembic"] == "desconocida"


# ────────── 11-14 · Camino real de las sondas, no solo el de los dobles ──────────

def test_listo_con_la_bd_real_y_redis_simulado_responde_200(api, monkeypatch):
    """Ejercita `_comprobar_bd` DE VERDAD, contra la sesión SQLite de la fixture.

    El resto de los tests de readiness doblan las dos sondas, de modo que el
    camino feliz real —`SELECT 1`, `scalar_one()` y la rama SQLite de
    `_aplicar_timeout_bd`— no se ejecutaba en ninguna prueba: cambiar el SQL por
    uno inválido dejaba la suite entera verde con la readiness rota en
    producción. Aquí se dobla **solo Redis**, que es el componente que la suite
    no tiene; la base sí la tiene, y doblarla era regalar cobertura.
    """
    from app.api import salud

    monkeypatch.setattr(salud, "_comprobar_redis", lambda: (True, 1.0))

    r = api.get(URL_LISTO)

    assert r.status_code == 200, r.text
    assert r.json() == {"estado": "ok", "componentes": {"bd": "ok", "redis": "ok"}}


def test_listo_con_los_dos_componentes_caidos_los_marca_a_ambos(api, monkeypatch):
    """Cierra la matriz: (ok,ok), (ok,error), (error,ok) ya estaban; faltaba (error,error)."""
    _simular_sondas(monkeypatch, bd_ok=False, redis_ok=False)

    r = api.get(URL_LISTO)

    assert r.status_code == 503, r.text
    assert r.json() == {"estado": "degradado",
                        "componentes": {"bd": "error", "redis": "error"}}


def test_listo_no_filtra_la_url_de_redis_con_contrasena(api, monkeypatch):
    """La otra mitad del test capital de no-filtración.

    El test de fuga original solo saboteaba la base de datos. Pero en producción
    la **URL de Redis también lleva contraseña** —Upstash, Redis Cloud,
    ElastiCache con AUTH: justo el escenario PaaS al que apunta la Fase 11-B—, y
    en la suite `redis_url` no tiene credenciales, así que una regresión que
    filtrara el motivo por la rama de Redis pasaba desapercibida.

    El puerto 1 garantiza un rechazo de conexión inmediato: el test no espera.
    """
    from app.api import salud

    ajustes = SimpleNamespace(
        redis_url="redis://:CLAVE_REDIS_SECRETA@127.0.0.1:1/0",
        health_timeout_segundos=0.2)
    monkeypatch.setattr(salud, "get_settings", lambda: ajustes)

    r = api.get(URL_LISTO)

    assert r.status_code == 503, r.text
    assert r.json()["componentes"]["redis"] == "error"
    for secreto in ("CLAVE_REDIS_SECRETA", "redis://", "127.0.0.1:1"):
        assert secreto not in r.text, f"La respuesta filtró «{secreto}»"

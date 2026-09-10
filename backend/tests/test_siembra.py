"""Hueco de cobertura nº 1: la ORQUESTACIÓN de la siembra.

Las tres piezas —conocimiento, administrador, sesión— ya tenían tests. Lo que no
los tenía es el `main()` que las encadena, ni en `init_db` ni en `sembrar`. Y ese
hueco no es teórico: la mutación que lo aprovecha es envolver la siembra en
`if creado:`.

Por qué esa mutación sobrevivía a toda la suite: en `development` y `test`
`crear_esquema_si_procede()` devuelve True, así que `if creado:` no cambia nada y
todo sigue verde. En `staging` y `production` devuelve False —el ADR-0004 retiró
`create_all` de esos entornos— y la instalación arranca **sin reglas, sin
parámetros y sin administrador**. Es decir: el defecto solo aparece donde no hay
tests, y no se descubre hasta el despliegue.

De ahí la forma de este módulo. El test que importa no es el del entorno de
desarrollo, es `test_init_db_siembra_aunque_el_esquema_no_lo_cree_el`: fija que
la siembra ocurre **precisamente cuando `create_all` no corre**, que es el caso
que la mutación rompe y el único que se parece a producción.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Secretos que aguantan la validación estricta de `staging` (config.py). No son
# reales: son largos y sin parecido con ninguna plantilla, que es lo que se exige.
SECRETOS_ESTRICTOS = {
    "JWT_SECRET": "S7uP2rq-xK9vLm4Tz1Wc8YbNd6Fg0HjQ3aEoI5RtUvXyZpMk",
    "ADMIN_PASSWORD": "Xk4-Rq9tLm2Zv7Bn",
    "ADMIN_EMAIL": "admin@ejemplo-siembra.test",
    # El vacío aborta en entornos estrictos; el centinela declara «no hay proxy».
    "PROXIES_DE_CONFIANZA": "ninguno",
    # Fase 16 (A-1): la guardia de CORS también aborta en entorno estricto. Aquí
    # se declara el centinela porque estos tests siembran una base, no atienden a
    # ningún navegador.
    "SEIS_CORS_ORIGINS": "ninguno",
}


@pytest.fixture
def base_desechable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Reapunta `app.core.db` a un SQLite propio de este test.

    `init_db.main()` y `sembrar.main()` importan `SessionLocal` **dentro** de la
    función, así que se resuelve en la llamada y basta con sustituirlo en el
    módulo. Sin esto, los `main()` sembrarían en el fichero compartido con la
    fixture `api` y contaminarían a otros tests.
    """
    from app.core import db as modulo_db

    ruta = tmp_path / "siembra.db"
    motor = create_engine(f"sqlite:///{ruta.as_posix()}",
                          connect_args={"check_same_thread": False})
    sesiones = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(modulo_db, "engine", motor)
    monkeypatch.setattr(modulo_db, "SessionLocal", sesiones)
    yield sesiones
    motor.dispose()


@pytest.fixture(autouse=True)
def _limpiar_ajustes():
    """La configuración está cacheada: sin esto, el SEIS_ENV de un test se
    quedaría pegado al siguiente y a toda la suite."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _comprobar_conocimiento_completo(sesiones) -> None:
    """Lo que debe existir para que la instalación sirva de algo."""
    from app import models
    from scripts.sembrar import FUENTES

    db = sesiones()
    try:
        assert db.query(models.Regla).count() > 0, "sin reglas T2 el motor no evalúa nada"
        assert db.query(models.Parametro).count() > 0, "sin parámetros T3 no hay umbrales"
        assert db.query(models.PerfilInversion).count() > 0, "sin perfiles no hay análisis"
        assert db.query(models.FuenteSubasta).count() == len(FUENTES)

        admin = db.query(models.Usuario).one()
        assert admin.es_superadmin, "el administrador inicial debe poder gobernar T2/T3"
        assert admin.organizacion_id, "sin organización el admin no puede operar"
        assert db.query(models.Organizacion).count() == 1
    finally:
        db.close()


# ────────────────────────── init_db.main() ──────────────────────────

def test_init_db_deja_lista_una_base_vacia_en_desarrollo(
        base_desechable, monkeypatch: pytest.MonkeyPatch) -> None:
    """El caso cómodo: en `test` sí se crea el esquema y luego se siembra."""
    from app.core.config import get_settings
    from scripts import init_db

    monkeypatch.setenv("SEIS_ENV", "test")
    get_settings.cache_clear()

    init_db.main()

    _comprobar_conocimiento_completo(base_desechable)


def test_init_db_siembra_aunque_el_esquema_no_lo_cree_el(
        base_desechable, monkeypatch: pytest.MonkeyPatch) -> None:
    """EL TEST QUE IMPORTA.

    En `staging` el ADR-0004 impide que `init_db` cree el esquema: lo gobierna
    Alembic. Aquí eso se simula creando las tablas antes de llamar. La siembra
    **debe ocurrir igual**, porque es el único camino por el que una instalación
    nueva obtiene reglas, parámetros y administrador.

    Es exactamente el caso que rompe la mutación `if creado:`, y el único que se
    parece a un despliegue real.
    """
    from app.core import db as modulo_db
    from app.core.config import get_settings
    from scripts import init_db

    monkeypatch.setenv("SEIS_ENV", "staging")
    for clave, valor in SECRETOS_ESTRICTOS.items():
        monkeypatch.setenv(clave, valor)
    get_settings.cache_clear()

    # El esquema lo pone Alembic en producción; aquí, el propio test.
    modulo_db.Base.metadata.create_all(modulo_db.engine)

    assert init_db.crear_esquema_si_procede() is False, (
        "premisa del test: en staging `init_db` NO debe crear el esquema. Si esto "
        "falla, el ADR-0004 se ha roto y lo que sigue ya no prueba lo que dice.")

    init_db.main()

    _comprobar_conocimiento_completo(base_desechable)


def test_init_db_dos_veces_no_duplica_ni_crea_un_segundo_admin(
        base_desechable, monkeypatch: pytest.MonkeyPatch) -> None:
    """La siembra corre en cada arranque, así que la idempotencia no es un lujo.

    Y el administrador es el caso delicado: crear un segundo superadministrador
    en una instalación en marcha sería un alta de privilegios por reinicio.
    """
    from app import models
    from app.core.config import get_settings
    from scripts import init_db

    monkeypatch.setenv("SEIS_ENV", "test")
    get_settings.cache_clear()

    init_db.main()
    db = base_desechable()
    try:
        reglas = db.query(models.Regla).count()
    finally:
        db.close()

    init_db.main()

    db = base_desechable()
    try:
        assert db.query(models.Regla).count() == reglas
        assert db.query(models.Usuario).count() == 1
        assert db.query(models.Organizacion).count() == 1
    finally:
        db.close()


# ────────────────────────── sembrar.main() ──────────────────────────

def test_sembrar_main_siembra_sobre_una_base_ya_migrada(
        base_desechable, monkeypatch: pytest.MonkeyPatch) -> None:
    """`scripts.sembrar` duplica la orquestación de `init_db` y se invoca a mano
    (`python -m scripts.sembrar`) contra una base ya migrada. Que nunca cree el
    esquema es su razón de ser, así que aquí lo pone el test."""
    from app.core import db as modulo_db
    from app.core.config import get_settings
    from scripts import sembrar

    monkeypatch.setenv("SEIS_ENV", "staging")
    for clave, valor in SECRETOS_ESTRICTOS.items():
        monkeypatch.setenv(clave, valor)
    get_settings.cache_clear()

    modulo_db.Base.metadata.create_all(modulo_db.engine)

    sembrar.main()

    _comprobar_conocimiento_completo(base_desechable)


def test_sembrar_main_no_crea_el_esquema(
        base_desechable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si `sembrar` creara tablas por su cuenta reintroduciría el antipatrón que
    el ADR-0004 retiró, solo que por otra puerta. Debe fallar contra una base sin
    esquema, no arreglárselo."""
    from app.core.config import get_settings
    from scripts import sembrar

    monkeypatch.setenv("SEIS_ENV", "staging")
    for clave, valor in SECRETOS_ESTRICTOS.items():
        monkeypatch.setenv(clave, valor)
    get_settings.cache_clear()

    with pytest.raises(Exception):
        sembrar.main()

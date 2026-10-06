"""La suite trabaja sobre su propia base desechable, nunca sobre `seis_dev.db`.

Contrato de `tests/conftest.py`: `DATABASE_URL` se fija antes de importar la app,
en un directorio temporal del sistema fuera del repositorio, y una guarda aborta
la sesión si el engine EFECTIVO apunta a otra base. Antes de esto, la fixture
`api` hacía `drop_all` y `os.remove("seis_dev.db")` sobre la base de desarrollo
(incidente del 2026-09-24).

Nada de aquí exige que `backend/seis_dev.db` exista: en CI no existe, y entonces
lo que se comprueba es que la suite no la crea.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import (ADMIN, DIR_BD_TESTS, RAIZ_REPO, RUTA_BD_DESARROLLO, RUTA_BD_TESTS,
                            problema_de_aislamiento)


def _ruta_efectiva() -> Path:
    from app.core.db import engine

    return Path(engine.url.database).resolve()


def _estado(ruta: Path) -> tuple[int, int] | None:
    """Tamaño y mtime, o `None` si no existe."""
    if not ruta.exists():
        return None
    s = ruta.stat()
    return (s.st_size, s.st_mtime_ns)


def test_la_url_efectiva_no_es_seis_dev_db():
    assert _ruta_efectiva().name != "seis_dev.db"
    assert _ruta_efectiva() != RUTA_BD_DESARROLLO.resolve()


def test_la_base_efectiva_es_la_desechable_dentro_del_temporal():
    ruta = _ruta_efectiva()
    assert ruta == RUTA_BD_TESTS.resolve()
    ruta.relative_to(DIR_BD_TESTS)                       # lanza si no cuelga de él
    with pytest.raises(ValueError):
        DIR_BD_TESTS.relative_to(RAIZ_REPO.resolve())    # el temporal NO está en el repo


def test_la_configuracion_y_el_engine_coinciden():
    """El engine se creó DESPUÉS de fijar la URL: los dos dicen lo mismo."""
    from app.core.config import get_settings
    from app.core.db import engine

    assert get_settings().database_url == f"sqlite:///{RUTA_BD_TESTS.as_posix()}"
    assert Path(engine.url.database).resolve() == RUTA_BD_TESTS.resolve()


@pytest.mark.parametrize("url", [
    f"sqlite:///{RUTA_BD_DESARROLLO.as_posix()}",        # la base de desarrollo, absoluta
    "sqlite:///./seis_dev.db",                           # el valor por defecto de Settings
    f"sqlite:///{(DIR_BD_TESTS / 'seis_dev.db').as_posix()}",   # ese nombre, aunque esté en el temporal
    f"sqlite:///{(DIR_BD_TESTS / 'otra.db').as_posix()}",       # dentro del temporal pero no la esperada
    f"sqlite:///{(RAIZ_REPO / 'backend' / 'tests.db').as_posix()}",  # fuera del temporal
    "postgresql+psycopg2://u:p@localhost:5432/seis_test",           # otro motor
])
def test_la_guarda_rechaza_cualquier_otra_base(url):
    assert problema_de_aislamiento(url, RUTA_BD_TESTS, DIR_BD_TESTS, RAIZ_REPO) is not None


def test_la_guarda_acepta_la_base_de_la_suite():
    from app.core.db import engine

    assert problema_de_aislamiento(engine.url, RUTA_BD_TESTS, DIR_BD_TESTS, RAIZ_REPO) is None


def test_la_guarda_rechaza_un_temporal_dentro_del_repositorio():
    dentro = RAIZ_REPO / "backend" / "tmp-suite"
    url = f"sqlite:///{(dentro / 'tests.db').as_posix()}"
    assert problema_de_aislamiento(url, dentro / "tests.db", dentro, RAIZ_REPO) is not None


def test_seis_dev_db_intacta_al_usar_la_fixture_api(api):
    """Las operaciones destructivas de `api` (`drop_all` + `create_all`) y una
    petición real no alteran `backend/seis_dev.db`, exista o no."""
    from app.core.db import Base, engine

    # También la raíz del repo: con la URL relativa de antes, lanzar pytest desde
    # la raíz creaba y borraba un `seis_dev.db` ahí.
    en_la_raiz = RAIZ_REPO / "seis_dev.db"
    antes = (_estado(RUTA_BD_DESARROLLO), _estado(en_la_raiz))

    assert api.post("/api/v1/auth/login", data=ADMIN).status_code == 200
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)      # deja el esquema como lo espera el teardown de `api`

    assert (_estado(RUTA_BD_DESARROLLO), _estado(en_la_raiz)) == antes

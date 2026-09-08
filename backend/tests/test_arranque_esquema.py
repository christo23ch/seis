"""Fase 11 · Bloque E — `create_all` fuera de la ruta de producción.

`CLAUDE.md` §6.9 prohíbe derivar la DDL de los modelos dentro de
`alembic/versions/`. Hasta la Fase 11 ese mismo antipatrón vivía en la ruta de
arranque —`init_db.py` llamaba a `create_all` y `docker-compose.yml` lo
encadenaba **después** de `alembic upgrade head`—, donde hace exactamente el
daño que la prohibición busca evitar: si un modelo declara algo que ninguna
migración crea, se crea en silencio en producción y la deriva de esquema que el
test T4 existe para detectar queda enmascarada.
"""
from __future__ import annotations

import pytest

from scripts import init_db


@pytest.mark.parametrize("entorno", ["staging", "production"])
def test_create_all_no_se_ejecuta_en_los_entornos_estrictos(entorno, monkeypatch):
    """Test capital del bloque.

    Se sabotea `create_all` para que estalle si alguien lo invoca: es la única
    forma de afirmar que **no se llama**, en vez de afirmar sobre un valor de
    retorno que un refactor podría dejar mintiendo.
    """
    from app.core import db as db_module
    from app.core.config import get_settings

    def _prohibido(*_a, **_k):
        raise AssertionError(
            "create_all se ejecutó en un entorno estricto: el esquema debe "
            "gobernarlo Alembic, o la deriva quedará enmascarada en producción")

    monkeypatch.setattr(db_module.Base.metadata, "create_all", _prohibido)
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("SEIS_ENV", entorno)
        monkeypatch.setenv("JWT_SECRET", "kJ7pQz2Xv9RtNw4bYm6HcE8sLdA3fUgW1oPiZxTq")
        monkeypatch.setenv("ADMIN_PASSWORD", "Zq8Rm2Vt6Yx4Bn7Kw")
        # Los entornos estrictos exigen pronunciarse sobre los proxies (Bloque H).
        monkeypatch.setenv("PROXIES_DE_CONFIANZA", "ninguno")

        assert init_db.crear_esquema_si_procede() is False
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("entorno", ["development", "test"])
def test_create_all_sigue_ejecutandose_en_desarrollo(entorno, monkeypatch):
    """En desarrollo no hay migraciones que respetar y crear el esquema al vuelo
    es lo cómodo y lo inocuo. Quitarlo aquí rompería el flujo local y la suite."""
    from app.core import db as db_module
    from app.core.config import get_settings

    llamadas = {"n": 0}
    monkeypatch.setattr(db_module.Base.metadata, "create_all",
                        lambda *_a, **_k: llamadas.__setitem__("n", llamadas["n"] + 1))
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("SEIS_ENV", entorno)

        assert init_db.crear_esquema_si_procede() is True
        assert llamadas["n"] == 1
    finally:
        get_settings.cache_clear()


def test_la_siembra_no_depende_de_crear_el_esquema(api):
    """La siembra es idempotente y corre en TODOS los entornos.

    Sacarla del arranque reintroduciría por otra puerta el defecto que originó la
    Fase 9.5: que `docker compose up` no baste para tener un sistema en pie. Una
    instalación sin reglas, sin parámetros y sin administrador es inservible
    aunque el esquema esté perfecto.
    """
    from app import models
    from app.core.db import SessionLocal
    from scripts.sembrar import sembrar_conocimiento

    db = SessionLocal()
    try:
        sembrar_conocimiento(db)
        antes = db.query(models.FuenteSubasta).count()
        assert antes > 0

        sembrar_conocimiento(db)      # segunda pasada: no debe duplicar nada

        assert db.query(models.FuenteSubasta).count() == antes
        assert db.query(models.PerfilInversion).count() > 0
        assert db.query(models.Regla).count() > 0
    finally:
        db.close()


def test_sembrar_admin_no_crea_un_segundo_administrador(api):
    """Solo siembra si NO hay ningún usuario: es lo que impide que un arranque
    cree un superadministrador en una instalación ya en marcha."""
    from app import models
    from app.core.db import SessionLocal
    from scripts.sembrar import sembrar_admin

    db = SessionLocal()
    try:
        antes = db.query(models.Usuario).count()
        assert antes > 0, "la fixture siembra el admin"

        assert sembrar_admin(db) is False
        assert db.query(models.Usuario).count() == antes
    finally:
        db.close()

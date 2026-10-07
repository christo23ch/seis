"""Fase 5J-3 — la siembra sincroniza las reglas T2 del catálogo YAML con la tabla `regla`.

Antes solo se copiaba el catálogo con la tabla vacía y, como `reglas_vigentes` ignora el YAML
en cuanto hay filas, una versión nueva de una regla no llegaba nunca a una base ya sembrada
(comprobado sobre la base de desarrollo: SEM-EJEC-01 seguía en 2026.07 tras la 5J-2b).
Decisión del responsable: sincronizar al sembrar, sin pisar nunca una versión creada por la API.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app import models
from app.core.db import SessionLocal
from app.engine.pipeline import cargar_catalogo
from app.services import conocimiento_service as cs
from scripts.sembrar import sincronizar_reglas

CODIGO = "SEM-EJEC-01"


@pytest.fixture
def db(api):
    sesion = SessionLocal()
    sesion.query(models.Regla).delete()
    sesion.query(models.Auditoria).filter(models.Auditoria.entidad == "regla").delete()
    sesion.commit()
    try:
        yield sesion
    finally:
        sesion.rollback()
        sesion.query(models.Regla).delete()
        sesion.commit()
        sincronizar_reglas(sesion)
        sesion.commit()
        sesion.close()


def _del_catalogo(codigo: str) -> dict:
    return next(r for r in cargar_catalogo()[0] if r["codigo"] == codigo)


def _vigentes(db, codigo: str) -> list[models.Regla]:
    return (db.query(models.Regla)
              .filter(models.Regla.codigo == codigo, models.Regla.vigente_hasta.is_(None)).all())


def _sembrada_antigua(db, codigo: str = CODIGO, version: str = "2026.07", autor: str | None = None):
    definicion = {**_del_catalogo(codigo), "version": version}
    definicion["efecto"] = {"condicion": "texto antiguo"}
    db.add(models.Regla(codigo=codigo, version=version, categoria=definicion["categoria"],
                        prioridad=definicion["prioridad"], definicion=definicion, autor=autor))
    db.commit()


def test_una_base_vacia_recibe_todo_el_catalogo(db):
    cambios = sincronizar_reglas(db)
    db.commit()
    assert len(cambios) == len(cargar_catalogo()[0])
    assert {r.codigo for r in db.query(models.Regla).all()} == {r["codigo"] for r in cargar_catalogo()[0]}


def test_una_version_sembrada_antigua_se_cierra_y_entra_la_del_catalogo(db):
    _sembrada_antigua(db)
    cambios = sincronizar_reglas(db)
    db.commit()
    nueva = _del_catalogo(CODIGO)["version"]
    assert f"{CODIGO} 2026.07 → {nueva}" in cambios
    [vigente] = _vigentes(db, CODIGO)
    assert vigente.version == nueva and vigente.autor is None
    assert vigente.definicion["efecto"] == _del_catalogo(CODIGO)["efecto"]
    antigua = db.get(models.Regla, (CODIGO, "2026.07"))
    assert antigua.vigente_hasta is not None
    audit = db.query(models.Auditoria).filter_by(entidad="regla", entidad_id=CODIGO).one()
    assert audit.accion == "sincronizar_catalogo" and audit.delta == {"version_anterior": "2026.07", "version": nueva}
    # El motor de la API lee ya la versión del catálogo.
    defs, _ = cs.reglas_vigentes(db)
    assert next(d for d in defs if d["codigo"] == CODIGO)["version"] == nueva


def test_una_version_creada_por_la_api_no_se_pisa(db):
    _sembrada_antigua(db, version="2026.10.07.1", autor="admin@seis.local")
    sincronizar_reglas(db)
    db.commit()
    [vigente] = _vigentes(db, CODIGO)
    assert (vigente.version, vigente.autor) == ("2026.10.07.1", "admin@seis.local")
    assert vigente.definicion["efecto"] == {"condicion": "texto antiguo"}


def test_es_idempotente(db):
    sincronizar_reglas(db)
    db.commit()
    total = db.query(models.Regla).count()
    assert sincronizar_reglas(db) == []
    db.commit()
    assert db.query(models.Regla).count() == total


def test_una_version_del_catalogo_ya_cerrada_no_se_resucita(db):
    nueva = _del_catalogo(CODIGO)["version"]
    sincronizar_reglas(db)
    db.commit()
    fila = db.get(models.Regla, (CODIGO, nueva))
    fila.vigente_hasta = datetime.now(timezone.utc)
    db.commit()
    sincronizar_reglas(db)
    db.commit()
    assert _vigentes(db, CODIGO) == []

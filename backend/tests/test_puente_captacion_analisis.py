"""Fase 1 — Puente captación → análisis.

Antes de esta fase, `analisis_service.crear_analisis` creaba SIEMPRE su propia
`Subasta` (`app/services/analisis_service.py`), sin relación alguna con las que
la Fase 17-A ya captura y persiste (`app/services/ingesta_service.py`). Una
subasta ya captada no se podía analizar sin re-teclearla entera
(`docs/ESTADO_ACTUAL.md`, «Frente abierto de PRODUCTO»).

Estos tests demuestran que, pasando el id de una subasta ya captada como
`subasta_id`, el análisis la reutiliza en vez de duplicarla, que un id
inexistente no deja residuos, y que el alta manual (sin `subasta_id`) sigue
funcionando exactamente igual que antes.
"""
from __future__ import annotations

import json

from tests.conftest import entrada_base


def _captar_subasta(api, headers, identificador: str, valor: float = 150000.0) -> str:
    """Da de alta una subasta por el camino real de captación (Fase 17-A)."""
    r = api.post("/api/v1/subastas", json={
        "fuente_codigo": "judicial_boe",
        "identificador_externo": identificador,
        "valor_subasta": valor,
        "deposito_pct": 0.05,
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _conteos(db) -> dict[str, int]:
    from app import models
    return {
        "subastas": db.query(models.Subasta).count(),
        "analisis": db.query(models.Analisis).count(),
        "activos": db.query(models.Activo).count(),
    }


def test_analisis_desde_subasta_existente_reutiliza_la_fila(api, headers):
    """Analizar una subasta captada no crea una segunda Subasta, y el Activo
    resultante queda ligado a la fila original mediante `subasta_id`."""
    from app.core.db import SessionLocal

    subasta_id = _captar_subasta(api, headers, "PUENTE-REUTILIZA")

    db = SessionLocal()
    try:
        antes = _conteos(db)
    finally:
        db.close()

    payload = json.loads(entrada_base().model_dump_json())
    r = api.post(f"/api/v1/analisis?subasta_id={subasta_id}", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    analisis_id = r.json()["id"]

    db = SessionLocal()
    try:
        despues = _conteos(db)
        assert despues["subastas"] == antes["subastas"], "no debe crear una segunda Subasta"
        assert despues["analisis"] == antes["analisis"] + 1
        assert despues["activos"] == antes["activos"] + 1

        from app import models
        analisis = db.get(models.Analisis, analisis_id)
        activo = db.get(models.Activo, analisis.activo_id)
        assert activo.subasta_id == subasta_id
    finally:
        db.close()


def test_subasta_id_inexistente_da_404_y_no_deja_residuos(api, headers):
    """Un id que no existe no crea ni Subasta, ni Activo, ni Analisis parcial."""
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        antes = _conteos(db)
    finally:
        db.close()

    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis?subasta_id=no-existe-123", json=payload, headers=headers)
    assert r.status_code == 404, r.text

    db = SessionLocal()
    try:
        assert _conteos(db) == antes, "un 404 no debe dejar ningún registro parcial"
    finally:
        db.close()


def test_analisis_manual_sin_subasta_id_sigue_funcionando(api, headers):
    """Regresión: el comportamiento sin `subasta_id` no cambia."""
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        antes = _conteos(db)
    finally:
        db.close()

    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["resultado"]["decision"]["semaforo"] == "amarillo"

    db = SessionLocal()
    try:
        despues = _conteos(db)
        assert despues["subastas"] == antes["subastas"] + 1, "el alta manual sigue creando su propia Subasta"
        assert despues["analisis"] == antes["analisis"] + 1
        assert despues["activos"] == antes["activos"] + 1
    finally:
        db.close()


def test_dos_analisis_desde_la_misma_subasta_no_la_duplican(api, headers):
    """Reanalizar la misma subasta (p. ej. con otro perfil) sigue sin duplicarla:
    cada análisis crea su propio Activo, pero comparten la misma Subasta."""
    from app.core.db import SessionLocal

    subasta_id = _captar_subasta(api, headers, "PUENTE-DOBLE")
    payload = json.loads(entrada_base().model_dump_json())

    r1 = api.post(f"/api/v1/analisis?subasta_id={subasta_id}", json=payload, headers=headers)
    assert r1.status_code == 200, r1.text
    r2 = api.post(f"/api/v1/analisis?subasta_id={subasta_id}", json=payload, headers=headers)
    assert r2.status_code == 200, r2.text
    assert r1.json()["id"] != r2.json()["id"]

    db = SessionLocal()
    try:
        from app import models
        assert db.query(models.Subasta).filter(models.Subasta.id == subasta_id).count() == 1
        activos = db.query(models.Activo).filter(models.Activo.subasta_id == subasta_id).all()
        assert len(activos) == 2
    finally:
        db.close()

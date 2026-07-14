"""Informe PDF (§12) y análisis asíncrono vía Celery (modo eager en tests)."""
import json

from tests.conftest import entrada_base


def test_informe_pdf(api, headers):
    payload = json.loads(entrada_base().model_dump_json())
    analisis_id = api.post("/api/v1/analisis", json=payload, headers=headers).json()["id"]
    r = api.get(f"/api/v1/analisis/{analisis_id}/informe.pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 4000                           # documento real, no cabecera vacía


def test_analisis_async_eager(api, headers):
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis/async", json=payload, headers=headers)
    assert r.status_code == 202
    body = r.json()
    assert body["estado"] == "SUCCESS"
    assert body["resultado"]["semaforo"] == "amarillo"
    # la tarea persistió de verdad: el análisis aparece en el listado
    listado = api.get("/api/v1/analisis", headers=headers).json()
    assert any(a["id"] == body["resultado"]["id"] for a in listado)

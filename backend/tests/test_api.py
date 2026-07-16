"""API end-to-end autenticada: persistir → listar → detalle → informe → checklist."""
import json

from tests.conftest import entrada_base


def test_health_publico(api):
    r = api.get("/api/v1/health")
    # "degraded" es válido si Redis no está disponible en el entorno de test (Fase 11):
    # la BD (el componente crítico) sigue "ok" y el status HTTP se mantiene en 200.
    assert r.status_code == 200 and r.json()["status"] in ("ok", "degraded")
    assert r.json()["componentes"]["db"]["status"] == "ok"


def test_sin_token_401(api):
    assert api.get("/api/v1/analisis").status_code == 401
    assert api.post("/api/v1/analisis/simular", json={}).status_code == 401


def test_opciones_y_perfiles(api, headers):
    r = api.get("/api/v1/opciones", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "vivienda" in data["tipologias"] and "flip_integral" in data["perfiles"]
    r2 = api.get("/api/v1/perfiles", headers=headers)
    assert "rentista" in r2.json()


def test_flujo_completo_analisis(api, headers):
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    analisis_id = body["id"]
    assert body["resultado"]["decision"]["semaforo"] == "amarillo"

    r = api.get("/api/v1/analisis", headers=headers)
    assert any(a["id"] == analisis_id for a in r.json())

    r = api.get(f"/api/v1/analisis/{analisis_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["resultado"]["decision"]["ico"] >= 60

    r = api.get(f"/api/v1/analisis/{analisis_id}/informe", headers=headers)
    assert r.status_code == 200 and "AMARILLO" in r.text

    r = api.get(f"/api/v1/analisis/{analisis_id}/checklist", headers=headers)
    assert r.status_code == 200 and len(r.json()) >= 25


def test_simular_no_persiste(api, headers):
    payload = json.loads(entrada_base().model_dump_json())
    antes = len(api.get("/api/v1/analisis", headers=headers).json())
    r = api.post("/api/v1/analisis/simular", json=payload, headers=headers)
    assert r.status_code == 200
    assert "decision" in r.json()
    assert len(api.get("/api/v1/analisis", headers=headers).json()) == antes


def test_404(api, headers):
    assert api.get("/api/v1/analisis/no-existe", headers=headers).status_code == 404

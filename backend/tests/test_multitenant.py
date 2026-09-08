"""Fase 9 — Aislamiento por organización (multi-tenancy).

Siembra dos organizaciones (A y B), cada una con propietario y analista, y verifica:
- ningún endpoint de análisis filtra datos entre organizaciones (acceso ajeno = 404);
- el CRUD de conocimiento T2/T3 exige superadmin de plataforma;
- la gestión de miembros la ejerce solo el propietario, y nunca sobre otra organización.
"""
import json

import pytest

from tests.conftest import ADMIN, entrada_base, token_headers


@pytest.fixture(scope="module")
def escenario(api):
    """Crea org A y org B con sus usuarios, usando al superadmin bootstrap.

    Devuelve un dict con cabeceras y datos útiles para los tests.
    """
    admin_h = token_headers(api, ADMIN["username"], ADMIN["password"])

    def nueva_org(nombre: str, prop_email: str, ana_email: str) -> dict:
        # El superadmin crea la organización creando a su propietario (con org nueva),
        # pero POST /auth/usuarios exige una organizacion_id existente; sembramos la
        # organización directamente por servicio para tener su id.
        from app.core.db import SessionLocal
        from app.services import usuario_service
        db = SessionLocal()
        try:
            org = usuario_service.crear_organizacion(db, nombre)
            usuario_service.crear_usuario(db, prop_email, "propietario123", "Prop",
                                          rol="admin", organizacion_id=org.id,
                                          rol_org="propietario", es_superadmin=False)
            usuario_service.crear_usuario(db, ana_email, "analista123", "Ana",
                                          rol="analista", organizacion_id=org.id,
                                          rol_org="miembro", es_superadmin=False)
            return {"org_id": org.id, "prop_email": prop_email, "ana_email": ana_email}
        finally:
            db.close()

    a = nueva_org("Org A", "propA@example.com", "anaA@example.com")
    b = nueva_org("Org B", "propB@example.com", "anaB@example.com")
    return {
        "admin_h": admin_h,
        "a": a, "b": b,
        "propA_h": token_headers(api, a["prop_email"], "propietario123"),
        "anaA_h": token_headers(api, a["ana_email"], "analista123"),
        "propB_h": token_headers(api, b["prop_email"], "propietario123"),
        "anaB_h": token_headers(api, b["ana_email"], "analista123"),
    }


def _crear_analisis(api, headers) -> str:
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ─────────────── Aislamiento de análisis (acceso ajeno = 404) ───────────────

def test_listado_no_cruza_organizaciones(api, escenario):
    id_a = _crear_analisis(api, escenario["anaA_h"])
    # B no ve el análisis de A en su listado
    listado_b = api.get("/api/v1/analisis", headers=escenario["anaB_h"]).json()
    assert all(x["id"] != id_a for x in listado_b)
    # A sí lo ve
    listado_a = api.get("/api/v1/analisis", headers=escenario["anaA_h"]).json()
    assert any(x["id"] == id_a for x in listado_a)


@pytest.mark.parametrize("sufijo", ["", "/informe", "/informe.pdf", "/checklist"])
def test_acceso_directo_a_analisis_ajeno_es_404(api, escenario, sufijo):
    id_a = _crear_analisis(api, escenario["anaA_h"])
    # B intenta acceder por ID directo a un recurso de A → 404 (no 403)
    r = api.get(f"/api/v1/analisis/{id_a}{sufijo}", headers=escenario["anaB_h"])
    assert r.status_code == 404, r.text
    # El propietario de A sí accede
    r_ok = api.get(f"/api/v1/analisis/{id_a}{sufijo}", headers=escenario["propA_h"])
    assert r_ok.status_code == 200, r_ok.text


# ─────────────── Permisos sobre el conocimiento T2/T3 (solo superadmin) ───────────────

def test_conocimiento_requiere_superadmin(api, escenario):
    cuerpo_param = {"clave": "tenencia.mensual_defecto", "valor": 300}
    # miembro (analista) → 403
    assert api.put("/api/v1/parametros", headers=escenario["anaA_h"],
                   json=cuerpo_param).status_code == 403
    # propietario (no superadmin) → 403
    assert api.put("/api/v1/parametros", headers=escenario["propA_h"],
                   json=cuerpo_param).status_code == 403
    # superadmin de plataforma → pasa el gate (200; el valor es una clave válida)
    assert api.put("/api/v1/parametros", headers=escenario["admin_h"],
                   json=cuerpo_param).status_code == 200


# ─────────────── Gestión de miembros ───────────────

def test_propietario_crea_miembro_en_su_org(api, escenario):
    r = api.post("/api/v1/organizacion/miembros", headers=escenario["propA_h"],
                 json={"email": "nuevoa@example.com", "password": "temp12345",
                       "nombre": "Nuevo", "rol": "analista"})
    assert r.status_code == 201, r.text
    # el nuevo miembro aparece en la organización de A…
    org = api.get("/api/v1/organizacion", headers=escenario["propA_h"]).json()
    assert any(m["email"] == "nuevoa@example.com" for m in org["miembros"])
    # …y NO en la de B
    org_b = api.get("/api/v1/organizacion", headers=escenario["propB_h"]).json()
    assert all(m["email"] != "nuevoa@example.com" for m in org_b["miembros"])


def test_miembro_no_gestiona_miembros(api, escenario):
    r = api.post("/api/v1/organizacion/miembros", headers=escenario["anaA_h"],
                 json={"email": "x@example.com", "password": "temp12345", "rol": "lector"})
    assert r.status_code == 403


def test_propietario_no_toca_miembro_de_otra_org(api, escenario):
    # crea un miembro en B y obtén su id
    api.post("/api/v1/organizacion/miembros", headers=escenario["propB_h"],
             json={"email": "objetivob@example.com", "password": "temp12345", "rol": "lector"})
    org_b = api.get("/api/v1/organizacion", headers=escenario["propB_h"]).json()
    id_b = next(m["id"] for m in org_b["miembros"] if m["email"] == "objetivob@example.com")
    # el propietario de A intenta desactivarlo → 404 (no revela su existencia)
    r = api.patch(f"/api/v1/organizacion/miembros/{id_b}", headers=escenario["propA_h"],
                  json={"activo": False})
    assert r.status_code == 404, r.text


def test_propietario_activa_desactiva_miembro_propio(api, escenario):
    api.post("/api/v1/organizacion/miembros", headers=escenario["propA_h"],
             json={"email": "togglable@example.com", "password": "temp12345", "rol": "lector"})
    org = api.get("/api/v1/organizacion", headers=escenario["propA_h"]).json()
    mid = next(m["id"] for m in org["miembros"] if m["email"] == "togglable@example.com")
    r = api.patch(f"/api/v1/organizacion/miembros/{mid}", headers=escenario["propA_h"],
                  json={"activo": False})
    assert r.status_code == 200 and r.json()["activo"] is False
    # el miembro desactivado no puede iniciar sesión
    login = api.post("/api/v1/auth/login",
                     data={"username": "togglable@example.com", "password": "temp12345"})
    assert login.status_code == 401


# ─────────────── Aislamiento del estado de tareas (GET /tareas/{id}) ───────────────

def _fingir_tarea_exitosa(monkeypatch, analisis_id: str, semaforo: str = "amarillo"):
    """Sustituye AsyncResult por una tarea SUCCESS que apunta a `analisis_id`.

    En modo eager el resultado no queda en ningún backend, así que consultarlo por
    HTTP devolvería PENDING y no ejercitaría la comprobación de propiedad. Fingir
    la tarea es lo que permite probar la fuga real: quien conoce un `tarea_id`
    ajeno obtenía el id del análisis y su semáforo.
    """
    class TareaFingida:
        status = "SUCCESS"
        result = {"id": analisis_id, "semaforo": semaforo}

        def successful(self) -> bool:
            return True

        def failed(self) -> bool:
            return False

    from app.tasks import celery_app
    monkeypatch.setattr(celery_app.celery, "AsyncResult", lambda _id: TareaFingida())


def test_estado_de_tarea_ajena_es_404(api, escenario, monkeypatch):
    """B conoce el id de una tarea de A: no puede leer su resultado."""
    id_a = _crear_analisis(api, escenario["anaA_h"])
    _fingir_tarea_exitosa(monkeypatch, id_a)

    r = api.get("/api/v1/tareas/cualquier-uuid", headers=escenario["anaB_h"])
    assert r.status_code == 404, r.text
    # Y no se filtra ni el id del análisis ni el semáforo en el cuerpo del error.
    assert id_a not in r.text
    assert "amarillo" not in r.text


def test_estado_de_tarea_propia_se_entrega(api, escenario, monkeypatch):
    """Regresión: el dueño sigue recibiendo su resultado (no se rompe el sondeo)."""
    id_a = _crear_analisis(api, escenario["anaA_h"])
    _fingir_tarea_exitosa(monkeypatch, id_a)

    r = api.get("/api/v1/tareas/cualquier-uuid", headers=escenario["anaA_h"])
    assert r.status_code == 200, r.text
    assert r.json()["resultado"]["id"] == id_a


def test_tarea_fallida_no_propaga_el_texto_de_la_excepcion(api, escenario, monkeypatch):
    class TareaFallida:
        status = "FAILURE"
        result = RuntimeError("fuga: subasta de la organización A en la calle Secreta 1")

        def successful(self) -> bool:
            return False

        def failed(self) -> bool:
            return True

    from app.tasks import celery_app
    monkeypatch.setattr(celery_app.celery, "AsyncResult", lambda _id: TareaFallida())

    r = api.get("/api/v1/tareas/cualquier-uuid", headers=escenario["anaB_h"])
    assert r.status_code == 200
    assert "Secreta" not in r.text and "fuga" not in r.text


# ─────────────── El filtro por tenant es fail-closed ───────────────

def test_sin_organizacion_no_se_ve_ningun_analisis(api, escenario):
    """Un usuario con `organizacion_id` NULL no puede ver los análisis de nadie.

    La columna es nullable, así que este estado es representable. Antes el filtro
    era *fail-open*: sin tenant devolvía TODOS los análisis de TODAS las
    organizaciones. Debe devolver cero.
    """
    id_a = _crear_analisis(api, escenario["anaA_h"])

    from app.core.db import SessionLocal
    from app.services import usuario_service
    db = SessionLocal()
    try:
        usuario_service.crear_usuario(db, "huerfano@example.com", "huerfano123",
                                      "Huérfano", rol="analista", organizacion_id=None)
    finally:
        db.close()

    h = token_headers(api, "huerfano@example.com", "huerfano123")
    assert api.get("/api/v1/analisis", headers=h).json() == []
    assert api.get(f"/api/v1/analisis/{id_a}", headers=h).status_code == 404


def test_servicio_sin_tenant_no_devuelve_nada():
    """Mismo invariante, comprobado directamente sobre la capa de servicio."""
    from app.core.db import SessionLocal
    from app.services import analisis_service
    db = SessionLocal()
    try:
        assert analisis_service.listar_analisis(db, organizacion_id=None) == []
        assert analisis_service.obtener_analisis(db, "cualquiera", organizacion_id=None) is None
    finally:
        db.close()

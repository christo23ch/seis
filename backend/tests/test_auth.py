"""Autenticación JWT y control de roles."""
import json

from tests.conftest import ADMIN, entrada_base


def test_login_ok_y_me(api, headers):
    r = api.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200 and r.json()["rol"] == "admin"


def test_login_incorrecto(api):
    r = api.post("/api/v1/auth/login", data={"username": ADMIN["username"],
                                             "password": "mal"})
    assert r.status_code == 401


def test_token_invalido(api):
    r = api.get("/api/v1/auth/me", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 401


def test_roles_lector_no_escribe(api, headers):
    r = api.post("/api/v1/auth/usuarios", headers=headers,
                 json={"email": "lector@example.com", "password": "1234",
                       "nombre": "Lector", "rol": "lector"})
    assert r.status_code == 201
    tok = api.post("/api/v1/auth/login", data={"username": "lector@example.com",
                                               "password": "1234"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    # puede leer…
    assert api.get("/api/v1/analisis", headers=h).status_code == 200
    # …pero no crear análisis ni tocar conocimiento
    payload = json.loads(entrada_base().model_dump_json())
    assert api.post("/api/v1/analisis/simular", json=payload, headers=h).status_code == 403
    assert api.put("/api/v1/parametros", headers=h,
                   json={"clave": "tenencia.mensual_defecto", "valor": 300}).status_code == 403


def test_solo_admin_crea_usuarios(api, headers):
    tok = api.post("/api/v1/auth/login", data={"username": "lector@example.com",
                                               "password": "1234"}).json()["access_token"]
    r = api.post("/api/v1/auth/usuarios",
                 headers={"Authorization": f"Bearer {tok}"},
                 json={"email": "x@example.com", "password": "1", "rol": "analista"})
    assert r.status_code == 403

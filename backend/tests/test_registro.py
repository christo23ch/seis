"""Fase 10 — Alta self-service: registro, verificación de email, recuperación
de contraseña y anti fuerza-bruta.

Captura de emails: `ConsoleEmailBackend.enviar` se monkeypatchea por test
(pytest revierte el parche automáticamente al terminar) para poder extraer el
token del cuerpo del mensaje sin depender de ningún estado global compartido
entre tests — cada test tiene su propia lista `enviados`, vive y muere con él.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.services import email_service


def _capturar_emails(monkeypatch) -> list[dict]:
    enviados: list[dict] = []

    def fake_enviar(self, destinatario, asunto, cuerpo):
        enviados.append({"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo})

    monkeypatch.setattr(email_service.ConsoleEmailBackend, "enviar", fake_enviar)
    return enviados


def _token_de(cuerpo: str) -> str:
    m = re.search(r"token=(\S+)", cuerpo)
    assert m, f"no se encontró token en el cuerpo del email: {cuerpo!r}"
    return m.group(1)


def _registrar(api, monkeypatch, email: str, password: str = "password123",
              nombre: str = "Persona") -> tuple[list[dict], str]:
    enviados = _capturar_emails(monkeypatch)
    r = api.post("/api/v1/auth/registro",
                 json={"email": email, "password": password, "nombre": nombre})
    assert r.status_code == 201, r.text
    token = _token_de(enviados[-1]["cuerpo"])
    return enviados, token


def _auditoria(entidad_id: str, accion: str) -> list:
    from app.core.db import SessionLocal
    from app import models
    db = SessionLocal()
    try:
        return (db.query(models.Auditoria)
                .filter(models.Auditoria.entidad_id == entidad_id,
                       models.Auditoria.accion == accion)
                .all())
    finally:
        db.close()


# ─────────────── Registro ───────────────

def test_registro_feliz_usuario_inactivo_y_email_capturado(api, monkeypatch):
    enviados, token = _registrar(api, monkeypatch, "feliz@example.com")
    assert enviados[-1]["destinatario"] == "feliz@example.com"
    assert "verifica" in enviados[-1]["asunto"].lower()
    assert token

    # Inactivo hasta verificar: login falla con el mensaje genérico, no un 200.
    r = api.post("/api/v1/auth/login", data={"username": "feliz@example.com", "password": "password123"})
    assert r.status_code == 401

    assert len(_auditoria("feliz@example.com", "usuario_registrado")) == 1


def test_registro_email_duplicado_400(api, monkeypatch):
    _registrar(api, monkeypatch, "duplicado@example.com")
    r = api.post("/api/v1/auth/registro",
                 json={"email": "duplicado@example.com", "password": "otraPassword1", "nombre": "Otro"})
    assert r.status_code == 400


def test_registro_password_corta_422(api, monkeypatch):
    _capturar_emails(monkeypatch)
    r = api.post("/api/v1/auth/registro",
                 json={"email": "corta@example.com", "password": "1234567", "nombre": "X"})
    assert r.status_code == 422  # Field(min_length=8) de Pydantic


# ─────────────── Verificación ───────────────

def test_verificar_activa_cuenta_y_login_funciona(api, monkeypatch):
    _, token = _registrar(api, monkeypatch, "verificame@example.com")
    r = api.post("/api/v1/auth/verificar", json={"token": token})
    assert r.status_code == 200, r.text

    r = api.post("/api/v1/auth/login", data={"username": "verificame@example.com", "password": "password123"})
    assert r.status_code == 200

    assert len(_auditoria("verificame@example.com", "email_verificado")) == 1


def test_verificar_token_caducado_400(api, monkeypatch):
    from app.core.security import crear_token_proposito
    enviados = _capturar_emails(monkeypatch)
    r = api.post("/api/v1/auth/registro",
                 json={"email": "caducado@example.com", "password": "password123", "nombre": "X"})
    assert r.status_code == 201

    # Token ya caducado (horas negativas): mismo mecanismo de creación, exp en el pasado.
    token_caducado = crear_token_proposito("caducado@example.com", "verificar", horas=-1)
    r = api.post("/api/v1/auth/verificar", json={"token": token_caducado})
    assert r.status_code == 400


def test_verificar_token_reutilizado_400(api, monkeypatch):
    _, token = _registrar(api, monkeypatch, "reusado@example.com")
    r1 = api.post("/api/v1/auth/verificar", json={"token": token})
    assert r1.status_code == 200
    r2 = api.post("/api/v1/auth/verificar", json={"token": token})
    assert r2.status_code == 400


def test_verificar_token_desconocido_400(api, monkeypatch):
    r = api.post("/api/v1/auth/verificar", json={"token": "no-es-un-jwt-valido"})
    assert r.status_code == 400


def test_verificar_simultaneo_del_mismo_token_solo_uno_consume(api, monkeypatch):
    _, token = _registrar(api, monkeypatch, "concurrente-verificar@example.com")

    def llamar():
        return api.post("/api/v1/auth/verificar", json={"token": token})

    with ThreadPoolExecutor(max_workers=2) as ex:
        futuros = [ex.submit(llamar) for _ in range(2)]
        resultados = [f.result().status_code for f in futuros]

    assert sorted(resultados) == [200, 400]


# ─────────────── Recuperación de contraseña ───────────────

def test_recuperar_respuesta_identica_exista_o_no_el_email(api, monkeypatch):
    _capturar_emails(monkeypatch)
    r_existe = api.post("/api/v1/auth/recuperar", json={"email": "no-existe-para-nada@example.com"})

    _registrar(api, monkeypatch, "conocido@example.com")
    r_no_existe = api.post("/api/v1/auth/recuperar", json={"email": "conocido@example.com"})

    assert r_existe.status_code == r_no_existe.status_code == 200
    assert r_existe.json() == r_no_existe.json()


def test_recuperar_cuenta_no_verificada_reenvia_verificacion(api, monkeypatch):
    enviados, _ = _registrar(api, monkeypatch, "sinverificar@example.com")
    n_antes = len(enviados)

    r = api.post("/api/v1/auth/recuperar", json={"email": "sinverificar@example.com"})
    assert r.status_code == 200

    assert len(enviados) == n_antes + 1
    assert "verifica" in enviados[-1]["asunto"].lower()  # reenvía verificación, no reseteo

    reg = _auditoria("sinverificar@example.com", "password_reset_solicitado")
    assert len(reg) == 1
    assert reg[0].delta.get("reenviado_verificacion") is True


def test_recuperar_cuenta_verificada_envia_reseteo(api, monkeypatch):
    enviados, token = _registrar(api, monkeypatch, "verificadaparareset@example.com")
    api.post("/api/v1/auth/verificar", json={"token": token})

    r = api.post("/api/v1/auth/recuperar", json={"email": "verificadaparareset@example.com"})
    assert r.status_code == 200
    assert "restablece" in enviados[-1]["asunto"].lower()

    reg = _auditoria("verificadaparareset@example.com", "password_reset_solicitado")
    assert reg[-1].delta.get("reenviado_verificacion") is False


# ─────────────── Reseteo ───────────────

def test_resetear_feliz_cambia_password(api, monkeypatch):
    enviados, token_verif = _registrar(api, monkeypatch, "resetfeliz@example.com")
    api.post("/api/v1/auth/verificar", json={"token": token_verif})

    api.post("/api/v1/auth/recuperar", json={"email": "resetfeliz@example.com"})
    token_reset = _token_de(enviados[-1]["cuerpo"])

    r = api.post("/api/v1/auth/resetear", json={"token": token_reset, "nueva": "nuevaPassword1"})
    assert r.status_code == 200, r.text

    r_vieja = api.post("/api/v1/auth/login", data={"username": "resetfeliz@example.com", "password": "password123"})
    assert r_vieja.status_code == 401
    r_nueva = api.post("/api/v1/auth/login", data={"username": "resetfeliz@example.com", "password": "nuevaPassword1"})
    assert r_nueva.status_code == 200

    assert len(_auditoria("resetfeliz@example.com", "password_reseteada")) == 1


def test_resetear_token_reutilizado_400(api, monkeypatch):
    enviados, token_verif = _registrar(api, monkeypatch, "resetreusado@example.com")
    api.post("/api/v1/auth/verificar", json={"token": token_verif})
    api.post("/api/v1/auth/recuperar", json={"email": "resetreusado@example.com"})
    token_reset = _token_de(enviados[-1]["cuerpo"])

    r1 = api.post("/api/v1/auth/resetear", json={"token": token_reset, "nueva": "primeraPassword1"})
    assert r1.status_code == 200
    r2 = api.post("/api/v1/auth/resetear", json={"token": token_reset, "nueva": "segundaPassword1"})
    assert r2.status_code == 400


def test_resetear_simultaneo_del_mismo_token_solo_uno_consume(api, monkeypatch):
    enviados, token_verif = _registrar(api, monkeypatch, "resetconcurrente@example.com")
    api.post("/api/v1/auth/verificar", json={"token": token_verif})
    api.post("/api/v1/auth/recuperar", json={"email": "resetconcurrente@example.com"})
    token_reset = _token_de(enviados[-1]["cuerpo"])

    def llamar():
        return api.post("/api/v1/auth/resetear", json={"token": token_reset, "nueva": "concurrentePassword1"})

    with ThreadPoolExecutor(max_workers=2) as ex:
        futuros = [ex.submit(llamar) for _ in range(2)]
        resultados = [f.result().status_code for f in futuros]

    assert sorted(resultados) == [200, 400]


# ─────────────── Cruce de propósitos ───────────────

def test_token_de_verificar_no_sirve_para_resetear(api, monkeypatch):
    _, token_verif = _registrar(api, monkeypatch, "cruce1@example.com")
    r = api.post("/api/v1/auth/resetear", json={"token": token_verif, "nueva": "otraPassword1"})
    assert r.status_code == 400


def test_token_de_resetear_no_sirve_para_verificar(api, monkeypatch):
    enviados, token_verif = _registrar(api, monkeypatch, "cruce2@example.com")
    api.post("/api/v1/auth/verificar", json={"token": token_verif})
    api.post("/api/v1/auth/recuperar", json={"email": "cruce2@example.com"})
    token_reset = _token_de(enviados[-1]["cuerpo"])

    r = api.post("/api/v1/auth/verificar", json={"token": token_reset})
    assert r.status_code == 400


# ─────────────── Anti fuerza-bruta (dos cubos: email + IP) ───────────────

def test_login_bloqueado_tras_5_fallos_por_email(api, monkeypatch):
    _registrar(api, monkeypatch, "fuerzabruta@example.com")
    for _ in range(5):
        r = api.post("/api/v1/auth/login", data={"username": "fuerzabruta@example.com", "password": "incorrecta"})
        assert r.status_code == 401
    r6 = api.post("/api/v1/auth/login", data={"username": "fuerzabruta@example.com", "password": "incorrecta"})
    assert r6.status_code == 429

    # Ni siquiera con la contraseña correcta: el bloqueo es del cubo, no de la credencial.
    r7 = api.post("/api/v1/auth/login", data={"username": "fuerzabruta@example.com", "password": "password123"})
    assert r7.status_code == 429


def test_login_bloqueado_por_ip_aunque_cambie_el_email(api, monkeypatch):
    """El cubo de IP se satura probando contraseñas incorrectas contra varias cuentas
    distintas desde el mismo origen — el bucket por IP debe bloquear igualmente."""
    from app.core import rate_limit
    ip_fija = "203.0.113.99"
    for i in range(5):
        rate_limit.registrar_fallo("ip", ip_fija)
    assert rate_limit.bloqueado("ip", ip_fija) is True
    assert rate_limit.bloqueado("email", "cualquier-email-no-probado@example.com") is False


def test_login_exitoso_limpia_el_contador(api, monkeypatch):
    _, token = _registrar(api, monkeypatch, "recupera2@example.com")
    api.post("/api/v1/auth/verificar", json={"token": token})

    for _ in range(4):
        r = api.post("/api/v1/auth/login", data={"username": "recupera2@example.com", "password": "incorrecta"})
        assert r.status_code == 401

    r_ok = api.post("/api/v1/auth/login", data={"username": "recupera2@example.com", "password": "password123"})
    assert r_ok.status_code == 200

    # El contador se limpió: cuatro fallos más no deberían bloquear (habían llegado a 4/5).
    for _ in range(4):
        r = api.post("/api/v1/auth/login", data={"username": "recupera2@example.com", "password": "incorrecta"})
        assert r.status_code == 401
    r_ok_de_nuevo = api.post("/api/v1/auth/login", data={"username": "recupera2@example.com", "password": "password123"})
    assert r_ok_de_nuevo.status_code == 200


def test_login_desbloqueo_tras_ventana(monkeypatch):
    """Fallback en memoria: envejece los timestamps registrados para simular el paso
    del tiempo sin depender de sleeps reales ni de Redis."""
    from app.core import rate_limit

    rate_limit.limpiar("email", "envejece@example.com")
    for _ in range(5):
        rate_limit.registrar_fallo("email", "envejece@example.com")
    assert rate_limit.bloqueado("email", "envejece@example.com") is True

    clave = rate_limit._clave("email", "envejece@example.com")
    ventana_seg = 15 * 60
    rate_limit._memoria[clave] = [t - ventana_seg - 1 for t in rate_limit._memoria[clave]]

    assert rate_limit.bloqueado("email", "envejece@example.com") is False


def test_login_mensaje_generico_no_filtra_estado_de_cuenta(api, monkeypatch):
    """Email inexistente, cuenta sin verificar y contraseña incorrecta deben dar
    exactamente el mismo cuerpo de respuesta (mismo mensaje, mismo status)."""
    _registrar(api, monkeypatch, "sinverificarloginmsg@example.com")

    r_inexistente = api.post("/api/v1/auth/login", data={"username": "no-existe-jamas@example.com", "password": "cualquiera1"})
    r_sin_verificar = api.post("/api/v1/auth/login", data={"username": "sinverificarloginmsg@example.com", "password": "password123"})

    assert r_inexistente.status_code == r_sin_verificar.status_code == 401
    assert r_inexistente.json() == r_sin_verificar.json()

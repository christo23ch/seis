"""Fase 12 — Notificaciones multicanal y scoring exprés.

Cubre: scoring determinista y P4, matcher con score_min, código Telegram
(generación/caducidad/un solo uso), digest que agrupa, baja firmada, alertas
privadas por usuario (404) y que sin proveedor configurado nada rompe.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security import crear_token_proposito
from app.engine.params.store import cargar_defaults
from app.engine.scoring_expres import puntuar_subasta

from .conftest import token_headers


# ── Scoring exprés (puro, sin API) ──────────────────────────────────────────

def _datos_subasta(**overrides) -> dict:
    base = dict(fuente_codigo="judicial_boe", valor_subasta=100000,
                valor_referencia=200000, subastas_desiertas_previas=1,
                fecha_cierre=(datetime.now(timezone.utc) + timedelta(hours=300)).isoformat(),
                tiene_descripcion=True, tiene_superficie=True,
                tiene_ubicacion=True, tiene_fotos=True)
    base.update(overrides)
    return base


def test_scoring_determinista():
    params = cargar_defaults()
    datos = _datos_subasta()
    ahora = datetime.now(timezone.utc)
    r1, r2 = puntuar_subasta(datos, params, ahora), puntuar_subasta(datos, params, ahora)
    assert r1 == r2                                     # P1: mismo input ⇒ mismo output
    assert 0 <= r1["score"] <= 100
    assert r1["version_parametros"] == params.version


def test_scoring_determinista_independiente_del_reloj_de_pared():
    """Cierre Fase 12 (P0.3): el MISMO snapshot (datos + `ahora` explícito) debe
    puntuar igual sin importar en qué instante REAL se ejecute la función — antes
    del arreglo, `puntuar_subasta` leía `datetime.now()` internamente y el mismo
    registro puntuaba distinto según el día en que se evaluara (67/66/63/60,
    verificado empíricamente durante la revisión de H1-adyacentes)."""
    import time

    params = cargar_defaults()
    # fecha_cierre FIJA, en el pasado respecto al "ahora" de captación simulado:
    # el registro es inmutable, solo cambia el instante REAL en que este test corre.
    ahora_congelado = datetime(2026, 8, 1, tzinfo=timezone.utc)
    datos = _datos_subasta(fecha_cierre=datetime(2026, 8, 8, tzinfo=timezone.utc).isoformat())

    r1 = puntuar_subasta(datos, params, ahora_congelado)
    time.sleep(1.2)                                     # el reloj de pared SÍ avanza aquí
    r2 = puntuar_subasta(datos, params, ahora_congelado)  # pero `ahora` que se pasa NO cambia
    assert r1 == r2
    assert r1["desglose"]["plazo"] == pytest.approx(62.5, abs=0.1)  # (168-48)/(240-48)*100


def test_scoring_ausencia_de_datos_penaliza():
    params = cargar_defaults()
    ahora = datetime.now(timezone.utc)
    completo = puntuar_subasta(_datos_subasta(), params, ahora)
    sin_datos = puntuar_subasta({"valor_subasta": 100000, "fuente_codigo": "judicial_boe"},
                                params, ahora)
    assert sin_datos["score"] < completo["score"]       # P4
    assert sin_datos["desglose"]["descuento"] == 0      # sin referencia ⇒ 0, nunca optimista
    assert sin_datos["desglose"]["plazo"] == 0          # sin fecha de cierre ⇒ 0


def test_scoring_pesos_t3_editables():
    params = cargar_defaults()
    solo_fuente = params.con_overrides({"scoring_expres.pesos": {
        "descuento": 0, "fuente": 100, "desiertas": 0, "informacion": 0, "plazo": 0}})
    r = puntuar_subasta(_datos_subasta(), solo_fuente, datetime.now(timezone.utc))
    assert r["score"] == 70                             # atractivo judicial_boe de la tabla


# ── Matcher de alertas con score_min (API) ──────────────────────────────────

CAPTADA = dict(fuente_codigo="judicial_boe", valor_subasta=100000,
               valor_referencia=200000, subastas_desiertas_previas=1,
               tiene_descripcion=True, tiene_superficie=True,
               tiene_ubicacion=True, tiene_fotos=True)


def test_matcher_score_min(api, headers):
    r = api.post("/api/v1/alertas", headers=headers,
                 json={"nombre": "Chollos BOE", "criterios": {"score_min": 40}})
    assert r.status_code == 201, r.text
    alerta_exigente = api.post("/api/v1/alertas", headers=headers,
                               json={"nombre": "Imposible", "criterios": {"score_min": 101}})
    assert alerta_exigente.status_code == 201

    r = api.post("/api/v1/subastas", headers=headers,
                 json={**CAPTADA,
                       "fecha_cierre": (datetime.now(timezone.utc)
                                        + timedelta(hours=300)).isoformat()})
    assert r.status_code == 201, r.text
    subasta = r.json()
    assert subasta["score"] is not None and subasta["score"] >= 40
    # Solo casa la alerta alcanzable, no la de score_min=101
    assert subasta["alertas_disparadas"] == 1


def test_listado_subastas_filtra_por_score_min(api, headers):
    r = api.get("/api/v1/subastas?score_min=101", headers=headers)
    assert r.status_code == 200
    assert r.json() == []
    r = api.get("/api/v1/subastas?score_min=0", headers=headers)
    assert len(r.json()) >= 1


# ── Aislamiento del matcher entre organizaciones (cierre Fase 12, P0.2 — H1) ─

def test_matcher_aislamiento_entre_organizaciones(api, dos_organizaciones):
    """H1: un analista de la org A capta una subasta que casaría con alertas de
    ambas organizaciones; solo debe dispararse la de SU propia organización.
    La subasta sigue siendo visible para B por GET /subastas (catálogo compartido);
    lo que se acota es el efecto privado (la notificación), no el dato."""
    a_h, b_h = dos_organizaciones["a_h"], dos_organizaciones["b_h"]

    criterios_amplios = {"nombre": "Cualquier BOE", "criterios": {"fuente": "judicial_boe"}}
    alerta_a = api.post("/api/v1/alertas", headers=a_h, json=criterios_amplios).json()
    alerta_b = api.post("/api/v1/alertas", headers=b_h, json=criterios_amplios).json()

    r = api.post("/api/v1/subastas", headers=a_h,
                 json={**CAPTADA, "identificador_externo": "aislamiento-001",
                       "fecha_cierre": (datetime.now(timezone.utc)
                                        + timedelta(hours=300)).isoformat()})
    assert r.status_code == 201, r.text
    subasta_id = r.json()["id"]
    # Solo la alerta de la org A (la del captador) debe dispararse.
    assert r.json()["alertas_disparadas"] == 1

    from app.core.db import SessionLocal
    from app import models
    db = SessionLocal()
    try:
        notifs = (db.query(models.Notificacion)
                  .filter(models.Notificacion.alerta_id.in_([alerta_a["id"], alerta_b["id"]]))
                  .all())
        alertas_notificadas = {n.alerta_id for n in notifs}
        assert alerta_a["id"] in alertas_notificadas
        assert alerta_b["id"] not in alertas_notificadas   # H1: B no debe recibir nada
    finally:
        db.close()

    # El dato sigue siendo compartido: B puede seguir consultando la subasta.
    listado_b = api.get("/api/v1/subastas", headers=b_h).json()
    assert any(s["id"] == subasta_id for s in listado_b)


def test_matcher_regresion_intra_organizacion(api, dos_organizaciones):
    """Regresión: dentro de la MISMA organización el matching sigue funcionando
    exactamente igual que antes del scoping por tenant (P0.2 no debe estrechar
    el matching intra-org, solo acotar el cruce entre organizaciones).

    No se asume una cifra exacta de `alertas_disparadas`: la fixture de módulo
    ya dejó activa una alerta amplia de B en el test anterior, así que lo único
    relevante para esta regresión es que LA ALERTA PROPIA de este test también
    dispare, no cuántas más lo hagan."""
    b_h = dos_organizaciones["b_h"]
    alerta = api.post("/api/v1/alertas", headers=b_h,
                      json={"nombre": "Propia de B", "criterios": {"score_min": 0}}).json()

    r = api.post("/api/v1/subastas", headers=b_h,
                 json={**CAPTADA, "identificador_externo": "regresion-001",
                       "fecha_cierre": (datetime.now(timezone.utc)
                                        + timedelta(hours=300)).isoformat()})
    assert r.status_code == 201, r.text
    assert r.json()["alertas_disparadas"] >= 1

    from app.core.db import SessionLocal
    from app import models
    db = SessionLocal()
    try:
        notif = (db.query(models.Notificacion)
                 .filter(models.Notificacion.alerta_id == alerta["id"]).first())
        assert notif is not None
    finally:
        db.close()


def test_sin_proveedor_configurado_nada_rompe(api, headers):
    """Sin EMAIL_PROVIDER ni TELEGRAM_BOT_TOKEN la captación con alertas no falla."""
    from app.notificadores import email as email_mod
    email_mod.ultimo_email = None
    r = api.post("/api/v1/subastas", headers=headers,
                 json={**CAPTADA, "fecha_cierre": (datetime.now(timezone.utc)
                                                   + timedelta(hours=300)).isoformat()})
    assert r.status_code == 201, r.text
    # El email quedó en el buffer honesto (no enviado, no roto) con enlace de baja.
    assert email_mod.ultimo_email is not None
    assert "baja?token=" in (email_mod.ultimo_email["enlace_baja"] or "")


# ── Alertas privadas por usuario ────────────────────────────────────────────

def test_alerta_ajena_devuelve_404(api, headers):
    propia = api.post("/api/v1/alertas", headers=headers,
                      json={"nombre": "Mía", "criterios": {}}).json()
    # Otro usuario (miembro de la misma org, pero las alertas son POR USUARIO)
    r = api.post("/api/v1/organizacion/miembros", headers=headers,
                 json={"email": "otro@ejemplo.com", "password": "otro1234",
                       "nombre": "Otro", "rol": "analista"})
    assert r.status_code == 201, r.text
    h_otro = token_headers(api, "otro@ejemplo.com", "otro1234")
    assert api.get("/api/v1/alertas", headers=h_otro).json() == []
    r = api.patch(f"/api/v1/alertas/{propia['id']}", headers=h_otro,
                  json={"activa": False})
    assert r.status_code == 404                         # ajeno = inexistente, no 403
    assert api.delete(f"/api/v1/alertas/{propia['id']}", headers=h_otro).status_code == 404


# ── Vinculación Telegram ────────────────────────────────────────────────────

def test_codigo_telegram_generacion_y_un_solo_uso(api, headers):
    from app.core.db import SessionLocal
    from app.services import notificaciones_service as svc

    r = api.post("/api/v1/notificaciones/telegram/codigo", headers=headers)
    assert r.status_code == 201, r.text
    codigo = r.json()["codigo"]
    assert len(codigo) == 6 and codigo.isdigit()

    db = SessionLocal()
    try:
        usuario = svc.vincular_telegram(db, codigo, chat_id="12345")
        assert usuario is not None
        pref = svc.obtener_preferencias(db, usuario.id)
        assert pref.telegram_chat_id == "12345"
        assert "telegram" in pref.canales
        # Un solo uso: el mismo código ya no vale
        assert svc.vincular_telegram(db, codigo, chat_id="99999") is None
    finally:
        db.close()

    prefs = api.get("/api/v1/notificaciones/preferencias", headers=headers).json()
    assert prefs["telegram_vinculado"] is True
    assert api.delete("/api/v1/notificaciones/telegram", headers=headers).json()["ok"]
    prefs = api.get("/api/v1/notificaciones/preferencias", headers=headers).json()
    assert prefs["telegram_vinculado"] is False


def test_codigo_telegram_caducado(api, headers):
    from app.core.db import SessionLocal
    from app import models
    from app.services import notificaciones_service as svc

    r = api.post("/api/v1/notificaciones/telegram/codigo", headers=headers)
    codigo = r.json()["codigo"]
    db = SessionLocal()
    try:
        fila = db.get(models.CodigoTelegram, codigo)
        fila.expira_en = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
        assert svc.vincular_telegram(db, codigo, chat_id="123") is None
    finally:
        db.close()


def test_generar_codigo_invalida_los_previos(api, headers):
    r1 = api.post("/api/v1/notificaciones/telegram/codigo", headers=headers).json()
    r2 = api.post("/api/v1/notificaciones/telegram/codigo", headers=headers).json()
    from app.core.db import SessionLocal
    from app.services import notificaciones_service as svc
    db = SessionLocal()
    try:
        assert svc.vincular_telegram(db, r1["codigo"], chat_id="1") is None
        assert svc.vincular_telegram(db, r2["codigo"], chat_id="1") is not None
    finally:
        db.close()


# ── Preferencias ────────────────────────────────────────────────────────────

def test_preferencias_actualizar_y_validar(api, headers):
    r = api.put("/api/v1/notificaciones/preferencias", headers=headers,
                json={"modo": "digest_diario", "hora_digest": 9,
                      "silencio_inicio": 22, "silencio_fin": 8})
    assert r.status_code == 200, r.text
    assert r.json()["modo"] == "digest_diario"
    assert api.put("/api/v1/notificaciones/preferencias", headers=headers,
                   json={"modo": "cada_minuto"}).status_code == 400
    # restaurar
    api.put("/api/v1/notificaciones/preferencias", headers=headers,
            json={"modo": "instantaneo"})


# ── Digest ──────────────────────────────────────────────────────────────────

def test_digest_agrupa_en_un_solo_mensaje(api, headers):
    from app.core.db import SessionLocal
    from app import models
    from app.notificadores import email as email_mod
    from app.services import notificaciones_service as svc

    db = SessionLocal()
    try:
        admin = db.query(models.Usuario).filter(
            models.Usuario.email == "admin@seis.local").first()
        pref = svc.obtener_preferencias(db, admin.id)
        pref.modo = "digest_diario"
        # Limpieza: los tests del matcher dejan pendientes (sin proveedor no se envían)
        db.query(models.Notificacion).filter(
            models.Notificacion.usuario_id == admin.id).delete()
        for i in range(3):
            db.add(models.Notificacion(usuario_id=admin.id,
                                       asunto=f"Novedad {i + 1}",
                                       cuerpo=f"Cuerpo de la novedad {i + 1}"))
        db.commit()

        email_mod.ultimo_email = None
        agrupadas = svc.enviar_digest_usuario(db, admin, pref)
        # Sin proveedor el envío no se completa (0 enviadas) pero el buffer
        # demuestra que las 3 se agruparon en UN solo email.
        assert agrupadas == 0
        assert email_mod.ultimo_email is not None
        cuerpo = email_mod.ultimo_email["cuerpo"]
        assert "3 novedad(es)" in cuerpo
        assert all(f"Novedad {i + 1}" in cuerpo for i in range(3))

        # restaurar
        pref.modo = "instantaneo"
        db.query(models.Notificacion).filter(
            models.Notificacion.usuario_id == admin.id).delete()
        db.commit()
    finally:
        db.close()


# ── Baja firmada ────────────────────────────────────────────────────────────

def test_baja_firmada_desactiva_comunicaciones(api, headers):
    token = crear_token_proposito("admin@seis.local", "baja", horas=1)
    r = api.post("/api/v1/notificaciones/baja", json={"token": token})
    assert r.status_code == 200, r.text
    prefs = api.get("/api/v1/notificaciones/preferencias", headers=headers).json()
    assert prefs["comunicaciones_activas"] is False


def test_baja_token_invalido_o_proposito_incorrecto(api):
    assert api.post("/api/v1/notificaciones/baja",
                    json={"token": "no-es-un-token"}).status_code == 400
    token_otro = crear_token_proposito("admin@seis.local", "verificar", horas=1)
    assert api.post("/api/v1/notificaciones/baja",
                    json={"token": token_otro}).status_code == 400


def test_baja_token_caducado(api):
    import time
    from app.core.config import get_settings
    ahora = datetime.now(timezone.utc)
    payload = {"sub": "admin@seis.local", "proposito": "baja", "jti": "x",
               "iat": ahora - timedelta(hours=2), "exp": ahora - timedelta(hours=1)}
    caducado = jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")
    assert api.post("/api/v1/notificaciones/baja",
                    json={"token": caducado}).status_code == 400

"""Fase 12 — Tareas Celery de notificaciones: polling de Telegram y digest.

Polling en lugar de webhook (decisión aprobada): no exige URL pública HTTPS y
funciona en cualquier entorno. Migrar a webhook en Fase 11 solo requiere llamar
a `procesar_update` desde el endpoint del webhook.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery

log = logging.getLogger("seis.tasks.notificaciones")


def procesar_update(db, update: dict) -> bool:
    """Procesa un update de Telegram: «/start CODIGO» vincula al usuario."""
    from app.notificadores.telegram import api_telegram
    from app.services import notificaciones_service

    mensaje = update.get("message") or {}
    texto = (mensaje.get("text") or "").strip()
    chat_id = str((mensaje.get("chat") or {}).get("id") or "")
    if not chat_id or not texto.startswith("/start"):
        return False
    partes = texto.split(maxsplit=1)
    codigo = partes[1].strip() if len(partes) > 1 else ""
    usuario = notificaciones_service.vincular_telegram(db, codigo, chat_id) if codigo else None
    if usuario:
        api_telegram("sendMessage", chat_id=chat_id,
                     text=f"✅ Cuenta vinculada correctamente a {usuario.email}. "
                          "Recibirá aquí sus alertas de SEIS.")
        return True
    api_telegram("sendMessage", chat_id=chat_id,
                 text="❌ Código inválido o caducado. Genere uno nuevo desde "
                      "Alertas → Preferencias en SEIS.")
    return False


@celery.task(name="seis.telegram_polling")
def telegram_polling() -> int:
    """Consume getUpdates con offset persistente en Redis. Sin token: no-op."""
    from app.core.config import get_settings
    from app.core.db import SessionLocal
    from app.notificadores.telegram import api_telegram

    if not get_settings().telegram_bot_token:
        return 0

    import redis
    r = redis.Redis.from_url(get_settings().redis_url)
    offset = int(r.get("seis:telegram:offset") or 0)
    respuesta = api_telegram("getUpdates", offset=offset + 1, timeout=0)
    if not respuesta:
        return 0

    procesados = 0
    db = SessionLocal()
    try:
        for update in respuesta.get("result", []):
            if procesar_update(db, update):
                procesados += 1
            offset = max(offset, int(update.get("update_id", 0)))
        r.set("seis:telegram:offset", offset)
    finally:
        db.close()
    return procesados


@celery.task(name="seis.digest")
def enviar_digests() -> int:
    """Cada hora: envía el digest a los usuarios cuya hora toca.

    digest_diario ⇒ a su hora_digest cada día; digest_semanal ⇒ solo los lunes.
    Agrupa todas las notificaciones pendientes del usuario en UN solo mensaje.
    """
    from app import models
    from app.core.db import SessionLocal
    from app.services import notificaciones_service

    ahora = datetime.now(timezone.utc)
    total = 0
    db = SessionLocal()
    try:
        prefs = (db.query(models.PreferenciasNotificacion)
                 .filter(models.PreferenciasNotificacion.modo.in_(
                     ("digest_diario", "digest_semanal")),
                     models.PreferenciasNotificacion.hora_digest == ahora.hour)
                 .all())
        for pref in prefs:
            if pref.modo == "digest_semanal" and ahora.weekday() != 0:
                continue
            usuario = db.get(models.Usuario, pref.usuario_id)
            if not usuario or not usuario.activo:
                continue
            total += notificaciones_service.enviar_digest_usuario(db, usuario, pref)
    finally:
        db.close()
    log.info("Digest: %d notificaciones agrupadas y enviadas", total)
    return total

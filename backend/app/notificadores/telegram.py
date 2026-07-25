"""Notificador de Telegram vía Bot API (Fase 12).

Sin TELEGRAM_BOT_TOKEN configurado es un no-op con log. El chat_id del usuario
se obtiene por vinculación con código (ver notificaciones_service).
"""
from __future__ import annotations

import logging

import httpx

from app import models
from app.core.config import get_settings
from app.notificadores.base import Mensaje, Notificador

log = logging.getLogger("seis.notificadores.telegram")

_API = "https://api.telegram.org/bot{token}/{metodo}"


def api_telegram(metodo: str, **params) -> dict | None:
    """Llamada mínima a la Bot API; None si no hay token o la llamada falla."""
    token = get_settings().telegram_bot_token
    if not token:
        return None
    try:
        r = httpx.post(_API.format(token=token, metodo=metodo), json=params, timeout=15)
        datos = r.json()
        return datos if datos.get("ok") else None
    except Exception:                                        # noqa: BLE001 — el canal nunca rompe
        log.exception("Fallo llamando a Telegram (%s)", metodo)
        return None


class NotificadorTelegram(Notificador):
    canal = "telegram"

    def disponible(self) -> bool:
        return bool(get_settings().telegram_bot_token)

    def enviar(self, usuario: models.Usuario, mensaje: Mensaje) -> bool:
        chat_id = getattr(usuario, "_telegram_chat_id", None)
        if not self.disponible():
            log.info("Telegram sin token (no enviado): para=%s", usuario.email)
            return False
        if not chat_id:
            log.info("Usuario %s sin Telegram vinculado", usuario.email)
            return False
        texto = f"*{mensaje.asunto}*\n\n{mensaje.cuerpo}"
        return api_telegram("sendMessage", chat_id=chat_id, text=texto,
                            parse_mode="Markdown") is not None

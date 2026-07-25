"""Registro y despacho de notificadores por canal (Fase 12)."""
from __future__ import annotations

from app.notificadores.base import Notificador
from app.notificadores.email import NotificadorEmail
from app.notificadores.telegram import NotificadorTelegram

_NOTIFICADORES: dict[str, Notificador] = {
    "email": NotificadorEmail(),
    "telegram": NotificadorTelegram(),
}

CANALES_VALIDOS = tuple(_NOTIFICADORES)


def obtener_notificadores(canales: list[str]) -> list[Notificador]:
    """Devuelve los notificadores de los canales pedidos (ignora los desconocidos)."""
    return [_NOTIFICADORES[c] for c in canales if c in _NOTIFICADORES]

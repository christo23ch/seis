"""Fase 12 — Notificadores multicanal con interfaz común.

Cada canal implementa `Notificador.enviar(usuario, mensaje)`. Sin proveedor
configurado ningún canal rompe: registra en log y devuelve False.
"""
from app.notificadores.base import Mensaje, Notificador
from app.notificadores.registro import obtener_notificadores

__all__ = ["Mensaje", "Notificador", "obtener_notificadores"]

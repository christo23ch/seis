"""Envío de email (Fase 10): abstracción honesta, sin proveedor externo.

`ConsoleEmailBackend` es la única implementación hoy: escribe el correo al log
estructurado. No hay ningún buffer ni estado de módulo compartido — quien
necesite inspeccionar lo "enviado" (tests) inyecta su propio `EmailBackend`
(vía DI, pasando `email_backend=...` a las funciones de `usuario_service`) en
vez de leer un buffer global. La integración con un proveedor real
(Postmark/SES, Fase 12) implicará añadir una nueva subclase, no tocar esta.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.core.config import get_settings

logger = logging.getLogger("seis.email")


class EmailBackend(ABC):
    @abstractmethod
    def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        ...


class ConsoleEmailBackend(EmailBackend):
    """Implementación actual: sin proveedor externo, solo log estructurado."""

    def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        logger.info("EMAIL destinatario=%s asunto=%r cuerpo=%r",
                   destinatario, asunto, cuerpo)


def enviar_verificacion(destinatario: str, token: str,
                        email_backend: EmailBackend | None = None) -> None:
    backend = email_backend or ConsoleEmailBackend()
    enlace = f"{get_settings().frontend_url}/verificar?token={token}"
    backend.enviar(
        destinatario, "Verifica tu cuenta en SEIS",
        f"Confirma tu email visitando: {enlace}\nEl enlace caduca en 24 horas.")


def enviar_reseteo(destinatario: str, token: str,
                   email_backend: EmailBackend | None = None) -> None:
    backend = email_backend or ConsoleEmailBackend()
    enlace = f"{get_settings().frontend_url}/resetear?token={token}"
    backend.enviar(
        destinatario, "Restablece tu contraseña en SEIS",
        f"Restablece tu contraseña visitando: {enlace}\nEl enlace caduca en 1 hora. "
        "Si no lo solicitaste, ignora este mensaje.")

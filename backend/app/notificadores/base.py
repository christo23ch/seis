"""Interfaz común de los notificadores (Fase 12)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app import models


@dataclass(frozen=True)
class Mensaje:
    """Mensaje neutro respecto al canal: cada notificador lo formatea a su medio."""
    asunto: str
    cuerpo: str                      # texto plano en español; email lo envuelve en HTML simple
    # Enlace firmado de baja. Obligatorio en las comunicaciones **comerciales**
    # por email (alertas y digest, Fase 12). Los correos **transaccionales** de
    # la Fase 10 —verificación, reseteo y aviso de intento de registro— lo dejan
    # a None a propósito: nadie debe poder darse de baja del mensaje que
    # justamente le permite activar la cuenta o recuperar el acceso.
    enlace_baja: str | None = None


class Notificador(ABC):
    """Contrato del canal. `enviar` nunca lanza: devuelve False ante cualquier fallo."""

    canal: str = ""

    @abstractmethod
    def disponible(self) -> bool:
        """True si el canal tiene configuración suficiente para intentar el envío."""

    @abstractmethod
    def enviar(self, usuario: models.Usuario, mensaje: Mensaje) -> bool:
        """Envía el mensaje al usuario. Devuelve True solo si el envío se completó."""

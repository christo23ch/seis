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
    enlace_baja: str | None = None   # enlace firmado de baja (obligatorio en email)


class Notificador(ABC):
    """Contrato del canal. `enviar` nunca lanza: devuelve False ante cualquier fallo."""

    canal: str = ""

    @abstractmethod
    def disponible(self) -> bool:
        """True si el canal tiene configuración suficiente para intentar el envío."""

    @abstractmethod
    def enviar(self, usuario: models.Usuario, mensaje: Mensaje) -> bool:
        """Envía el mensaje al usuario. Devuelve True solo si el envío se completó."""

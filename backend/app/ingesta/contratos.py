"""Contratos de la capa de captación (Fase 17-A).

Separan el PARSEO (texto → contrato) de la INGESTA (contrato → base de datos).
Esa frontera es lo que permitirá a la Fase 17-B ajustar los selectores contra el
HTML real del portal sin tocar una línea de persistencia.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SubastaCaptada(BaseModel):
    """Una subasta tal y como la entrega una fuente, antes de persistirse.

    Vivía en `app/api/captacion.py`; se mueve aquí porque ya no es el cuerpo de
    una petición HTTP concreta, sino el contrato que comparten el alta manual y
    cualquier conector. El router la importa desde aquí, no la duplica.
    """
    fuente_codigo: str = Field(min_length=1, max_length=32)
    identificador_externo: str | None = None
    url: str | None = None
    valor_subasta: float = Field(gt=0)
    valor_referencia: float | None = Field(default=None, gt=0)  # tasación/mercado si la fuente lo da
    puja_minima: float | None = None
    deposito_pct: float = 0.05
    fecha_cierre: datetime | None = None
    subastas_desiertas_previas: int = 0
    tiene_descripcion: bool = False
    tiene_superficie: bool = False
    tiene_ubicacion: bool = False
    tiene_fotos: bool = False
    datos_extra: dict = Field(default_factory=dict)


@dataclass(frozen=True)
class OrigenCaptacion:
    """Quién capta. Decide a qué alertas alcanza el matcher.

    Existe para que ese alcance sea IMPOSIBLE de colar por descuido. Antes se
    pasaba un `organizacion_id: str | None` y `None` era ambiguo: el filtro
    `Usuario.organizacion_id == None` no significa «todas las organizaciones»,
    sino «los usuarios sin organización», que no es nadie. Una ingesta
    automática que pasara `None` no habría notificado a NADIE, en silencio, y la
    funcionalidad central habría quedado inerte sin que fallara ningún test.

    Ahora el tipo obliga a decir cuál de los dos casos es. Ver ADR-0011.
    """
    tipo: Literal["manual", "plataforma"]
    organizacion_id: str | None = None

    @classmethod
    def manual(cls, organizacion_id: str | None) -> "OrigenCaptacion":
        """Un usuario capta a mano: el efecto queda dentro de SU organización."""
        return cls(tipo="manual", organizacion_id=organizacion_id)

    @classmethod
    def plataforma(cls) -> "OrigenCaptacion":
        """Un conector automático capta: alcanza a todas las organizaciones.

        No viola el aislamiento de la Fase 9 porque el invariante que aquella
        protege es que ninguna acción de un TENANT produzca efectos observables
        en otro — y el BOE no es un tenant.
        """
        return cls(tipo="plataforma", organizacion_id=None)


@dataclass
class ResumenLote:
    """Qué pasó al ingerir un lote. Se audita y se devuelve al llamador."""
    total: int = 0
    insertadas: int = 0
    duplicadas: int = 0
    fallidas: int = 0
    notificaciones: int = 0
    motivos_de_fallo: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.motivos_de_fallo is None:
            self.motivos_de_fallo = []

    def como_dict(self) -> dict:
        return {"total": self.total, "insertadas": self.insertadas,
                "duplicadas": self.duplicadas, "fallidas": self.fallidas,
                "notificaciones": self.notificaciones,
                "motivos_de_fallo": self.motivos_de_fallo}

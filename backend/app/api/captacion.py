"""Fase 12 — Captación mínima: ingesta manual de subastas con scoring exprés.

Las subastas captadas son conocimiento COMPARTIDO entre organizaciones (CLAUDE.md §4);
lo privado son las alertas y notificaciones que generan. El conector BOE real es
trabajo de la Fase 17: este router da la vía de entrada manual y para conectores.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.api.deps import ROLES_ESCRITURA, get_current_user, require_rol
from app.core.db import get_db
from app.engine.scoring_expres import puntuar_subasta
from app.services import notificaciones_service
from app.services.conocimiento_service import parametros_vigentes

router = APIRouter(prefix="/subastas", tags=["captacion"])


class SubastaCaptada(BaseModel):
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


def _subasta_dict(s: models.Subasta) -> dict:
    brutos = s.datos_brutos or {}
    return {"id": s.id, "fuente_codigo": s.fuente_codigo,
            "identificador_externo": s.identificador_externo, "url": s.url,
            "valor_subasta": float(s.valor_subasta),
            "fecha_cierre": s.fecha_cierre.isoformat() if s.fecha_cierre else None,
            "estado": s.estado,
            "subastas_desiertas_previas": s.subastas_desiertas_previas,
            "score": brutos.get("score"), "score_desglose": brutos.get("score_desglose"),
            "creado_en": s.creado_en.isoformat() if s.creado_en else None}


@router.post("", status_code=201)
def captar_subasta(body: SubastaCaptada,
                   user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA)),
                   db: Session = Depends(get_db)) -> dict:
    """Ingesta una subasta, calcula el scoring exprés y dispara el matcher de alertas."""
    params = parametros_vigentes(db)
    datos_scoring = body.model_dump(mode="json")
    # P0.3 — ahora se calcula UNA sola vez aquí y se pasa explícito: puntuar_subasta()
    # ya no lee el reloj internamente, así que el score queda ligado a este instante
    # congelado, no al momento en que alguien lo reevalúe.
    ahora = datetime.now(timezone.utc)
    puntuacion = puntuar_subasta(datos_scoring, params, ahora)

    subasta = models.Subasta(
        fuente_codigo=body.fuente_codigo,
        identificador_externo=body.identificador_externo,
        url=body.url, valor_subasta=body.valor_subasta,
        puja_minima=body.puja_minima, deposito_pct=body.deposito_pct,
        fecha_cierre=body.fecha_cierre,
        subastas_desiertas_previas=body.subastas_desiertas_previas,
        datos_brutos={**body.datos_extra, "captacion": datos_scoring,
                      "score": puntuacion["score"],
                      "score_desglose": puntuacion["desglose"],
                      "score_version_parametros": puntuacion["version_parametros"],
                      "score_calculado_en": ahora.isoformat()})
    db.add(subasta)
    db.flush()                                       # asigna el id antes de auditar
    db.add(models.Auditoria(quien=user.email, entidad="subasta", entidad_id=subasta.id,
                            accion="captar", delta={"fuente": body.fuente_codigo,
                                                    "score": puntuacion["score"]}))
    db.commit()
    db.refresh(subasta)

    # P0.2 — el matcher solo evalúa alertas de la MISMA organización que el
    # captador (ver la regla documentada en notificaciones_service.evaluar_subasta).
    notificaciones = notificaciones_service.evaluar_subasta(db, subasta, user.organizacion_id)
    return {**_subasta_dict(subasta), "alertas_disparadas": len(notificaciones)}


@router.get("")
def listar_subastas(user: models.Usuario = Depends(get_current_user),
                    db: Session = Depends(get_db),
                    score_min: int | None = None) -> list[dict]:
    subastas = (db.query(models.Subasta)
                .order_by(models.Subasta.creado_en.desc()).limit(200).all())
    filas = [_subasta_dict(s) for s in subastas]
    if score_min is not None:
        # P4: sin score no pasa un filtro score_min.
        filas = [f for f in filas if f["score"] is not None and f["score"] >= score_min]
    return filas

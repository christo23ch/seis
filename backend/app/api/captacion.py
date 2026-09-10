"""Captación de subastas: alta manual y consulta del catálogo.

Las subastas captadas son conocimiento COMPARTIDO entre organizaciones (CLAUDE.md §4);
lo privado son las alertas y notificaciones que generan.

Desde la Fase 17-A este router NO ingiere por su cuenta: delega en
`services/ingesta_service.py`, que es el único camino de entrada de una subasta
al sistema. Así el scoring, el dedupe y el disparo de alertas ocurren igual venga
de un formulario o de un conector automático.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.deps import ROLES_ESCRITURA, get_current_user, require_rol
from app.core.db import get_db
from app.ingesta.contratos import OrigenCaptacion, SubastaCaptada
from app.services import ingesta_service

router = APIRouter(prefix="/subastas", tags=["captacion"])


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
    """Alta manual de una subasta.

    El origen es `manual`, de modo que el matcher solo alcanza alertas de la
    organización de quien capta: un acto de un tenant no produce efectos en otro
    (regla de la Fase 12, P0.2). La ingesta automática usa
    `OrigenCaptacion.plataforma()` y sí alcanza a todas — ver ADR-0011.
    """
    resumen, nuevas = ingesta_service.procesar_lote(
        db, [body], OrigenCaptacion.manual(user.organizacion_id), quien=user.email)

    if not nuevas:
        if resumen.duplicadas:
            raise HTTPException(409, "Esa subasta ya estaba captada")
        raise HTTPException(422, "No se pudo captar la subasta: " +
                            "; ".join(resumen.motivos_de_fallo))
    return {**_subasta_dict(nuevas[0]), "alertas_disparadas": resumen.notificaciones}


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

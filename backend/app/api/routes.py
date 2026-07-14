"""API REST v1 — análisis (protegido por JWT desde la Fase 2)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app import models
from app.api.deps import ROLES_ESCRITURA, get_current_user, require_rol
from app.core.config import get_settings
from app.core.db import get_db
from app.engine.contracts import AnalisisInput
from app.services import analisis_service, pdf_service

router = APIRouter(tags=["analisis"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "servicio": "seis-backend"}


@router.post("/analisis")
def crear_analisis(inp: AnalisisInput, db: Session = Depends(get_db),
                   user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    analisis_id, resultado = analisis_service.crear_analisis(
        db, inp, quien=user.email, organizacion_id=user.organizacion_id)
    return {"id": analisis_id, "resultado": resultado.model_dump()}


@router.post("/analisis/simular")
def simular_analisis(inp: AnalisisInput, db: Session = Depends(get_db),
                     _u: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """Ejecuta el motor con el conocimiento vigente sin persistir (paso 11 del asistente)."""
    return analisis_service.simular(db, inp).model_dump()


@router.post("/analisis/async", status_code=202)
def crear_analisis_async(inp: AnalisisInput,
                         user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    from app.tasks.celery_app import analizar_task
    t = analizar_task.delay(json.loads(inp.model_dump_json()),
                            organizacion_id=user.organizacion_id, quien=user.email)
    if get_settings().celery_task_always_eager:               # tests / modo síncrono
        return {"tarea_id": t.id, "estado": t.status, "resultado": t.result}
    return {"tarea_id": t.id, "estado": "PENDING"}


@router.get("/tareas/{tarea_id}")
def estado_tarea(tarea_id: str,
                 _u: models.Usuario = Depends(get_current_user)) -> dict:
    from app.tasks.celery_app import celery
    r = celery.AsyncResult(tarea_id)
    out = {"tarea_id": tarea_id, "estado": r.status}
    if r.successful():
        out["resultado"] = r.result
    elif r.failed():
        out["error"] = str(r.result)
    return out


@router.get("/analisis")
def listar(limit: int = 50, db: Session = Depends(get_db),
           user: models.Usuario = Depends(get_current_user)) -> list[dict]:
    return analisis_service.listar_analisis(db, limit, organizacion_id=user.organizacion_id)


@router.get("/analisis/{analisis_id}")
def detalle(analisis_id: str, db: Session = Depends(get_db),
            user: models.Usuario = Depends(get_current_user)) -> dict:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    return {"id": a.id, "creado_en": a.creado_en.isoformat() if a.creado_en else None,
            "perfil": a.perfil_codigo, "version_reglas": a.version_reglas,
            "version_parametros": a.version_parametros, "entrada": a.entrada,
            "resultado": a.resultado}


@router.get("/analisis/{analisis_id}/informe", response_class=PlainTextResponse)
def informe(analisis_id: str, db: Session = Depends(get_db),
            user: models.Usuario = Depends(get_current_user)) -> str:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    return a.resultado.get("informe_markdown", "")


@router.get("/analisis/{analisis_id}/informe.pdf")
def informe_pdf(analisis_id: str, db: Session = Depends(get_db),
                user: models.Usuario = Depends(get_current_user)) -> Response:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    pdf = pdf_service.informe_a_pdf(a.resultado.get("informe_markdown", ""))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="SEIS_informe_{analisis_id[:8]}.pdf"'})


@router.get("/analisis/{analisis_id}/checklist")
def checklist(analisis_id: str, db: Session = Depends(get_db),
              user: models.Usuario = Depends(get_current_user)) -> list[dict]:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    return a.resultado.get("checklist", [])

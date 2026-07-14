"""API de organización (Fase 9): datos del tenant y gestión de miembros por el propietario."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_current_user, require_propietario
from app.core.db import get_db
from app.services import usuario_service

router = APIRouter(prefix="/organizacion", tags=["organizacion"])


class MiembroCrear(BaseModel):
    email: EmailStr
    password: str                     # contraseña temporal
    nombre: str | None = None
    rol: str = "analista"             # capacidad dentro de la org: analista | lector


class MiembroPatch(BaseModel):
    activo: bool


def _miembro_dict(u: models.Usuario) -> dict:
    return {"id": u.id, "email": u.email, "nombre": u.nombre, "rol": u.rol,
            "rol_org": u.rol_org, "activo": u.activo}


@router.get("")
def mi_organizacion(user: models.Usuario = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> dict:
    if not user.organizacion_id:
        raise HTTPException(404, "El usuario no pertenece a ninguna organización")
    org = usuario_service.obtener_organizacion(db, user.organizacion_id)
    if not org:
        raise HTTPException(404, "Organización no encontrada")
    puede_gestionar = user.rol_org == "propietario" or user.es_superadmin
    return {
        "id": org.id, "nombre": org.nombre,
        "rol_org": user.rol_org, "puede_gestionar": puede_gestionar,
        "miembros": [_miembro_dict(m) for m in usuario_service.miembros_de_org(db, org.id)],
    }


@router.post("/miembros", status_code=201)
def crear_miembro(body: MiembroCrear,
                  user: models.Usuario = Depends(require_propietario),
                  db: Session = Depends(get_db)) -> dict:
    if not user.organizacion_id:
        raise HTTPException(400, "El propietario no tiene organización asignada")
    try:
        u = usuario_service.crear_miembro(
            db, user.organizacion_id, body.email, body.password, body.nombre,
            rol=body.rol, quien=user.email)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _miembro_dict(u)


@router.patch("/miembros/{miembro_id}")
def actualizar_miembro(miembro_id: str, body: MiembroPatch,
                       user: models.Usuario = Depends(require_propietario),
                       db: Session = Depends(get_db)) -> dict:
    miembro = usuario_service.obtener_por_id(db, miembro_id)
    # Un recurso de otra organización se comporta como inexistente (404, no 403).
    if not miembro or (not user.es_superadmin
                       and miembro.organizacion_id != user.organizacion_id):
        raise HTTPException(404, "Miembro no encontrado")
    if miembro.id == user.id:
        raise HTTPException(400, "No puede desactivarse a sí mismo")
    usuario_service.set_activo_miembro(db, miembro, body.activo, quien=user.email)
    return _miembro_dict(miembro)

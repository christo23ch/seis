"""Autenticación: login OAuth2 password, perfil propio y alta de usuarios (admin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_current_user, require_rol
from app.core.db import get_db
from app.core.security import crear_token
from app.services import usuario_service

router = APIRouter(prefix="/auth", tags=["auth"])


class UsuarioCrear(BaseModel):
    email: EmailStr
    password: str
    nombre: str | None = None
    rol: str = "analista"


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> dict:
    user = usuario_service.autenticar(db, form.username, form.password)
    if not user:
        raise HTTPException(401, "Email o contraseña incorrectos")
    return {"access_token": crear_token(user.email, user.rol),
            "token_type": "bearer", "rol": user.rol, "nombre": user.nombre}


@router.get("/me")
def me(user: models.Usuario = Depends(get_current_user)) -> dict:
    return {"email": user.email, "nombre": user.nombre, "rol": user.rol}


@router.post("/usuarios", status_code=201)
def crear_usuario(body: UsuarioCrear, db: Session = Depends(get_db),
                  _admin: models.Usuario = Depends(require_rol("admin"))) -> dict:
    try:
        u = usuario_service.crear_usuario(db, body.email, body.password, body.nombre, body.rol)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"email": u.email, "rol": u.rol}

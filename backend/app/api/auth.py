"""Autenticación: login OAuth2 password, perfil propio, alta de usuarios (superadmin)
y alta self-service (Fase 10: registro, verificación de email, recuperación de
contraseña, anti fuerza-bruta)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_current_user, require_superadmin
from app.core import rate_limit
from app.core.db import get_db
from app.core.security import crear_token
from app.services import usuario_service

router = APIRouter(prefix="/auth", tags=["auth"])


class UsuarioCrear(BaseModel):
    email: EmailStr
    password: str
    nombre: str | None = None
    rol: str = "analista"
    organizacion_id: str | None = None       # superadmin: org destino (por defecto, la suya)
    rol_org: str = "miembro"
    es_superadmin: bool = False


class RegistroBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str | None = None


class VerificarBody(BaseModel):
    token: str


class RecuperarBody(BaseModel):
    email: EmailStr


class ResetearBody(BaseModel):
    token: str
    nueva: str = Field(min_length=8)


_MSG_LOGIN_INVALIDO = "Email o contraseña incorrectos"


@router.post("/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
         db: Session = Depends(get_db)) -> dict:
    email = form.username.strip().lower()
    ip = request.client.host if request.client else "desconocida"

    # Dos cubos independientes (email e IP): ambos deben estar libres para intentar
    # el login. No se distingue en el mensaje qué cubo bloqueó — evita filtrar info.
    if rate_limit.bloqueado("email", email) or rate_limit.bloqueado("ip", ip):
        raise HTTPException(429, "Demasiados intentos. Inténtalo de nuevo más tarde.")

    user = usuario_service.autenticar(db, email, form.password)
    if not user:
        # autenticar() ya devuelve None tanto si el email no existe, como si la
        # contraseña es incorrecta, como si la cuenta está inactiva (incl. sin
        # verificar) — el mismo mensaje genérico cubre los tres casos sin distinguir.
        rate_limit.registrar_fallo("email", email)
        rate_limit.registrar_fallo("ip", ip)
        raise HTTPException(401, _MSG_LOGIN_INVALIDO)

    rate_limit.limpiar("email", email)
    rate_limit.limpiar("ip", ip)
    return {"access_token": crear_token(user.email, user.rol),
            "token_type": "bearer", "rol": user.rol, "nombre": user.nombre}


@router.get("/me")
def me(user: models.Usuario = Depends(get_current_user),
       db: Session = Depends(get_db)) -> dict:
    org = (usuario_service.obtener_organizacion(db, user.organizacion_id)
           if user.organizacion_id else None)
    return {"email": user.email, "nombre": user.nombre, "rol": user.rol,
            "organizacion_id": user.organizacion_id,
            "organizacion_nombre": org.nombre if org else None,
            "rol_org": user.rol_org, "es_superadmin": user.es_superadmin}


@router.post("/usuarios", status_code=201)
def crear_usuario(body: UsuarioCrear, db: Session = Depends(get_db),
                  admin: models.Usuario = Depends(require_superadmin)) -> dict:
    try:
        u = usuario_service.crear_usuario(
            db, body.email, body.password, body.nombre, body.rol,
            organizacion_id=body.organizacion_id or admin.organizacion_id,
            rol_org=body.rol_org, es_superadmin=body.es_superadmin)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"email": u.email, "rol": u.rol, "organizacion_id": u.organizacion_id}


# ─────────────── Alta self-service (Fase 10) ───────────────

@router.post("/registro", status_code=201)
def registro(body: RegistroBody, db: Session = Depends(get_db)) -> dict:
    try:
        u = usuario_service.registrar_usuario(db, body.email, body.password, body.nombre)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"email": u.email, "mensaje": "Cuenta creada. Revisa tu email para verificarla."}


@router.post("/verificar")
def verificar(body: VerificarBody, db: Session = Depends(get_db)) -> dict:
    try:
        u = usuario_service.verificar_email(db, body.token)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"email": u.email, "mensaje": "Cuenta verificada. Ya puedes iniciar sesión."}


@router.post("/recuperar")
def recuperar(body: RecuperarBody, db: Session = Depends(get_db)) -> dict:
    # Respuesta idéntica exista o no la cuenta: no se filtra su existencia.
    usuario_service.solicitar_reseteo(db, body.email)
    return {"mensaje": "Si la cuenta existe, recibirás instrucciones por email."}


@router.post("/resetear")
def resetear(body: ResetearBody, db: Session = Depends(get_db)) -> dict:
    try:
        usuario_service.resetear_password(db, body.token, body.nueva)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"mensaje": "Contraseña actualizada. Ya puedes iniciar sesión."}

"""Dependencias de autorización de la API."""
from __future__ import annotations

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models
from app.core.db import get_db
from app.core.security import decodificar_token
from app.services import usuario_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ROLES_ESCRITURA = ("admin", "analista")


def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> models.Usuario:
    error = HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas",
                          headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decodificar_token(token)
    except pyjwt.PyJWTError:
        raise error
    user = usuario_service.obtener_por_email(db, payload.get("sub", ""))
    if not user or not user.activo:
        raise error
    return user


def require_rol(*roles: str):
    def dep(user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Se requiere rol {' o '.join(roles)}")
        return user
    return dep


def require_superadmin(user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
    """Rol de plataforma (Fase 9): gobierna el conocimiento T2/T3 global y el alta
    de usuarios en cualquier organización."""
    if not user.es_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Se requiere rol de superadministrador de plataforma")
    return user


def require_propietario(user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
    """Gestión de miembros de la propia organización (propietario o superadmin)."""
    if user.rol_org != "propietario" and not user.es_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Se requiere ser propietario de la organización")
    return user

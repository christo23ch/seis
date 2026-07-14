"""Gestión de usuarios y autenticación."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import models
from app.core.security import hash_password, verify_password


def obtener_por_email(db: Session, email: str) -> models.Usuario | None:
    return db.query(models.Usuario).filter(models.Usuario.email == email.lower()).first()


def crear_usuario(db: Session, email: str, password: str, nombre: str | None = None,
                  rol: str = "analista") -> models.Usuario:
    if rol not in ("admin", "analista", "lector"):
        raise ValueError("rol inválido")
    if obtener_por_email(db, email):
        raise ValueError("email ya registrado")
    u = models.Usuario(email=email.lower(), nombre=nombre,
                       hash_pwd=hash_password(password), rol=rol)
    db.add(u)
    db.add(models.Auditoria(entidad="usuario", entidad_id=u.email, accion="crear",
                            delta={"rol": rol}))
    db.commit()
    db.refresh(u)
    return u


def autenticar(db: Session, email: str, password: str) -> models.Usuario | None:
    u = obtener_por_email(db, email)
    if u and u.activo and verify_password(password, u.hash_pwd):
        return u
    return None

"""Gestión de usuarios, organizaciones (Fase 9) y autenticación."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import models
from app.core.security import hash_password, verify_password

ROLES_VALIDOS = ("admin", "analista", "lector")
ROLES_ORG_VALIDOS = ("propietario", "miembro")


def obtener_por_email(db: Session, email: str) -> models.Usuario | None:
    return db.query(models.Usuario).filter(models.Usuario.email == email.lower()).first()


def obtener_por_id(db: Session, usuario_id: str) -> models.Usuario | None:
    return db.get(models.Usuario, usuario_id)


def crear_usuario(db: Session, email: str, password: str, nombre: str | None = None,
                  rol: str = "analista", organizacion_id: str | None = None,
                  rol_org: str = "miembro", es_superadmin: bool = False) -> models.Usuario:
    if rol not in ROLES_VALIDOS:
        raise ValueError("rol inválido")
    if rol_org not in ROLES_ORG_VALIDOS:
        raise ValueError("rol de organización inválido")
    if obtener_por_email(db, email):
        raise ValueError("email ya registrado")
    u = models.Usuario(email=email.lower(), nombre=nombre,
                       hash_pwd=hash_password(password), rol=rol,
                       organizacion_id=organizacion_id, rol_org=rol_org,
                       es_superadmin=es_superadmin)
    db.add(u)
    db.add(models.Auditoria(entidad="usuario", entidad_id=u.email, accion="crear",
                            delta={"rol": rol, "rol_org": rol_org,
                                   "organizacion_id": organizacion_id}))
    db.commit()
    db.refresh(u)
    return u


def autenticar(db: Session, email: str, password: str) -> models.Usuario | None:
    u = obtener_por_email(db, email)
    if u and u.activo and verify_password(password, u.hash_pwd):
        return u
    return None


# ─────────────── Organizaciones y miembros (Fase 9) ───────────────

def crear_organizacion(db: Session, nombre: str) -> models.Organizacion:
    org = models.Organizacion(nombre=nombre)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def obtener_organizacion(db: Session, organizacion_id: str) -> models.Organizacion | None:
    return db.get(models.Organizacion, organizacion_id)


def miembros_de_org(db: Session, organizacion_id: str) -> list[models.Usuario]:
    return (db.query(models.Usuario)
            .filter(models.Usuario.organizacion_id == organizacion_id)
            .order_by(models.Usuario.creado_en).all())


def crear_miembro(db: Session, organizacion_id: str, email: str, password: str,
                  nombre: str | None = None, rol: str = "analista",
                  quien: str | None = None) -> models.Usuario:
    """Alta de un miembro dentro de una organización (la efectúa su propietario).

    El nuevo usuario es siempre `rol_org='miembro'` y nunca superadmin; su capacidad
    (admin/analista/lector) la fija el propietario dentro del abanico permitido.
    """
    if rol not in ("analista", "lector"):
        # un propietario no puede crear otros administradores de plataforma ni capacidades admin
        raise ValueError("un miembro solo puede tener capacidad 'analista' o 'lector'")
    u = crear_usuario(db, email, password, nombre, rol=rol,
                      organizacion_id=organizacion_id, rol_org="miembro",
                      es_superadmin=False)
    db.add(models.Auditoria(quien=quien, entidad="usuario", entidad_id=u.email,
                            accion="alta_miembro",
                            delta={"organizacion_id": organizacion_id, "rol": rol}))
    db.commit()
    return u


def set_activo_miembro(db: Session, miembro: models.Usuario, activo: bool,
                       quien: str | None = None) -> models.Usuario:
    miembro.activo = activo
    db.add(models.Auditoria(quien=quien, entidad="usuario", entidad_id=miembro.email,
                            accion="activar" if activo else "desactivar",
                            delta={"organizacion_id": miembro.organizacion_id}))
    db.commit()
    db.refresh(miembro)
    return miembro

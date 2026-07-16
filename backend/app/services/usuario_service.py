"""Gestión de usuarios, organizaciones (Fase 9) y autenticación."""
from __future__ import annotations

import jwt as pyjwt
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import models
from app.core.security import (crear_token_proposito, decodificar_token_proposito,
                               hash_password, verify_password)
from app.services.email_service import EmailBackend, enviar_reseteo, enviar_verificacion

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


# ─────────────── Alta self-service (Fase 10) ───────────────
# Regla de transacción en todo este bloque: el email se envía SIEMPRE después de
# que la transacción relevante ya se confirmó con db.commit(); si el commit falla,
# no se ha enviado ni se envía ningún correo.

def registrar_usuario(db: Session, email: str, password: str, nombre: str | None,
                      email_backend: EmailBackend | None = None) -> models.Usuario:
    """Registro público: crea una organización propia + su propietario, inactivo
    hasta verificar el email. rol='admin' (capacidad plena dentro de su propia
    organización); rol_org='propietario'; es_superadmin=False (eso solo lo otorga
    un superadmin existente, nunca el alta self-service)."""
    if obtener_por_email(db, email):
        raise ValueError("email ya registrado")

    org = crear_organizacion(db, f"Organización de {nombre or email}")
    u = models.Usuario(email=email.lower(), nombre=nombre,
                       hash_pwd=hash_password(password), rol="admin",
                       organizacion_id=org.id, rol_org="propietario",
                       es_superadmin=False, activo=False, email_verificado=False)
    db.add(u)
    db.add(models.Auditoria(entidad="usuario", entidad_id=u.email,
                            accion="usuario_registrado",
                            delta={"organizacion_id": org.id}))
    db.commit()
    db.refresh(u)

    token = crear_token_proposito(u.email, "verificar", horas=24)
    enviar_verificacion(u.email, token, email_backend=email_backend)
    return u


def jti_consumido(db: Session, jti: str) -> bool:
    return db.get(models.TokenConsumido, jti) is not None


def marcar_jti(db: Session, jti: str, proposito: str) -> None:
    """Inserta el jti como consumido y confirma de inmediato: bajo concurrencia,
    la clave primaria de token_consumido es lo único que decide qué petición
    "gana" el token — la otra recibe IntegrityError/OperationalError al intentar
    el mismo insert y debe tratarse como token inválido."""
    db.add(models.TokenConsumido(jti=jti, proposito=proposito))
    db.commit()


def _decodificar_o_error(token: str, proposito: str) -> dict:
    try:
        return decodificar_token_proposito(token, proposito)
    except (pyjwt.PyJWTError, ValueError):
        raise ValueError("token inválido o caducado")


def verificar_email(db: Session, token: str) -> models.Usuario:
    payload = _decodificar_o_error(token, "verificar")
    try:
        marcar_jti(db, payload["jti"], "verificar")
    except (IntegrityError, OperationalError):
        db.rollback()
        raise ValueError("token inválido o ya usado")

    u = obtener_por_email(db, payload["sub"])
    if not u:
        raise ValueError("token inválido o caducado")

    u.activo = True
    u.email_verificado = True
    db.add(models.Auditoria(entidad="usuario", entidad_id=u.email,
                            accion="email_verificado", delta={}))
    db.commit()
    db.refresh(u)
    return u


def solicitar_reseteo(db: Session, email: str,
                      email_backend: EmailBackend | None = None) -> None:
    """Nunca revela si el email existe: sin cuenta, no hace nada (el endpoint
    responde igual en todos los casos). Si la cuenta existe pero no está
    verificada, no tiene sentido resetear una contraseña de una cuenta inactiva:
    se reenvía el correo de verificación en su lugar."""
    u = obtener_por_email(db, email)
    if not u:
        return

    if not u.email_verificado:
        db.add(models.Auditoria(entidad="usuario", entidad_id=u.email,
                                accion="password_reset_solicitado",
                                delta={"reenviado_verificacion": True}))
        db.commit()
        token = crear_token_proposito(u.email, "verificar", horas=24)
        enviar_verificacion(u.email, token, email_backend=email_backend)
        return

    db.add(models.Auditoria(entidad="usuario", entidad_id=u.email,
                            accion="password_reset_solicitado",
                            delta={"reenviado_verificacion": False}))
    db.commit()
    token = crear_token_proposito(u.email, "resetear", horas=1)
    enviar_reseteo(u.email, token, email_backend=email_backend)


def resetear_password(db: Session, token: str, nueva_password: str) -> models.Usuario:
    payload = _decodificar_o_error(token, "resetear")
    try:
        marcar_jti(db, payload["jti"], "resetear")
    except (IntegrityError, OperationalError):
        db.rollback()
        raise ValueError("token inválido o ya usado")

    u = obtener_por_email(db, payload["sub"])
    if not u:
        raise ValueError("token inválido o caducado")

    u.hash_pwd = hash_password(nueva_password)
    db.add(models.Auditoria(entidad="usuario", entidad_id=u.email,
                            accion="password_reseteada", delta={}))
    db.commit()
    db.refresh(u)
    return u

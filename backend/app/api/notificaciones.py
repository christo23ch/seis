"""Fase 12 — API de notificaciones: preferencias, Telegram, alertas y baja firmada."""
from __future__ import annotations

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import decodificar_token_proposito
from app.services import notificaciones_service as svc

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])
router_alertas = APIRouter(prefix="/alertas", tags=["alertas"])


# ── Esquemas ────────────────────────────────────────────────────────────────

class PreferenciasUpdate(BaseModel):
    canales: list[str] | None = None
    modo: str | None = None
    hora_digest: int | None = Field(default=None, ge=0, le=23)
    silencio_inicio: int | None = Field(default=None, ge=0, le=23)
    silencio_fin: int | None = Field(default=None, ge=0, le=23)


class BajaBody(BaseModel):
    token: str


class AlertaCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    criterios: dict = Field(default_factory=dict)   # fuente, valor_max, score_min…
    activa: bool = True


class AlertaPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    criterios: dict | None = None
    activa: bool | None = None


def _pref_dict(p: models.PreferenciasNotificacion) -> dict:
    return {"canales": p.canales, "modo": p.modo, "hora_digest": p.hora_digest,
            "silencio_inicio": p.silencio_inicio, "silencio_fin": p.silencio_fin,
            "telegram_vinculado": bool(p.telegram_chat_id),
            "comunicaciones_activas": p.comunicaciones_activas}


def _alerta_dict(a: models.Alerta) -> dict:
    return {"id": a.id, "nombre": a.nombre, "criterios": a.criterios, "activa": a.activa}


# ── Preferencias ────────────────────────────────────────────────────────────

@router.get("/preferencias")
def preferencias(user: models.Usuario = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict:
    return _pref_dict(svc.obtener_preferencias(db, user.id))


@router.put("/preferencias")
def actualizar_preferencias(body: PreferenciasUpdate,
                            user: models.Usuario = Depends(get_current_user),
                            db: Session = Depends(get_db)) -> dict:
    cambios = body.model_dump(exclude_unset=True)
    try:
        pref = svc.actualizar_preferencias(db, user, cambios)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _pref_dict(pref)


# ── Telegram ────────────────────────────────────────────────────────────────

@router.post("/telegram/codigo", status_code=201)
def codigo_telegram(user: models.Usuario = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> dict:
    codigo = svc.generar_codigo_telegram(db, user)
    s = get_settings()
    enlace = (f"https://t.me/{s.telegram_bot_nombre}?start={codigo.codigo}"
              if s.telegram_bot_nombre else None)
    return {"codigo": codigo.codigo, "expira_en": codigo.expira_en.isoformat(),
            "enlace": enlace}


@router.delete("/telegram")
def desvincular_telegram(user: models.Usuario = Depends(get_current_user),
                         db: Session = Depends(get_db)) -> dict:
    svc.desvincular_telegram(db, user)
    return {"ok": True}


# ── Baja firmada (público: sin login) ───────────────────────────────────────

@router.post("/baja")
def baja(body: BajaBody, db: Session = Depends(get_db)) -> dict:
    try:
        payload = decodificar_token_proposito(body.token, "baja")
    except pyjwt.PyJWTError:
        raise HTTPException(400, "Enlace de baja inválido o caducado")
    if not svc.dar_de_baja(db, payload["sub"]):
        raise HTTPException(400, "Enlace de baja inválido o caducado")
    return {"ok": True, "mensaje": "Comunicaciones desactivadas correctamente"}


# ── Alertas (privadas por usuario; recurso ajeno = 404) ─────────────────────

@router_alertas.get("")
def listar_alertas(user: models.Usuario = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> list[dict]:
    alertas = (db.query(models.Alerta)
               .filter(models.Alerta.usuario_id == user.id)
               .order_by(models.Alerta.creado_en).all())
    return [_alerta_dict(a) for a in alertas]


@router_alertas.post("", status_code=201)
def crear_alerta(body: AlertaCrear, user: models.Usuario = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict:
    a = models.Alerta(usuario_id=user.id, nombre=body.nombre,
                      criterios=body.criterios, activa=body.activa)
    db.add(a)
    db.flush()                                       # asigna el id antes de auditar
    db.add(models.Auditoria(quien=user.email, entidad="alerta", entidad_id=a.id,
                            accion="crear", delta={"criterios": body.criterios}))
    db.commit()
    db.refresh(a)
    return _alerta_dict(a)


def _alerta_propia(db: Session, alerta_id: str, user: models.Usuario) -> models.Alerta:
    a = db.get(models.Alerta, alerta_id)
    if not a or a.usuario_id != user.id:
        raise HTTPException(404, "Alerta no encontrada")
    return a


@router_alertas.patch("/{alerta_id}")
def actualizar_alerta(alerta_id: str, body: AlertaPatch,
                      user: models.Usuario = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> dict:
    a = _alerta_propia(db, alerta_id, user)
    cambios = body.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(a, campo, valor)
    db.add(models.Auditoria(quien=user.email, entidad="alerta", entidad_id=a.id,
                            accion="actualizar", delta=cambios))
    db.commit()
    db.refresh(a)
    return _alerta_dict(a)


@router_alertas.delete("/{alerta_id}", status_code=204)
def eliminar_alerta(alerta_id: str, user: models.Usuario = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> None:
    a = _alerta_propia(db, alerta_id, user)
    db.add(models.Auditoria(quien=user.email, entidad="alerta", entidad_id=a.id,
                            accion="eliminar", delta={}))
    db.delete(a)
    db.commit()

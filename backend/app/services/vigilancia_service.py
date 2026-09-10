"""Vigilancia de fuentes de captación (Fase 17-A).

Detecta el modo de fallo más peligroso de la ingesta: que un conector deje de
traer nada. No produce error, no llena ningún log de excepciones y el sistema
sigue respondiendo con normalidad — simplemente deja de haber subastas nuevas,
que desde fuera es indistinguible de que el portal no publique.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models
from app.services.conocimiento_service import parametros_vigentes

log = logging.getLogger("seis.vigilancia")

HORAS_POR_DEFECTO = 24
TIPO_AVISO = "fuente-en-silencio"


def _horas_umbral(db: Session) -> int:
    try:
        valor = parametros_vigentes(db).get("ingesta.vigilancia.horas_sin_items_alerta")
        return int(valor) if valor else HORAS_POR_DEFECTO
    except Exception:                            # noqa: BLE001 — nunca tumbar el planificador
        return HORAS_POR_DEFECTO


def _superadministradores(db: Session) -> list[models.Usuario]:
    return (db.query(models.Usuario)
            .filter(models.Usuario.es_superadmin.is_(True),
                    models.Usuario.activo.is_(True))
            .all())


def _ya_avisado(db: Session, usuario_id: str, fuente: str) -> bool:
    """¿Hay ya un aviso sin enviar de esta misma fuente para este usuario?

    Evita que una fuente rota una semana produzca siete avisos idénticos. Se mira
    el estado `pendiente`: si el digest ya lo envió, un recordatorio al día
    siguiente es información legítima, no ruido.
    """
    return db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id,
        models.Notificacion.estado == "pendiente",
        models.Notificacion.asunto.like(f"%{fuente}%"),
    ).first() is not None


def revisar_fuentes(db: Session) -> dict:
    """Crea una notificación por cada fuente activa que lleve demasiado callada."""
    horas = _horas_umbral(db)
    corte = datetime.now(timezone.utc) - timedelta(hours=horas)
    fuentes = db.query(models.FuenteSubasta).all()
    superadmins = _superadministradores(db)

    en_silencio: list[str] = []
    creadas = 0

    for fuente in fuentes:
        ultima = (db.query(models.Subasta)
                  .filter(models.Subasta.fuente_codigo == fuente.codigo)
                  .order_by(models.Subasta.creado_en.desc())
                  .first())
        # Una fuente sin NINGUNA subasta también cuenta: un conector que nunca
        # llegó a traer nada está tan roto como el que dejó de hacerlo.
        if ultima is not None and ultima.creado_en is not None:
            marca = ultima.creado_en
            if marca.tzinfo is None:             # SQLite devuelve naive
                marca = marca.replace(tzinfo=timezone.utc)
            if marca >= corte:
                continue

        en_silencio.append(fuente.codigo)
        for admin in superadmins:
            if _ya_avisado(db, admin.id, fuente.codigo):
                continue
            db.add(models.Notificacion(
                usuario_id=admin.id,
                asunto=f"SEIS — La fuente «{fuente.codigo}» lleva {horas} h sin traer nada",
                cuerpo=(f"La fuente de captación «{fuente.codigo}» no ha registrado ninguna "
                        f"subasta nueva en las últimas {horas} horas.\n\n"
                        "Suele significar que el portal cambió su estructura y el conector "
                        "ya no reconoce los datos. Conviene revisar los parámetros "
                        "«ingesta.*» y los registros de la última ingesta.")))
            creadas += 1

    if creadas:
        db.commit()
    if en_silencio:
        log.warning("vigilancia: fuentes en silencio: %s", ", ".join(en_silencio))

    return {"fuentes_revisadas": len(fuentes), "en_silencio": en_silencio,
            "avisos_creados": creadas, "umbral_horas": horas}

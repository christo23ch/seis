"""Fase 15 — checklist de arranque: qué le falta a una cuenta nueva para empezar.

**El principio que ordena este módulo:** un paso que se puede DEDUCIR de los datos
no se guarda. Que haya un análisis en cartera se le pregunta a la tabla de
análisis; que haya una alerta, a la de alertas. Solo se persisten los pasos que
**no dejan rastro** en ningún otro sitio — leer cómo funciona, por ejemplo—, y
esos se guardan en `paso_onboarding`.

La razón no es de eficiencia: es que **un visto que el usuario se pone a sí mismo
no demuestra nada**. Si la checklist dijera «tienes un análisis» porque alguien
marcó una casilla, el sistema estaría afirmando algo que no sabe — que es
exactamente lo que el motor tiene prohibido hacer (ADR-0015).

ALCANCE DECLARADO (ADR-0014):

- La checklist es **por usuario**, no por organización. En una cuenta con varias
  personas cada una tiene su propio arranque; si eso resulta molesto, es una
  decisión de producto y no un defecto de aquí.
- Los pasos deducidos se calculan **en el momento de la consulta**. No hay caché,
  así que no hay nada que pueda quedar desactualizado — y tampoco historial: si
  alguien borra su único análisis, el paso vuelve a estar pendiente.
- No envía recordatorios. La tabla soporta saber qué falta y desde cuándo, pero
  el envío no existe todavía.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models


@dataclass(frozen=True)
class Paso:
    clave: str
    titulo: str
    descripcion: str
    accion: str | None          # ruta relativa dentro de la app, si la hay
    deducido: bool              # True ⇒ se calcula de los datos, no se marca a mano


# El catálogo vive en código a propósito: añadir un paso no necesita migración ni
# toca ninguna fila. El orden es el orden en que se muestran.
PASOS: tuple[Paso, ...] = (
    Paso("como_funciona", "Ver cómo funciona el motor",
         "Qué calcula en cada paso y qué significa cada número del informe.",
         "/ayuda", deducido=False),
    Paso("primer_analisis", "Analizar tu primera subasta",
         "Con los datos del anuncio basta para empezar; lo que falte quedará "
         "declarado como carencia, no inventado.",
         "/nueva", deducido=True),
    Paso("perfil_revisado", "Revisar el perfil de inversión",
         "Los márgenes objetivo y mínimo cambian la escalera de precios entera.",
         "/configuracion", deducido=False),
    Paso("primera_alerta", "Crear una alerta de captación",
         "Para que las subastas que encajen lleguen solas en vez de buscarlas.",
         "/alertas", deducido=True),
)

CLAVES = tuple(p.clave for p in PASOS)
CLAVES_MANUALES = tuple(p.clave for p in PASOS if not p.deducido)


def _deducidos(db: Session, usuario: models.Usuario) -> dict[str, bool]:
    """Pasos que se leen de los datos reales de la organización del usuario."""
    hay_analisis = db.scalar(
        select(func.count()).select_from(models.Analisis)
        .where(models.Analisis.organizacion_id == usuario.organizacion_id)) or 0
    hay_alertas = db.scalar(
        select(func.count()).select_from(models.Alerta)
        .where(models.Alerta.usuario_id == usuario.id)) or 0
    return {"primer_analisis": hay_analisis > 0, "primera_alerta": hay_alertas > 0}


def _marcados(db: Session, usuario_id: str) -> dict[str, datetime]:
    filas = db.scalars(
        select(models.PasoOnboarding)
        .where(models.PasoOnboarding.usuario_id == usuario_id)).all()
    return {f.clave: f.completado_en for f in filas}


def estado(db: Session, usuario: models.Usuario) -> dict:
    """Checklist completa: cada paso con si está hecho y cómo se supo."""
    deducidos = _deducidos(db, usuario)
    marcados = _marcados(db, usuario.id)
    pasos = []
    for p in PASOS:
        completado = deducidos[p.clave] if p.deducido else p.clave in marcados
        pasos.append({
            "clave": p.clave, "titulo": p.titulo, "descripcion": p.descripcion,
            "accion": p.accion, "completado": completado,
            # `origen` es lo que hace honesta la checklist: distingue «lo sé porque
            # existe el dato» de «lo sé porque lo marcaste».
            "origen": "datos" if p.deducido else "declarado",
            "completado_en": (marcados.get(p.clave).isoformat()
                              if not p.deducido and p.clave in marcados else None),
        })
    hechos = sum(1 for p in pasos if p["completado"])
    return {"pasos": pasos, "completados": hechos, "total": len(pasos),
            "terminado": hechos == len(pasos)}


def marcar(db: Session, usuario_id: str, clave: str) -> bool:
    """Marca un paso manual. Idempotente. Devuelve False si la clave no es manual.

    No se puede marcar un paso deducido: su verdad está en los datos, y aceptar
    una marca sería dejar que alguien declare un hecho que el sistema puede
    comprobar por su cuenta.
    """
    if clave not in CLAVES_MANUALES:
        return False
    db.add(models.PasoOnboarding(usuario_id=usuario_id, clave=clave))
    try:
        db.flush()
    except IntegrityError:
        # Ya estaba marcado. La unicidad la impone la base, no este servicio: si
        # dos peticiones llegan a la vez, gana la restricción y no una carrera.
        db.rollback()
    return True

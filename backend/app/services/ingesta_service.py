"""Ingesta de subastas captadas (Fase 17-A): contrato → base de datos.

Único camino de entrada de una subasta al sistema. Tanto el alta manual del
router como cualquier conector automático pasan por aquí, de modo que el
scoring, el dedupe y el disparo de alertas ocurren siempre igual y en un solo
sitio.

No sabe nada de HTML: eso es `app/ingesta/`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import models
from app.engine.scoring_expres import puntuar_subasta
from app.ingesta.contratos import OrigenCaptacion, ResumenLote, SubastaCaptada
from app.services import notificaciones_service
from app.services.conocimiento_service import parametros_vigentes

log = logging.getLogger("seis.ingesta")


def _ya_existe(db: Session, captada: SubastaCaptada) -> bool:
    """Dedupe explícito, ANTES de intentar el insert.

    La restricción de unicidad de la migración 0007 es la garantía dura —la que
    sobrevive a dos ingestas simultáneas—, pero comprobar aquí evita gastar un
    `savepoint` y ensuciar el log con un IntegrityError en el caso normal, que
    es reingerir un lote donde casi todo ya está.

    Sin `identificador_externo` no se puede dedupear: dos altas manuales de la
    misma subasta sin identificador son indistinguibles de dos subastas
    distintas, y la restricción tampoco las bloquea porque en SQL los NULL no
    colisionan entre sí. Se acepta a propósito: inventar una clave por
    aproximación (valor + fecha) uniría subastas legítimamente distintas.
    """
    if not captada.identificador_externo:
        return False
    return db.query(models.Subasta).filter(
        models.Subasta.fuente_codigo == captada.fuente_codigo,
        models.Subasta.identificador_externo == captada.identificador_externo,
    ).first() is not None


def _persistir(db: Session, captada: SubastaCaptada, ahora: datetime,
               params, quien: str | None) -> models.Subasta:
    """Crea la subasta con su puntuación congelada. No hace commit."""
    datos = captada.model_dump(mode="json")
    # `ahora` explícito (cierre Fase 12, P0.3): la puntuación queda ligada a este
    # instante y no al momento en que alguien la reevalúe.
    puntuacion = puntuar_subasta(datos, params, ahora)

    subasta = models.Subasta(
        fuente_codigo=captada.fuente_codigo,
        identificador_externo=captada.identificador_externo,
        url=captada.url, valor_subasta=captada.valor_subasta,
        puja_minima=captada.puja_minima, deposito_pct=captada.deposito_pct,
        fecha_cierre=captada.fecha_cierre,
        subastas_desiertas_previas=captada.subastas_desiertas_previas,
        datos_brutos={**captada.datos_extra, "captacion": datos,
                      "score": puntuacion["score"],
                      "score_desglose": puntuacion["desglose"],
                      "score_version_parametros": puntuacion["version_parametros"],
                      "score_calculado_en": ahora.isoformat()})
    db.add(subasta)
    db.flush()                                   # asigna el id antes de auditar
    db.add(models.Auditoria(quien=quien, entidad="subasta", entidad_id=subasta.id,
                            accion="captar", delta={"fuente": captada.fuente_codigo,
                                                    "score": puntuacion["score"]}))
    return subasta


def procesar_lote(db: Session, captadas: list[SubastaCaptada], origen: OrigenCaptacion,
                  quien: str | None = None) -> tuple[ResumenLote, list[models.Subasta]]:
    """Ingiere un lote entero. Un ítem corrupto NO tumba a los demás.

    Cada ítem va en su propio `begin_nested()` (savepoint): si falla, se deshace
    solo él y el lote continúa. Es lo que separa una ingesta nocturna que mete
    199 de 200 subastas de una que no mete ninguna porque el portal cambió un
    campo en la última.

    El matcher se dispara DESPUÉS de confirmar el lote, no dentro del savepoint:
    una notificación es un efecto externo (correo, Telegram) y no puede enviarse
    por una subasta cuya inserción todavía puede deshacerse.
    """
    resumen = ResumenLote(total=len(captadas))
    nuevas: list[models.Subasta] = []
    if not captadas:
        return resumen, nuevas

    params = parametros_vigentes(db)
    ahora = datetime.now(timezone.utc)

    for i, captada in enumerate(captadas, 1):
        if _ya_existe(db, captada):
            resumen.duplicadas += 1
            continue
        try:
            with db.begin_nested():
                nuevas.append(_persistir(db, captada, ahora, params, quien))
        except (IntegrityError, OperationalError):
            # Carrera con otra ingesta simultánea: la restricción de unicidad hizo
            # su trabajo. No es un fallo, es el dedupe funcionando bajo carga.
            resumen.duplicadas += 1
        except Exception as e:                   # noqa: BLE001 — un ítem no tumba el lote
            resumen.fallidas += 1
            resumen.motivos_de_fallo.append(f"ítem {i}: {type(e).__name__}: {e}")
            log.warning("ingesta: ítem %d descartado (%s)", i, type(e).__name__)

    resumen.insertadas = len(nuevas)
    db.add(models.Auditoria(quien=quien or "plataforma", entidad="ingesta",
                            entidad_id=origen.tipo, accion="procesar_lote",
                            delta=resumen.como_dict()))
    db.commit()

    for subasta in nuevas:
        try:
            resumen.notificaciones += len(
                notificaciones_service.evaluar_subasta(db, subasta, origen))
        except Exception as e:                   # noqa: BLE001
            # Que falle una notificación no puede deshacer una ingesta ya
            # confirmada: la subasta es el dato valioso y ya está guardada.
            log.warning("ingesta: matcher falló para %s (%s)", subasta.id, type(e).__name__)

    log.info("ingesta (%s): %s", origen.tipo, resumen.como_dict())
    return resumen, nuevas

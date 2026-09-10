"""Tareas de mantenimiento periódico (Fase 11, Bloque I).

Cierran deudas que `docs/PENDIENTES.md` asigna nominalmente a esta fase: tablas
que solo crecen y nunca se podan. Corren en el planificador `beat`, que es un
servicio único por diseño (ver ADR-0007).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery

log = logging.getLogger("seis.mantenimiento")


@celery.task(name="seis.purgar")
def purgar() -> dict:
    """Higiene diaria: tokens gastados (deuda 2) y cuentas sin verificar (deuda 10).

    Las dos purgas van en `try` independientes: un fallo en una no puede impedir
    la otra ni tumbar al planificador. El log registra **solo recuentos**, nunca
    direcciones de correo: las de las cuentas sin verificar no están demostradas
    y pueden pertenecer a un tercero que jamás pidió nada.
    """
    from app.core.db import SessionLocal
    from app.services import purga_service

    resumen: dict = {}

    try:
        resumen["tokens_borrados"] = purgar_tokens_consumidos()
    except Exception:                                    # noqa: BLE001
        log.exception("Fallo purgando token_consumido")
        resumen["tokens_borrados"] = 0

    db = SessionLocal()
    try:
        resultado = purga_service.purgar_cuentas_sin_verificar(db)
        resumen.update(modo=resultado.modo, candidatas=resultado.candidatas,
                       cuentas_borradas=resultado.cuentas_borradas,
                       organizaciones_borradas=resultado.organizaciones_borradas,
                       omitidas=resultado.omitidas_en_revision,
                       # `fallidas` sí llega al resumen: es el recuento que
                       # delata una purga averiada, y omitirlo dejaba el
                       # diagnóstico solo en el log del worker.
                       fallidas=resultado.fallidas,
                       huerfanas=resultado.organizaciones_huerfanas_detectadas)
    except Exception:                                    # noqa: BLE001
        db.rollback()
        log.exception("Fallo purgando cuentas sin verificar")
    finally:
        db.close()

    return resumen


def purgar_tokens_consumidos() -> int:
    """Borra los `jti` gastados cuya vida útil ya no puede solaparse con nada.

    `token_consumido` guarda una fila por cada enlace de verificación, reseteo o
    baja consumido, **para siempre** (deuda 2 de `docs/PENDIENTES.md`). En un
    sistema con altas continuas es una tabla que solo crece.

    **De qué depende el plazo.** La retención tiene que superar el TTL del token
    de un solo uso más largo, porque el `jti` es lo ÚNICO que impide reutilizar
    un enlace: borrar la fila mientras el token sigue vigente devuelve el uso
    único que la Fase 10 cerró.

    Y «el más largo» **no es el que parece**. El token de baja dura 30 días, pero
    `/notificaciones/baja` no llama a `marcar_jti` —darse de baja dos veces es
    inocuo—, de modo que jamás llega a esta tabla. Los únicos que sí llegan son
    los de verificación (24 h) y reseteo (1 h), ambos por `_consumir_token` en
    `app/api/auth.py`, que es el **único** llamante de `marcar_jti`. El TTL
    máximo real es por tanto de 24 horas, no de 30 días.

    El valor por defecto (45 días) es deliberadamente holgado, y `config.py`
    aborta el arranque si alguien lo baja por debajo del TTL real.

    Devuelve el número de filas borradas, para que quede en el log de la tarea.
    """
    from app import models
    from app.core.config import get_settings
    from app.core.db import SessionLocal

    dias = get_settings().purga_tokens_dias
    corte = datetime.now(timezone.utc) - timedelta(days=dias)

    db = SessionLocal()
    try:
        borrados = (db.query(models.TokenConsumido)
                    .filter(models.TokenConsumido.consumido_en < corte)
                    .delete(synchronize_session=False))
        db.commit()
    except Exception:                                    # noqa: BLE001
        # Una tarea de mantenimiento que revienta no debe tumbar el planificador
        # ni dejar la transacción abierta: se registra y se devuelve 0.
        db.rollback()
        log.exception("Fallo purgando token_consumido")
        return 0
    finally:
        db.close()

    if borrados:
        log.info("Purga de token_consumido: %d filas anteriores a %s",
                 borrados, corte.isoformat())
    return borrados


@celery.task(name="seis.vigilancia_fuentes")
def vigilancia_fuentes() -> dict:
    """Avisa al superadministrador si una fuente activa lleva demasiado en silencio.

    Es la única señal automática de que un conector se rompió. Sin ella, el modo
    de fallo es el peor posible: el sistema sigue funcionando, las alertas siguen
    activas y sencillamente no llega nada — indistinguible, desde fuera, de que
    no haya subastas nuevas.

    No repite el aviso mientras siga pendiente uno anterior de la misma fuente:
    una fuente rota durante una semana debe producir un aviso, no siete.
    """
    from app.core.db import SessionLocal
    from app.services import vigilancia_service

    db = SessionLocal()
    try:
        return vigilancia_service.revisar_fuentes(db)
    except Exception as e:                       # noqa: BLE001 — nunca tumbar el planificador
        log.warning("vigilancia_fuentes: %s: %s", type(e).__name__, e)
        return {"error": type(e).__name__}
    finally:
        db.close()


@celery.task(name="seis.borrados_rgpd")
def borrados_rgpd() -> dict:
    """Ejecuta los borrados cuya gracia de 14 días ya venció (Fase 14).

    Va en tarea propia y no dentro de `seis.purgar` aunque comparta camino de
    borrado, porque son dos cosas distintas con dos razones distintas para
    fallar: la purga limpia cuentas que nadie reclamó, esto ejecuta una petición
    expresa de una persona. Mezclarlas haría que un fallo en una retrasara la
    otra, y retrasar un derecho ejercido no es lo mismo que retrasar higiene.

    Corre DESPUÉS de la purga (05:00 frente a 04:30) por si acaso comparten
    candidatas: una cuenta sin verificar que además pidió el borrado la limpia
    la purga y aquí ya no aparece.
    """
    from app.core.db import SessionLocal
    from app.services import cuenta_service

    db = SessionLocal()
    try:
        return cuenta_service.ejecutar_borrados_vencidos(db)
    except Exception:                                    # noqa: BLE001
        log.exception("Fallo ejecutando los borrados RGPD vencidos")
        return {"error": True}
    finally:
        db.close()

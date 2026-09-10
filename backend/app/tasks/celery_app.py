"""Celery — cola para análisis en lote y re-análisis por eventos (F2)."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
celery = Celery("seis", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.task_serializer = "json"
celery.conf.result_serializer = "json"
celery.conf.accept_content = ["json"]
if settings.celery_task_always_eager:
    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True

# Fase 12 — beat: polling de Telegram (si hay token) y digest horario
# Fase 11 (Bloque I) — mantenimiento diario de las tablas que solo crecen
celery.conf.beat_schedule = {
    "telegram-polling": {"task": "seis.telegram_polling", "schedule": 30.0},
    "digest-horario": {"task": "seis.digest", "schedule": 3600.0},
    # `crontab` y NO un intervalo de 86400 s: `beat` no persiste su
    # `celerybeat-schedule` —vive en la capa efímera del contenedor—, de modo que
    # con un intervalo cada recreación reiniciaría la cuenta de 24 horas y en un
    # despliegue con recreaciones frecuentes la purga podría no ejecutarse nunca.
    # Un horario anclado al reloj no tiene ese problema.
    "purga-diaria": {"task": "seis.purgar", "schedule": crontab(hour=4, minute=30)},
    # Mismo motivo que la purga para usar `crontab` y no un intervalo: `beat` no
    # persiste su horario entre recreaciones del contenedor.
    "vigilancia-fuentes": {"task": "seis.vigilancia_fuentes",
                           "schedule": crontab(hour=9, minute=0)},
    # Después de la purga (04:30) a propósito: si una cuenta sin verificar
    # además pidió el borrado, la limpia la purga y aquí ya no aparece.
    "borrados-rgpd": {"task": "seis.borrados_rgpd",
                      "schedule": crontab(hour=5, minute=0)},
}
celery.autodiscover_tasks(["app.tasks"], related_name="notificaciones_tasks")
celery.autodiscover_tasks(["app.tasks"], related_name="mantenimiento_tasks")


@celery.task(name="seis.analizar")
def analizar_task(payload: dict, organizacion_id: str | None = None,
                  quien: str | None = None) -> dict:
    from app.core.db import SessionLocal
    from app.engine.contracts import AnalisisInput
    from app.services.analisis_service import crear_analisis

    db = SessionLocal()
    try:
        analisis_id, resultado = crear_analisis(
            db, AnalisisInput.model_validate(payload),
            quien=quien, organizacion_id=organizacion_id)
        return {"id": analisis_id, "semaforo": resultado.decision.semaforo}
    finally:
        db.close()

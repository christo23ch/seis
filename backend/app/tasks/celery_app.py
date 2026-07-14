"""Celery — cola para análisis en lote y re-análisis por eventos (F2)."""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery = Celery("seis", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.task_serializer = "json"
celery.conf.result_serializer = "json"
celery.conf.accept_content = ["json"]
if settings.celery_task_always_eager:
    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True


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

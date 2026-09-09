"""Fase 17-A — Vigilancia de fuentes en silencio.

El modo de fallo más peligroso de la ingesta no produce error: un conector que
deja de reconocer el HTML sigue corriendo, sigue registrando su ejecución y
simplemente no trae nada. Desde fuera es indistinguible de que el portal no haya
publicado. Estos tests fijan que eso se avisa, y que se avisa **una vez**.
"""
from __future__ import annotations

from app.ingesta.contratos import OrigenCaptacion, SubastaCaptada


# ─────────────────────── Vigilancia de fuentes ───────────────────────

def test_una_fuente_en_silencio_avisa_al_superadministrador_una_sola_vez(api):
    """Sin este aviso, un conector roto es indistinguible de que no haya subastas."""
    from app.core.db import SessionLocal
    from app.services import vigilancia_service
    from app import models

    db = SessionLocal()
    try:
        db.add(models.FuenteSubasta(codigo="fuente_muda"))
        db.commit()

        primero = vigilancia_service.revisar_fuentes(db)
        assert "fuente_muda" in primero["en_silencio"]
        assert primero["avisos_creados"] >= 1

        # Una fuente rota una semana debe producir un aviso, no siete.
        segundo = vigilancia_service.revisar_fuentes(db)
        assert segundo["avisos_creados"] == 0

        avisos = db.query(models.Notificacion).filter(
            models.Notificacion.asunto.like("%fuente_muda%")).count()
        assert avisos == 1
    finally:
        db.close()


def test_una_fuente_con_subastas_recientes_no_avisa(api):
    from app.core.db import SessionLocal
    from app.services import ingesta_service, vigilancia_service
    from app import models

    db = SessionLocal()
    try:
        db.add(models.FuenteSubasta(codigo="fuente_viva"))
        db.commit()
        ingesta_service.procesar_lote(
            db, [SubastaCaptada(fuente_codigo="fuente_viva",
                                identificador_externo="VIVA-1", valor_subasta=100000)],
            OrigenCaptacion.plataforma())

        resultado = vigilancia_service.revisar_fuentes(db)

        assert "fuente_viva" not in resultado["en_silencio"]
    finally:
        db.close()

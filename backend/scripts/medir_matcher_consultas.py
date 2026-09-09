"""Cuántas CONSULTAS y cuántas FILAS toca un lote. Lo que no depende de la máquina."""
import os, sys, uuid
os.environ.setdefault("SEIS_ENV", "test"); os.environ.setdefault("JWT_SECRET", "x"*48)
os.environ.setdefault("ADMIN_PASSWORD", "Admin-Test-1234"); sys.path.insert(0, ".")
from sqlalchemy import event
from app.core.db import Base, SessionLocal, engine
from app import models
from app.ingesta.contratos import OrigenCaptacion, SubastaCaptada
from app.services import ingesta_service

CUENTA = {"select_alerta": 0, "select_pref": 0, "total": 0}

@event.listens_for(engine, "before_cursor_execute")
def _contar(conn, cursor, sql, params, ctx, many):
    CUENTA["total"] += 1
    s = sql.lower()
    if "from alerta" in s: CUENTA["select_alerta"] += 1
    if "from preferencias_notificacion" in s: CUENTA["select_pref"] += 1

def medir(total_alertas, tam_lote, casan, modo):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    db = SessionLocal()
    org = models.Organizacion(nombre="O"); db.add(org); db.flush()
    for i in range(total_alertas):
        u = models.Usuario(email=f"u{i}-{uuid.uuid4().hex[:6]}@e.com", hash_pwd="x",
                           rol="analista", organizacion_id=org.id)
        db.add(u); db.flush()
        db.add(models.PreferenciasNotificacion(usuario_id=u.id, canales=["email"], modo=modo))
        db.add(models.Alerta(usuario_id=u.id, nombre=f"A{i}", activa=True,
                             criterios={"fuente": "judicial_boe"} if i < casan else {"fuente": "no"}))
    db.commit()
    for k in CUENTA: CUENTA[k] = 0
    lote = [SubastaCaptada(fuente_codigo="judicial_boe", identificador_externo=f"S{i}",
                           valor_subasta=100000.0) for i in range(tam_lote)]
    r, _ = ingesta_service.procesar_lote(db, lote, OrigenCaptacion.plataforma())
    print(f"  alertas={total_alertas} lote={tam_lote} casan={casan} modo={modo}: "
          f"total={CUENTA['total']} · SELECT alerta={CUENTA['select_alerta']} "
          f"(filas leídas ≈ {CUENTA['select_alerta']*total_alertas}) · "
          f"SELECT preferencias={CUENTA['select_pref']} · notif={r.notificaciones}", flush=True)
    db.close()

medir(1000, 50, 100, "digest_diario")
medir(1000, 50, 100, "instantaneo")
medir(1000, 10, 100, "digest_diario")

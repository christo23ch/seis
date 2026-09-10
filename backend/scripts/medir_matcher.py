"""Coste del matcher con ingesta de plataforma (condición 4 de la Fase 17-A).

Cada medición parte de una base VACÍA: en la primera versión de este script las
alertas se acumulaban entre bloques y las cifras no medían lo que decían medir.

Separa emparejar (CPU + consultas) de despachar (I/O por notificación), porque
son magnitudes distintas y solo una de ellas escala mal.
"""
import os, sys, time, uuid
os.environ.setdefault("SEIS_ENV", "test")
os.environ.setdefault("JWT_SECRET", "x" * 48)
os.environ.setdefault("ADMIN_PASSWORD", "Admin-Test-1234")
sys.path.insert(0, ".")

from app.core.db import Base, SessionLocal, engine
from app import models
from app.ingesta.contratos import OrigenCaptacion, SubastaCaptada
from app.services import ingesta_service


def limpiar():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def sembrar(db, total_alertas, n_orgs, casan, modo):
    """`casan`: cuántas de las alertas tienen criterios que casarán con el lote.
    `modo`: preferencia de notificación de todos los usuarios."""
    orgs = []
    for o in range(n_orgs):
        org = models.Organizacion(nombre=f"Org {o}")
        db.add(org); orgs.append(org)
    db.flush()
    for i in range(total_alertas):
        u = models.Usuario(email=f"u{i}-{uuid.uuid4().hex[:6]}@ej.com", hash_pwd="x",
                           nombre="U", rol="analista", organizacion_id=orgs[i % n_orgs].id)
        db.add(u); db.flush()
        db.add(models.PreferenciasNotificacion(usuario_id=u.id, canales=["email"], modo=modo))
        db.add(models.Alerta(usuario_id=u.id, nombre=f"A{i}", activa=True,
                             criterios={"fuente": "judicial_boe"} if i < casan
                                       else {"fuente": "no_casa"}))
    db.commit()


def medir(total_alertas, tam_lote, casan, modo="digest_diario", n_orgs=10):
    limpiar()
    db = SessionLocal()
    try:
        sembrar(db, total_alertas, n_orgs, casan, modo)
        lote = [SubastaCaptada(fuente_codigo="judicial_boe", identificador_externo=f"S-{i}",
                               valor_subasta=100000.0 + i) for i in range(tam_lote)]
        t0 = time.perf_counter()
        resumen, _ = ingesta_service.procesar_lote(db, lote, OrigenCaptacion.plataforma())
        dt = time.perf_counter() - t0
        print(f"  alertas={total_alertas:>5} lote={tam_lote:>3} casan={casan:>4} "
              f"modo={modo:<13} → {dt:6.2f} s  notif={resumen.notificaciones:>6} "
              f"({dt / tam_lote * 1000:6.1f} ms/subasta)", flush=True)
        return dt
    finally:
        db.close()


if __name__ == "__main__":
    print("A) Solo emparejar (ninguna alerta casa ⇒ 0 notificaciones, 0 despacho)")
    for a in (100, 500, 1000, 2000, 5000):
        medir(a, 50, casan=0)

    print("\nB) Emparejar + crear notificaciones, SIN despacho (todos en digest)")
    for a in (100, 500, 1000):
        medir(a, 50, casan=a // 10)

    print("\nC) Lo mismo, CON despacho instantáneo (el envío entra en la ingesta)")
    for a in (100, 500, 1000):
        medir(a, 50, casan=a // 10, modo="instantaneo")

    print("\nD) Tamaño del lote, 1000 alertas, 10 % casan, digest")
    for n in (10, 50, 200):
        medir(1000, n, casan=100)

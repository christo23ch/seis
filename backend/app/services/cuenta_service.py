"""Derechos del titular sobre su cuenta (Fase 14, RGPD).

Tres cosas: exportar sus datos, pedir el borrado y arrepentirse dentro de la
gracia. El borrado en sí NO se implementa aquí — lo hace `borrado_service`, que
es el único camino, compartido con la purga de cuentas sin verificar. Aquí solo
está **quién** puede borrarse y **cuándo**.

**La gracia no es cortesía, es la única defensa que queda.** El borrado es
irreversible y no hay copia que restaurar por usuario: quien lo pide en caliente
—o quien entra en una cuenta ajena— destruye datos que no vuelven. Catorce días
convierten un clic irreversible en algo que el titular real puede deshacer.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models
from app.legal import textos
from app.services.borrado_service import borrar_datos_de_usuario

log = logging.getLogger("seis.cuenta")

DIAS_DE_GRACIA = 14


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _aware(momento: datetime | None) -> datetime | None:
    """SQLite devuelve datetimes naive; compararlos con aware lanza TypeError."""
    if momento is None:
        return None
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


# ───────────────────────────── Exportación ─────────────────────────────

def exportar_datos(db: Session, usuario: models.Usuario) -> dict:
    """Todo lo que el sistema guarda SOBRE ESTA PERSONA. Nada más.

    Dos exclusiones deliberadas, porque en una exportación lo que sobra es tan
    importante como lo que falta:

    - **`hash_pwd` no sale.** No aporta nada al titular y es material de ataque.
    - **`Analisis` no sale.** Cuelga de `organizacion_id` y no tiene autor: no
      es atribuible a una persona, es de la organización. Incluirlo convertiría
      el derecho de acceso de un miembro en una vía para llevarse el trabajo de
      toda su organización — y en una organización de varias personas, datos de
      terceros. El derecho de acceso cubre los datos personales del solicitante,
      no todo lo que pueda ver.

    Todo lo que se devuelve está filtrado por `usuario_id` o por su dirección.
    Nada se filtra por organización, que es lo que hace imposible que aquí se
    cuele algo de otro tenant: no hay ninguna consulta que pueda alcanzarlo.
    """
    marca = f"anonimizado:{usuario.id}"
    consentimientos = (db.query(models.Consentimiento)
                       .filter(models.Consentimiento.usuario_id == usuario.id)
                       .order_by(models.Consentimiento.otorgado_en).all())
    alertas = db.query(models.Alerta).filter(
        models.Alerta.usuario_id == usuario.id).all()
    notificaciones = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario.id).all()
    preferencias = db.get(models.PreferenciasNotificacion, usuario.id)
    auditoria = (db.query(models.Auditoria)
                 .filter(models.Auditoria.quien.in_([usuario.email, marca]))
                 .order_by(models.Auditoria.cuando).all())

    return {
        "generado_en": _ahora().isoformat(),
        "cuenta": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "rol": usuario.rol,
            "rol_en_la_organizacion": usuario.rol_org,
            "activo": usuario.activo,
            "email_verificado": usuario.email_verificado,
            "creado_en": usuario.creado_en.isoformat() if usuario.creado_en else None,
            "borrado_solicitado_en": (
                usuario.borrado_solicitado_en.isoformat()
                if usuario.borrado_solicitado_en else None),
        },
        "consentimientos": [
            {"tipo": c.tipo, "version": c.version, "otorgado": c.otorgado,
             "otorgado_en": c.otorgado_en.isoformat() if c.otorgado_en else None}
            for c in consentimientos],
        "preferencias_de_notificacion": (
            {"modo": preferencias.modo, "canales": preferencias.canales,
             "comunicaciones_activas": preferencias.comunicaciones_activas}
            if preferencias else None),
        "alertas": [{"nombre": a.nombre, "criterios": a.criterios, "activa": a.activa}
                    for a in alertas],
        "notificaciones": [
            {"asunto": n.asunto, "cuerpo": n.cuerpo, "estado": n.estado,
             "creada_en": n.creado_en.isoformat() if n.creado_en else None}
            for n in notificaciones],
        "auditoria": [
            {"cuando": a.cuando.isoformat() if a.cuando else None,
             "accion": a.accion, "entidad": a.entidad, "delta": a.delta}
            for a in auditoria],
    }


# ─────────────────────── Borrado a petición del titular ───────────────────────

def solicitar_borrado(db: Session, usuario: models.Usuario) -> datetime:
    """Marca la cuenta para borrar y devuelve cuándo se ejecutará.

    Idempotente: pedirlo dos veces no reinicia la cuenta atrás. Si la reiniciara,
    bastaría con repetir la petición para aplazar indefinidamente un borrado
    —o, al revés, un cliente que reintentara por su cuenta alargaría la espera
    sin que nadie lo pidiera.
    """
    if usuario.borrado_solicitado_en is None:
        usuario.borrado_solicitado_en = _ahora()
        db.add(models.Auditoria(
            quien=usuario.email, entidad="usuario", entidad_id=usuario.email,
            accion="borrado_solicitado", delta={"dias_de_gracia": DIAS_DE_GRACIA}))
        db.commit()
        db.refresh(usuario)
    return fecha_de_ejecucion(usuario)


def cancelar_borrado(db: Session, usuario: models.Usuario) -> bool:
    """Retira la solicitud. Devuelve si había algo que retirar."""
    if usuario.borrado_solicitado_en is None:
        return False
    usuario.borrado_solicitado_en = None
    db.add(models.Auditoria(quien=usuario.email, entidad="usuario",
                            entidad_id=usuario.email,
                            accion="borrado_cancelado", delta={}))
    db.commit()
    db.refresh(usuario)
    return True


def fecha_de_ejecucion(usuario: models.Usuario) -> datetime | None:
    solicitado = _aware(usuario.borrado_solicitado_en)
    return solicitado + timedelta(days=DIAS_DE_GRACIA) if solicitado else None


def borrados_vencidos(db: Session, *, ahora: datetime | None = None,
                      limite: int = 500) -> list[str]:
    """Ids de cuentas cuya gracia ya expiró."""
    corte = (ahora or _ahora()) - timedelta(days=DIAS_DE_GRACIA)
    filas = (db.query(models.Usuario.id)
             .filter(models.Usuario.borrado_solicitado_en.isnot(None),
                     models.Usuario.borrado_solicitado_en < corte)
             .order_by(models.Usuario.borrado_solicitado_en)
             .limit(limite).all())
    return [f[0] for f in filas]


def ejecutar_borrado(db: Session, usuario_id: str, *,
                     ahora: datetime | None = None) -> bool:
    """Borra de verdad una cuenta cuya gracia venció. Transacción propia.

    **Revalida la gracia dentro de la transacción**, igual que hace la purga con
    su predicado y por el mismo motivo: la selección ocurre fuera, y el titular
    puede haber cancelado entre ambos momentos. Sin esta comprobación, cancelar
    justo antes de que corriera la tarea no serviría de nada.
    """
    ahora = ahora or _ahora()
    usuario = (db.query(models.Usuario)
               .filter(models.Usuario.id == usuario_id)
               .with_for_update(skip_locked=True)     # ignorado en SQLite
               .one_or_none())
    if usuario is None:
        db.rollback()
        return False

    solicitado = _aware(usuario.borrado_solicitado_en)
    if solicitado is None or solicitado > ahora - timedelta(days=DIAS_DE_GRACIA):
        # Canceló, o todavía está en gracia. No es un fallo: es la gracia
        # haciendo lo suyo.
        db.rollback()
        return False

    organizacion_borrada = borrar_datos_de_usuario(db, usuario)
    # `quien` es el sistema y `entidad_id` el UUID: la constancia de que se borró
    # no puede reintroducir la dirección que se acaba de anonimizar.
    db.add(models.Auditoria(
        quien="sistema:rgpd", entidad="usuario", entidad_id=usuario_id,
        accion="borrado_a_peticion",
        delta={"organizacion_borrada": organizacion_borrada,
               "dias_de_gracia": DIAS_DE_GRACIA}))
    db.commit()
    return True


def ejecutar_borrados_vencidos(db: Session, *, ahora: datetime | None = None) -> dict:
    """Punto de entrada de la tarea programada."""
    ahora = ahora or _ahora()
    vencidos = borrados_vencidos(db, ahora=ahora)
    borrados = fallidos = 0
    for usuario_id in vencidos:
        try:
            if ejecutar_borrado(db, usuario_id, ahora=ahora):
                borrados += 1
        except Exception:                              # noqa: BLE001
            # Un fallo en una cuenta no puede llevarse por delante a las demás.
            db.rollback()
            log.exception("Fallo borrando una cuenta vencida; se continúa")
            fallidos += 1
    if fallidos:
        log.error("Borrado RGPD: %d cuentas FALLARON. Puede haber una tabla hija "
                  "que el borrado no cubre.", fallidos)
    log.info("Borrado RGPD: %d vencidas, %d borradas, %d fallidas.",
             len(vencidos), borrados, fallidos)
    return {"vencidas": len(vencidos), "borradas": borrados, "fallidas": fallidos}


# ───────────────────────────── Consentimientos ─────────────────────────────

def registrar_consentimientos(db: Session, usuario: models.Usuario,
                              otorgados: dict[str, bool]) -> list[models.Consentimiento]:
    """Guarda una fila por consentimiento. No comitea: lo hace el llamante.

    Se guardan también los NEGADOS. Un «no» explícito es tan demostrable como un
    «sí», y sin él no habría forma de distinguir a quien rechazó las
    comunicaciones comerciales de quien nunca vio la casilla.
    """
    creados = []
    for tipo in textos.TIPOS_VALIDOS:
        if tipo not in otorgados:
            continue
        c = models.Consentimiento(
            usuario_id=usuario.id, tipo=tipo,
            version=textos.TEXTOS[tipo].version,
            otorgado=bool(otorgados[tipo]))
        db.add(c)
        creados.append(c)
    return creados

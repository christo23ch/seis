"""Fase 12 — Servicio de notificaciones: preferencias, Telegram, matcher, digest y baja."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models
from app.ingesta.contratos import OrigenCaptacion
from app.core.config import get_settings
from app.core.security import crear_token_proposito
from app.notificadores import Mensaje, obtener_notificadores
from app.notificadores.registro import CANALES_VALIDOS

log = logging.getLogger("seis.notificaciones")

CODIGO_TELEGRAM_MINUTOS = 10
MODOS_VALIDOS = ("instantaneo", "digest_diario", "digest_semanal")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite pierde el tzinfo al persistir: normaliza a UTC para comparar."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── Preferencias ────────────────────────────────────────────────────────────

def obtener_preferencias(db: Session, usuario_id: str) -> models.PreferenciasNotificacion:
    pref = db.get(models.PreferenciasNotificacion, usuario_id)
    if not pref:
        pref = models.PreferenciasNotificacion(usuario_id=usuario_id, canales=["email"])
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def actualizar_preferencias(db: Session, usuario: models.Usuario, cambios: dict,
                            quien: str | None = None) -> models.PreferenciasNotificacion:
    pref = obtener_preferencias(db, usuario.id)
    if "canales" in cambios:
        canales = [c for c in cambios["canales"] if c in CANALES_VALIDOS]
        pref.canales = canales
    if "modo" in cambios:
        if cambios["modo"] not in MODOS_VALIDOS:
            raise ValueError("modo inválido")
        pref.modo = cambios["modo"]
    for campo in ("hora_digest", "silencio_inicio", "silencio_fin"):
        if campo in cambios:
            valor = cambios[campo]
            if valor is not None and not (0 <= int(valor) <= 23):
                raise ValueError(f"{campo} debe estar entre 0 y 23")
            setattr(pref, campo, valor)
    db.add(models.Auditoria(quien=quien or usuario.email, entidad="preferencias_notificacion",
                            entidad_id=usuario.id, accion="actualizar", delta=cambios))
    db.commit()
    db.refresh(pref)
    return pref


# ── Vinculación Telegram ────────────────────────────────────────────────────

def generar_codigo_telegram(db: Session, usuario: models.Usuario) -> models.CodigoTelegram:
    """Código de 6 dígitos, caducidad 10 min. Invalida los códigos previos del usuario."""
    db.query(models.CodigoTelegram).filter(
        models.CodigoTelegram.usuario_id == usuario.id,
        models.CodigoTelegram.usado.is_(False)).update({"usado": True})
    codigo = models.CodigoTelegram(
        codigo=f"{secrets.randbelow(1_000_000):06d}",
        usuario_id=usuario.id,
        expira_en=_now() + timedelta(minutes=CODIGO_TELEGRAM_MINUTOS))
    db.add(codigo)
    db.commit()
    db.refresh(codigo)
    return codigo


def vincular_telegram(db: Session, codigo_texto: str, chat_id: str) -> models.Usuario | None:
    """Consume el código (un solo uso) y guarda el chat_id. None si inválido/caducado."""
    codigo = db.get(models.CodigoTelegram, codigo_texto.strip())
    if not codigo or codigo.usado or _aware(codigo.expira_en) < _now():
        return None
    codigo.usado = True
    usuario = db.get(models.Usuario, codigo.usuario_id)
    if not usuario:
        return None
    pref = obtener_preferencias(db, usuario.id)
    pref.telegram_chat_id = str(chat_id)
    if "telegram" not in pref.canales:
        pref.canales = [*pref.canales, "telegram"]
    db.add(models.Auditoria(quien=usuario.email, entidad="preferencias_notificacion",
                            entidad_id=usuario.id, accion="vincular_telegram",
                            delta={"chat_id": str(chat_id)}))
    db.commit()
    return usuario


def desvincular_telegram(db: Session, usuario: models.Usuario) -> None:
    pref = obtener_preferencias(db, usuario.id)
    pref.telegram_chat_id = None
    pref.canales = [c for c in pref.canales if c != "telegram"]
    db.add(models.Auditoria(quien=usuario.email, entidad="preferencias_notificacion",
                            entidad_id=usuario.id, accion="desvincular_telegram", delta={}))
    db.commit()


# ── Baja firmada ────────────────────────────────────────────────────────────

def enlace_baja(email: str) -> str:
    token = crear_token_proposito(email, "baja", horas=24 * 30)
    return f"{get_settings().frontend_url}/baja?token={token}"


def dar_de_baja(db: Session, email: str) -> bool:
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email.lower()).first()
    if not usuario:
        return False
    pref = obtener_preferencias(db, usuario.id)
    pref.comunicaciones_activas = False
    db.add(models.Auditoria(quien=email, entidad="preferencias_notificacion",
                            entidad_id=usuario.id, accion="baja_comunicaciones", delta={}))
    db.commit()
    return True


# ── Matcher de alertas ──────────────────────────────────────────────────────

def casa_alerta(alerta: models.Alerta, subasta: models.Subasta) -> bool:
    """Evalúa los criterios de la alerta contra la subasta (todos deben cumplirse)."""
    c = alerta.criterios or {}
    if c.get("fuente") and c["fuente"] != subasta.fuente_codigo:
        return False
    if c.get("valor_max") is not None and float(subasta.valor_subasta) > float(c["valor_max"]):
        return False
    if c.get("score_min") is not None:
        score = (subasta.datos_brutos or {}).get("score")
        # P4: sin score la subasta NO casa un filtro score_min (la ausencia penaliza).
        if score is None or int(score) < int(c["score_min"]):
            return False
    return True


def evaluar_subasta(db: Session, subasta: models.Subasta,
                    origen: OrigenCaptacion) -> list[models.Notificacion]:
    """Casa la subasta con las alertas activas y crea notificaciones.

    Modo instantáneo ⇒ intenta el envío inmediato (respetando franja de silencio);
    modos digest ⇒ la notificación queda pendiente para la tarea beat.

    EL ALCANCE LO DECIDE `origen`, Y ES EXPLÍCITO (Fase 17-A, ADR-0011):

    - `OrigenCaptacion.manual(org)` — un usuario capta a mano. Se evalúan solo
      las alertas de SU organización. Es la regla de la Fase 12 (P0.2, corrige
      H1) y sigue intacta: sin ella, un analista de A dispararía notificaciones
      privadas hacia usuarios de B, C y D con solo captar una subasta.
    - `OrigenCaptacion.plataforma()` — un conector automático capta. Se evalúan
      las alertas de TODAS las organizaciones.

    Por qué la segunda no rompe el aislamiento de la Fase 9: el invariante que
    aquella protege es que ninguna acción de un TENANT produzca efectos
    observables en otro, y una ingesta automática no es un acto de ningún
    tenant. El BOE no es un tenant.

    Antes esto era un `organizacion_id: str | None` y `None` era una trampa: el
    filtro `Usuario.organizacion_id == None` no significa «todas» sino «los
    usuarios sin organización», que no es nadie. Una ingesta automática que
    pasara `None` no habría notificado a NADIE, en silencio, sin romper ningún
    test. De ahí que ahora el tipo obligue a elegir.

    Las entidades `Alerta` y `Notificacion` no tienen columna de organización
    propia por decisión de producto: el eje de tenant se deriva vía `Usuario`.

    Nada de esto restringe el catálogo compartido: `Subasta` sigue sin columna
    de organización y `GET /subastas` sigue siendo legible por cualquier usuario
    de cualquier organización. Lo que el origen decide es el alcance del EFECTO
    PRIVADO (la notificación), no la visibilidad del dato.

    Alcance ampliado tampoco significa datos compartidos: con origen plataforma
    cada usuario recibe SU aviso sobre un dato común, construido únicamente con
    su propia alerta y la subasta. El cuerpo no lleva nada de otra organización,
    y hay un test que falla si alguien lo rompe
    (`test_una_notificacion_de_plataforma_no_contiene_datos_de_otra_organizacion`).

    Trade-off que la Fase 12 asumió y la 17-A revisa: aquella regla decía que si
    ningún usuario de B vuelve a captar la misma subasta, sus alertas no se
    disparan. Con captación automática ese "si nadie la capta" pasa a ser el caso
    normal —el conector capta por todos—, y mantenerlo dejaría las alertas
    inertes. Se revisa solo para el origen plataforma; para el manual sigue
    vigente palabra por palabra. Ver `30-Decisiones/ADR/ADR-0011`.
    """
    creadas: list[models.Notificacion] = []
    consulta = (db.query(models.Alerta)
                .join(models.Usuario, models.Alerta.usuario_id == models.Usuario.id)
                .filter(models.Alerta.activa.is_(True)))
    if origen.tipo == "manual":
        # El acto es de un tenant: su efecto no sale de su organización.
        consulta = consulta.filter(models.Usuario.organizacion_id == origen.organizacion_id)
    alertas = consulta.all()
    for alerta in alertas:
        if not casa_alerta(alerta, subasta):
            continue
        score = (subasta.datos_brutos or {}).get("score")
        cuerpo = (f"Nueva subasta captada que casa con su alerta «{alerta.nombre}»:\n"
                  f"Fuente: {subasta.fuente_codigo}\n"
                  f"Valor de subasta: {float(subasta.valor_subasta):,.0f} €\n"
                  + (f"Puntuación orientativa: {score}/100\n" if score is not None else "")
                  + f"Detalle: {get_settings().frontend_url}/subastas")
        n = models.Notificacion(usuario_id=alerta.usuario_id, alerta_id=alerta.id,
                                asunto=f"SEIS — Subasta que casa con «{alerta.nombre}»",
                                cuerpo=cuerpo)
        db.add(n)
        creadas.append(n)
    db.commit()

    for n in creadas:
        pref = obtener_preferencias(db, n.usuario_id)
        if pref.modo == "instantaneo" and not _en_silencio(pref):
            enviar_notificacion(db, n, pref)
    return creadas


def _en_silencio(pref: models.PreferenciasNotificacion,
                 ahora: datetime | None = None) -> bool:
    if pref.silencio_inicio is None or pref.silencio_fin is None:
        return False
    hora = (ahora or _now()).hour
    ini, fin = pref.silencio_inicio, pref.silencio_fin
    if ini <= fin:
        return ini <= hora < fin
    return hora >= ini or hora < fin                       # franja que cruza medianoche


def enviar_notificacion(db: Session, n: models.Notificacion,
                        pref: models.PreferenciasNotificacion) -> bool:
    """Envía por los canales activos del usuario. Nunca lanza; marca el estado."""
    if not pref.comunicaciones_activas:
        n.estado = "enviada"                               # baja: se consume sin enviar
        n.enviado_en = _now()
        db.commit()
        return False
    usuario = db.get(models.Usuario, n.usuario_id)
    if not usuario:
        return False
    usuario._telegram_chat_id = pref.telegram_chat_id      # transporte para el notificador
    mensaje = Mensaje(asunto=n.asunto, cuerpo=n.cuerpo,
                      enlace_baja=enlace_baja(usuario.email))
    exito = False
    for notificador in obtener_notificadores(pref.canales):
        if notificador.enviar(usuario, mensaje):
            exito = True
    n.estado = "enviada" if exito else "pendiente"
    if exito:
        n.enviado_en = _now()
    db.commit()
    return exito


# ── Digest ──────────────────────────────────────────────────────────────────

def construir_digest(notificaciones: list[models.Notificacion], periodo: str) -> Mensaje:
    """Agrupa N notificaciones pendientes en UN solo mensaje en español."""
    etiqueta = "diario" if periodo == "digest_diario" else "semanal"
    lineas = [f"Resumen {etiqueta} de SEIS — {len(notificaciones)} novedad(es):", ""]
    for i, n in enumerate(notificaciones, 1):
        lineas.append(f"{i}. {n.asunto}")
        lineas.extend(f"   {linea}" for linea in n.cuerpo.splitlines() if linea)
        lineas.append("")
    return Mensaje(asunto=f"SEIS — Resumen {etiqueta} ({len(notificaciones)} novedades)",
                   cuerpo="\n".join(lineas))


def enviar_digest_usuario(db: Session, usuario: models.Usuario,
                          pref: models.PreferenciasNotificacion) -> int:
    """Envía en un solo mensaje todas las pendientes del usuario. Devuelve cuántas agrupó."""
    pendientes = (db.query(models.Notificacion)
                  .filter(models.Notificacion.usuario_id == usuario.id,
                          models.Notificacion.estado == "pendiente")
                  .order_by(models.Notificacion.creado_en).all())
    if not pendientes:
        return 0
    if not pref.comunicaciones_activas:
        for n in pendientes:                               # baja: consumir sin enviar
            n.estado = "enviada"
            n.enviado_en = _now()
        db.commit()
        return 0
    usuario._telegram_chat_id = pref.telegram_chat_id
    mensaje = construir_digest(pendientes, pref.modo)
    mensaje = Mensaje(asunto=mensaje.asunto, cuerpo=mensaje.cuerpo,
                      enlace_baja=enlace_baja(usuario.email))
    exito = any(nf.enviar(usuario, mensaje) for nf in obtener_notificadores(pref.canales))
    for n in pendientes:
        n.estado = "enviada" if exito else "pendiente"
        if exito:
            n.enviado_en = _now()
    db.commit()
    return len(pendientes) if exito else 0

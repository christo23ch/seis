"""Purga de cuentas nunca verificadas (Fase 11, Bloque I — deuda 10).

Una cuenta registrada y jamás verificada no caduca. Además de ser una tabla que
solo crece, tiene una consecuencia funcional que `docs/PENDIENTES.md` no
recogía: **secuestra la dirección de correo de forma indefinida**.
`registrar_usuario` devuelve `None` si el email ya existe y el endpoint responde
201 neutro, de modo que hoy cualquiera puede registrar la dirección de un tercero,
no verificarla nunca y **negarle el alta a su titular para siempre**.

**Por qué el predicado tiene nueve condiciones y no una.** Un usuario sin
verificar es **propietario de una `Organizacion` propia** que creó su alta. Ni
`Usuario` ni `Organizacion` declaran una sola `relationship()`, y ninguna de las
seis claves foráneas que les apuntan declara `ondelete` (verificado sobre el
mapeo). En PostgreSQL eso significa que un borrado desordenado aborta la
transacción; en SQLite, donde las claves foráneas están **desactivadas por
defecto**, significa algo peor: pasa en verde y deja filas huérfanas. De ahí que
el borrado sea manual, ordenado y condicional.

**Arranca en modo «informar».** El mecanismo se entrega completo y probado, pero
con el interruptor en la posición segura: cuenta las candidatas y no borra nada.
Pasar a `borrar` es una variable de entorno, no un despliegue de código. Un
borrado irreversible no debe ser el comportamiento por defecto de algo que nunca
se ha visto correr contra datos reales.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, and_
from sqlalchemy.orm import Session, aliased

from app import models
from app.core.config import get_settings
from app.services.borrado_service import borrar_datos_de_usuario

log = logging.getLogger("seis.purga")

MODO_INFORMAR = "informar"
MODO_BORRAR = "borrar"
MODOS_VALIDOS = (MODO_INFORMAR, MODO_BORRAR)

# Tope de cuentas por ejecución: acota la duración de la tarea y el tamaño de la
# transacción. Con una purga diaria, 500 cubre de sobra cualquier volumen real.
LIMITE_POR_EJECUCION = 500


@dataclass(frozen=True)
class ResultadoPurga:
    """Lo que hizo una ejecución. Solo recuentos: NUNCA direcciones de correo."""
    modo: str
    candidatas: int
    cuentas_borradas: int
    organizaciones_borradas: int
    # Dos recuentos y no uno: «perdió el predicado al revisarla» es la operación
    # NORMAL (alguien se verificó entre la selección y el borrado), mientras que
    # «la transacción falló» es una AVERÍA. Contarlas juntas hacía que un fallo
    # sistémico —una tabla hija que la purga no borra, por ejemplo— produjera
    # exactamente las mismas métricas y el mismo log que un día tranquilo, que es
    # justo el fallo mudo que este bloque existe para combatir.
    omitidas_en_revision: int
    fallidas: int
    organizaciones_huerfanas_detectadas: int


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _filtros_de_purga(corte: datetime, admin_email: str):
    """Las nueve condiciones, como lista de filtros de SQLAlchemy.

    Se comparan las fechas **en SQL** y nunca en Python: `creado_en` se persiste
    como `DateTime(timezone=True)`, pero en SQLite el `tzinfo` no sobrevive a la
    relectura, y comparar en Python produciría un `TypeError` entre datetimes
    naive y aware.
    """
    U = models.Usuario
    otro = aliased(models.Usuario)

    hay_otro_miembro = exists().where(and_(
        otro.organizacion_id == U.organizacion_id, otro.id != U.id))
    hay_analisis = exists().where(
        models.Analisis.organizacion_id == U.organizacion_id)

    return [
        U.email_verificado.is_(False),      # P1 · es la definición de la deuda
        U.activo.is_(False),                # P2 · así nace el alta pública; otra
                                            #      combinación es una anomalía que
                                            #      no sabemos interpretar
        U.es_superadmin.is_(False),         # P3 · gobierno de plataforma, jamás
        U.rol_org == "propietario",         # P4 · solo el alta pública los produce
        U.organizacion_id.isnot(None),      # P5 · sin tenant no sabemos evaluar
        U.email != admin_email,             # P6 · cinturón sobre el bootstrap
        U.creado_en < corte,                # P7 · la ventana
        ~hay_otro_miembro,                  # P8 · no dejar miembros huérfanos
        ~hay_analisis,                      # P9 · un análisis es snapshot inmutable
    ]


def candidatos_sin_verificar(db: Session, *, ahora: datetime, dias: int,
                             limite: int = LIMITE_POR_EJECUCION) -> list[tuple[str, str]]:
    """Devuelve `[(usuario_id, organizacion_id)]` que cumplen las nueve condiciones."""
    corte = ahora - timedelta(days=dias)
    U = models.Usuario
    filas = (db.query(U.id, U.organizacion_id)
             .filter(*_filtros_de_purga(corte, get_settings().admin_email))
             .order_by(U.creado_en)
             .limit(limite)
             .all())
    return [(f[0], f[1]) for f in filas]


def es_purgable(db: Session, usuario: models.Usuario, *, ahora: datetime,
                dias: int) -> bool:
    """Re-evalúa el predicado sobre una instancia concreta, ya cargada.

    **No es redundante con `candidatos_sin_verificar`.** La selección ocurre
    fuera de la transacción de borrado; esto ocurre dentro. Es la única defensa
    real contra la carrera con `/verificar`: si el usuario se verificó entre
    ambos momentos, aquí se detecta y la purga se retira sin tocar nada.
    """
    corte = ahora - timedelta(days=dias)
    return db.query(
        exists().where(and_(models.Usuario.id == usuario.id,
                            *_filtros_de_purga(corte, get_settings().admin_email)))
    ).scalar() is True


def purgar_cuenta_sin_verificar(db: Session, usuario_id: str, *, ahora: datetime,
                                dias: int) -> tuple[bool, bool]:
    """Borra una cuenta y, si procede, su organización. Transacción propia.

    Devuelve `(usuario_borrado, organizacion_borrada)`.

    El orden de borrado no es cosmético: lo imponen las claves foráneas, que no
    declaran `ondelete`. `notificacion` va antes que `alerta` porque también
    apunta a ella.
    """
    usuario = (db.query(models.Usuario)
               .filter(models.Usuario.id == usuario_id)
               .with_for_update(skip_locked=True)      # ignorado en SQLite
               .one_or_none())
    if usuario is None or not es_purgable(db, usuario, ahora=ahora, dias=dias):
        db.rollback()
        return False, False

    organizacion_borrada = borrar_datos_de_usuario(db, usuario)

    # La auditoría va DENTRO de la misma transacción: si el borrado se aborta,
    # la constancia se aborta con él, y nunca queda registrada una purga que no
    # ocurrió. `entidad_id` es el UUID y no el email, y el delta no lleva
    # dirección: no hay motivo para duplicar por tercera vez una dirección que
    # jamás fue verificada y que puede pertenecer a un tercero ajeno.
    db.add(models.Auditoria(
        quien="sistema:purga", entidad="usuario", entidad_id=usuario_id,
        accion="purga_sin_verificar",
        delta={"organizacion_borrada": organizacion_borrada, "dias": dias}))
    db.commit()
    return True, organizacion_borrada


def contar_organizaciones_huerfanas(db: Session) -> int:
    """Organizaciones sin ningún usuario. Se CUENTAN, no se borran.

    `crear_organizacion` comitea por su cuenta antes de crear al usuario, así que
    un proceso que muera entre ambos commits deja una organización sin dueño. El
    predicado de purga, anclado en usuarios, no la ve. Borrarlas exige un
    criterio distinto —hay que razonar sobre `analisis.organizacion_id`, que es
    nulable— y sin esa evidencia informar es la respuesta correcta e improvisar
    un borrado no lo es.
    """
    return db.query(models.Organizacion).filter(
        ~exists().where(models.Usuario.organizacion_id == models.Organizacion.id)
    ).count()


def purgar_cuentas_sin_verificar(db: Session, *, ahora: datetime | None = None,
                                 dias: int | None = None, modo: str | None = None,
                                 limite: int = LIMITE_POR_EJECUCION) -> ResultadoPurga:
    """Punto de entrada. En modo «informar» cuenta y no borra."""
    ajustes = get_settings()
    ahora = ahora or _ahora_utc()
    dias = dias if dias is not None else ajustes.purga_cuentas_dias
    modo = (modo or ajustes.purga_cuentas_modo).strip().lower()
    if modo not in MODOS_VALIDOS:
        # Fallar en cerrado: un modo que no se reconoce nunca borra.
        log.error("Modo de purga no reconocido (%r); se actúa como «informar».", modo)
        modo = MODO_INFORMAR

    candidatas = candidatos_sin_verificar(db, ahora=ahora, dias=dias, limite=limite)
    huerfanas = contar_organizaciones_huerfanas(db)

    if modo == MODO_INFORMAR:
        if candidatas or huerfanas:
            log.info("Purga en modo informe: %d cuentas serían borradas, "
                     "%d organizaciones huérfanas detectadas. No se ha borrado nada.",
                     len(candidatas), huerfanas)
        return ResultadoPurga(modo=modo, candidatas=len(candidatas),
                              cuentas_borradas=0, organizaciones_borradas=0,
                              omitidas_en_revision=0, fallidas=0,
                              organizaciones_huerfanas_detectadas=huerfanas)

    borradas = organizaciones = omitidas = fallidas = 0
    for usuario_id, _org in candidatas:
        try:
            borrado, org_borrada = purgar_cuenta_sin_verificar(
                db, usuario_id, ahora=ahora, dias=dias)
        except Exception:                                # noqa: BLE001
            # Un fallo en una cuenta no puede llevarse por delante a las demás
            # ni al planificador. Se cuenta APARTE de las omitidas: esto es una
            # avería, no la operación normal.
            db.rollback()
            log.exception("Fallo purgando una cuenta; se continúa con las demás")
            fallidas += 1
            continue
        if borrado:
            borradas += 1
            organizaciones += int(org_borrada)
        else:
            omitidas += 1

    if fallidas:
        # Nivel ERROR y no INFO: si fallan cuentas, algo va mal en el borrado
        # —una tabla hija sin cubrir, por ejemplo— y no debe leerse como rutina.
        log.error("Purga: %d cuentas FALLARON al borrarse. Revise el log de "
                  "excepciones: puede haber una relación que la purga no borra.",
                  fallidas)
    log.info("Purga: %d cuentas borradas, %d organizaciones borradas, "
             "%d omitidas al revisarlas, %d fallidas, %d huérfanas detectadas.",
             borradas, organizaciones, omitidas, fallidas, huerfanas)
    return ResultadoPurga(modo=modo, candidatas=len(candidatas),
                          cuentas_borradas=borradas,
                          organizaciones_borradas=organizaciones,
                          omitidas_en_revision=omitidas, fallidas=fallidas,
                          organizaciones_huerfanas_detectadas=huerfanas)

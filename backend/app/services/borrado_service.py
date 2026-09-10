"""El ÚNICO camino de borrado de una persona (Fase 14, RGPD).

Existe por una decisión tomada antes de escribir la fase: la 14 **extiende** el
borrado que la 11-A construyó en `purga_service`, no escribe uno paralelo.

Por qué importa tanto tener uno solo. Ni `Usuario` ni `Organizacion` declaran
una sola `relationship()`, y **ninguna clave foránea que les apunte declara
`ondelete`**. No hay cascada, ni de ORM ni de base de datos. En PostgreSQL un
borrado desordenado aborta la transacción entera; en SQLite —donde las claves
foráneas están apagadas por defecto y la suite no las enciende— pasa **en
verde** y deja filas huérfanas: datos personales que sobreviven a un borrado que
el sistema dio por completo. Dos implementaciones de esto significan dos listas
de tablas hijas que hay que acordarse de mantener a la vez, y la segunda vez que
alguien añada una tabla se acordará de una.

Con un solo camino, olvidar una tabla es un fallo; con dos, es cuestión de
tiempo. Y hay un test que deriva las tablas hijas del `metadata` en lugar de
enumerarlas, así que añadir una relación nueva sin cubrirla aquí sale en rojo
sola.

**La anonimización de la auditoría es parte del borrado, no un extra.**
`auditoria.quien` y `auditoria.entidad_id` guardan la DIRECCIÓN DE CORREO en el
registro, la verificación y el cambio de contraseña (`usuario_service`). Borrar
la fila de `usuario` y dejar esas ahí deja el dato personal más identificativo
que hay dentro del sistema. No es hipotético: es lo que hacía la purga de la
11-A hasta esta fase.
"""
from __future__ import annotations

import logging

from sqlalchemy import exists, or_
from sqlalchemy.orm import Session

from app import models

log = logging.getLogger("seis.borrado")

# Tablas hijas de `usuario`, en orden de borrado. El orden NO es cosmético: lo
# imponen las claves foráneas, que no declaran `ondelete`. `notificacion` va
# antes que `alerta` porque también apunta a ella.
#
# Esta lista es la que el test derivado del `metadata` vigila: si alguien añade
# una tabla que apunte a `usuario` y no la añade aquí, el test se pone rojo con
# el nombre de la tabla que falta.
TABLAS_HIJAS_DE_USUARIO = (
    models.Notificacion,
    models.Alerta,
    models.CodigoTelegram,
    models.PreferenciasNotificacion,
    models.Consentimiento,
)

PREFIJO_ANONIMO = "anonimizado:"


def marca_anonima(usuario_id: str) -> str:
    """Sustituto de la dirección en `auditoria.quien` (String(120)).

    Se conserva el identificador y no se pone «anónimo» a secas porque la
    auditoría tiene que seguir siendo una traza: dos acciones del mismo titular
    deben seguir agrupándose. Es un seudónimo, y una vez borrada la fila de
    `usuario` ya no hay nada en el sistema que lo devuelva a una persona.
    """
    return f"{PREFIJO_ANONIMO}{usuario_id}"


def marca_anonima_entidad(usuario_id: str) -> str:
    """Sustituto en `auditoria.entidad_id`, que es String(36) — justo el ancho
    de un UUID y ni un carácter más.

    Va el identificador PELADO, sin prefijo, y no es una elección estética:
    `anonimizado:` + UUID son 48 caracteres. En PostgreSQL eso aborta la
    transacción con `StringDataRightTruncation` —que es como se descubrió— y en
    SQLite, que no aplica el ancho declarado, se habría guardado entero y nadie
    se habría enterado hasta el primer despliegue.

    Que el valor sea indistinguible de un identificador normal no estorba:
    `entidad_id` ya guarda UUID en las purgas, y el prefijo explícito viaja en
    `quien`, que sí tiene sitio.
    """
    return usuario_id


def anonimizar_auditoria(db: Session, usuario: models.Usuario) -> int:
    """Sustituye la dirección del titular en la auditoría. Devuelve filas tocadas.

    No borra las filas: la traza de qué ocurrió en el sistema es legítima y a
    menudo obligatoria. Lo que no es legítimo es que siga nombrando a una
    persona que pidió desaparecer.
    """
    email = usuario.email
    tocadas = (db.query(models.Auditoria)
               .filter(or_(models.Auditoria.quien == email,
                           models.Auditoria.entidad_id == email))
               .update({models.Auditoria.quien: marca_anonima(usuario.id),
                        models.Auditoria.entidad_id: marca_anonima_entidad(usuario.id)},
                       synchronize_session=False))
    return int(tocadas or 0)


def _organizacion_vacia(db: Session, organizacion_id: str | None) -> bool:
    """¿Queda algo colgando de esa organización?

    Se RECOMPRUEBA en vez de fiarse de lo que dijera el predicado del llamante:
    un superadmin puede añadir un usuario a cualquier organización entre la
    selección y el borrado. Y `analisis` cuenta: son snapshots inmutables (P1) y
    borrar su organización dejaría la referencia rota.
    """
    if organizacion_id is None:
        return False
    quedan_miembros = db.query(exists().where(
        models.Usuario.organizacion_id == organizacion_id)).scalar()
    hay_analisis = db.query(exists().where(
        models.Analisis.organizacion_id == organizacion_id)).scalar()
    return not quedan_miembros and not hay_analisis


def borrar_datos_de_usuario(db: Session, usuario: models.Usuario) -> bool:
    """Borra al usuario, sus filas hijas y su organización si queda vacía.

    **No hace commit ni rollback**: el llamante decide la transacción, porque es
    quien sabe qué más va dentro de ella —la purga añade su propia auditoría, el
    borrado por RGPD la suya—. Devuelve si la organización se borró.

    No comprueba ningún predicado. Quién puede borrarse es decisión del llamante
    (`purga_service` tiene sus nueve condiciones; el borrado a petición tiene la
    gracia vencida), y meter aquí esa lógica volvería a mezclar dos cosas que
    esta fase separó a propósito.
    """
    organizacion_id = usuario.organizacion_id
    usuario_id = usuario.id

    # ANTES de borrar la fila de `usuario`: después ya no se sabría qué correo
    # sustituir. Es el orden lo que hace que esto funcione, no la buena voluntad.
    anonimizadas = anonimizar_auditoria(db, usuario)

    for modelo in TABLAS_HIJAS_DE_USUARIO:
        db.query(modelo).filter(
            modelo.usuario_id == usuario_id).delete(synchronize_session=False)
    db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id).delete(synchronize_session=False)

    organizacion_borrada = False
    if _organizacion_vacia(db, organizacion_id):
        db.query(models.Organizacion).filter(
            models.Organizacion.id == organizacion_id).delete(
                synchronize_session=False)
        organizacion_borrada = True

    log.info("Borrado de datos: usuario=%s, %d filas de auditoría anonimizadas, "
             "organización borrada=%s", usuario_id, anonimizadas, organizacion_borrada)
    return organizacion_borrada

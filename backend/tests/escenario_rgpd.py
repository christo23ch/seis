"""Escenario compartido del borrado RGPD, para poder correrlo en DOS motores.

No es un módulo de tests: no tiene `test_*`. Existe porque la comprobación que
importa —que no queden filas huérfanas— **tiene que correr también contra
PostgreSQL**, y es justo el sitio donde SQLite miente: con las claves foráneas
apagadas por defecto, un borrado incompleto pasa en verde y deja datos
personales colgando de un usuario que ya no existe.

Duplicar el escenario en los dos módulos habría sido garantizar que dentro de
tres meses uno de los dos se quedara atrás — que es el mismo argumento por el
que esta fase tiene un solo camino de borrado.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect, or_, text
from sqlalchemy.orm import Session

from app import models

PASSWORD = "unaClaveLarga-14"


def tablas_hijas_de(metadata, *padres: str) -> set[str]:
    """Tablas con clave foránea a alguno de esos padres, DERIVADAS del metadata.

    Derivarlas y no enumerarlas es lo que hace que este test siga sirviendo
    dentro de un año: quien añada una tabla nueva colgando de `usuario` y no la
    cubra en `borrado_service` verá este test en rojo con el nombre de su tabla,
    sin haber tenido que acordarse de nada.
    """
    hijas = set()
    for tabla in metadata.sorted_tables:
        for fk in tabla.foreign_keys:
            if fk.column.table.name in padres and tabla.name not in padres:
                hijas.add(tabla.name)
    return hijas


def sembrar_titular(db: Session, *, email: str, con_analisis: bool = False
                    ) -> tuple[str, str]:
    """Un usuario verificado con datos en TODAS sus tablas hijas.

    Devuelve `(usuario_id, organizacion_id)`. Si alguna tabla hija se quedara
    sin sembrar, el borrado podría estar incompleto y el test no lo vería: por
    eso el llamante comprueba la cobertura contra el metadata.
    """
    from app.services import usuario_service

    org = usuario_service.crear_organizacion(db, f"Org de {email}")
    u = usuario_service.crear_usuario(db, email, PASSWORD, "Titular", "analista",
                                      organizacion_id=org.id, rol_org="propietario")
    u.email_verificado = True
    db.add(models.PreferenciasNotificacion(usuario_id=u.id, canales=["email"]))
    db.add(models.CodigoTelegram(
        codigo=uuid.uuid4().hex[:6].upper(), usuario_id=u.id,
        expira_en=datetime.now(timezone.utc) + timedelta(minutes=10)))
    db.add(models.Consentimiento(id=str(uuid.uuid4()), usuario_id=u.id,
                                 tipo="terminos", version="1", otorgado=True))
    alerta = models.Alerta(id=str(uuid.uuid4()), usuario_id=u.id, nombre="mía",
                           criterios={"fuente": "judicial_boe"}, activa=True)
    db.add(alerta)
    db.flush()
    db.add(models.Notificacion(id=str(uuid.uuid4()), usuario_id=u.id,
                               alerta_id=alerta.id, asunto="a", cuerpo="b",
                               estado="pendiente"))
    db.add(models.Notificacion(id=str(uuid.uuid4()), usuario_id=u.id,
                               alerta_id=None, asunto="c", cuerpo="d",
                               estado="pendiente"))
    # Auditoría con la DIRECCIÓN dentro, que es como la escribe el registro real.
    db.add(models.Auditoria(quien=email, entidad="usuario", entidad_id=email,
                            accion="registro_self_service", delta={}))
    if con_analisis:
        db.add(models.Analisis(id=str(uuid.uuid4()), organizacion_id=org.id,
                               perfil_codigo="conservador", version_reglas="1",
                               version_parametros="1", entrada={}, hechos={},
                               resultado={}))
    db.commit()
    return u.id, org.id


def comprobar_sin_huerfanas(db: Session, metadata, usuario_id: str,
                            organizacion_id: str, email: str) -> None:
    """La comprobación que da sentido a todo: no queda NADA del titular.

    Se recorren las tablas hijas derivadas del metadata, no una lista escrita a
    mano, y se consulta en SQL crudo para no depender de que el ORM tenga
    mapeada la tabla que alguien añada mañana.
    """
    tablas = inspect(db.get_bind()).get_table_names()
    huerfanas: dict[str, int] = {}

    for nombre in sorted(tablas_hijas_de(metadata, "usuario")):
        if nombre not in tablas:
            continue
        n = db.execute(text(f"SELECT COUNT(*) FROM {nombre} WHERE usuario_id = :u"),
                       {"u": usuario_id}).scalar()
        if n:
            huerfanas[nombre] = int(n)

    assert db.get(models.Usuario, usuario_id) is None, "el usuario sigue ahí"
    assert not huerfanas, (
        f"quedan filas colgando de un usuario borrado: {huerfanas}. Sin `ondelete` "
        "no hay cascada, así que cada tabla hija hay que borrarla a mano en "
        "`borrado_service.TABLAS_HIJAS_DE_USUARIO`.")

    assert db.query(models.Auditoria).filter(
        or_(models.Auditoria.quien == email,
            models.Auditoria.entidad_id == email)).count() == 0, (
        "la dirección del titular sigue en la auditoría tras borrar su cuenta")


def cobertura_de_tablas_hijas(metadata) -> set[str]:
    """Tablas hijas de `usuario` que el escenario NO siembra.

    Si esto devuelve algo, el test que lo llama debe fallar: significa que hay
    una relación nueva y el escenario no la ejercita, de modo que el borrado
    podría estar dejándola atrás sin que nadie se entere.
    """
    sembradas = {"preferencias_notificacion", "codigo_telegram", "alerta",
                 "notificacion", "consentimiento"}
    return tablas_hijas_de(metadata, "usuario") - sembradas

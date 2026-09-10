"""Fase 11 · Bloque I — purga de cuentas nunca verificadas (deuda 10).

Un usuario sin verificar es **propietario de una `Organizacion` propia**, así que
un borrado ingenuo o deja organizaciones huérfanas o se lleva datos de terceros.
De ahí que el predicado tenga nueve condiciones y que casi todos los tests de
este fichero sean **negativos**: lo que hay que demostrar no es que borre, es
que **no borre lo que no debe**.

Nota sobre SQLite: en la suite las claves foráneas están desactivadas por
defecto, de modo que un orden de borrado incorrecto pasaría en verde aquí y
reventaría en PostgreSQL. `test_la_purga_no_deja_filas_huerfanas_con_claves_foraneas_activas`
activa `PRAGMA foreign_keys=ON` precisamente para que ese falso verde no exista.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import or_, text

from app import models
from app.services import purga_service


def _sesion():
    from app.core.db import SessionLocal

    return SessionLocal()


def _crear_org(db, nombre="Org de purga") -> models.Organizacion:
    org = models.Organizacion(id=str(uuid.uuid4()), nombre=nombre,
                              creado_en=datetime.now(timezone.utc))
    db.add(org)
    db.commit()
    return org


def _crear_usuario(db, org, *, dias_de_antiguedad=60, email_verificado=False,
                   activo=False, rol_org="propietario", es_superadmin=False,
                   email=None) -> models.Usuario:
    u = models.Usuario(
        id=str(uuid.uuid4()), email=email or f"{uuid.uuid4().hex[:12]}@example.com",
        hash_pwd="x", nombre="Sin Verificar", rol="admin",
        activo=activo, email_verificado=email_verificado,
        organizacion_id=org.id, rol_org=rol_org, es_superadmin=es_superadmin,
        creado_en=datetime.now(timezone.utc) - timedelta(days=dias_de_antiguedad))
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def db(api):
    """Sesión con limpieza de lo que cada test siembre.

    Depende de `api` para reutilizar el esquema y el admin ya sembrados.
    """
    s = _sesion()
    yield s
    s.rollback()
    s.close()


def _purgar(db, **kwargs):
    return purga_service.purgar_cuentas_sin_verificar(
        db, modo=purga_service.MODO_BORRAR, **kwargs)


def _existe_por(db, modelo, columna, valor) -> bool:
    """Variante de `_existe` para modelos cuya clave primaria no se llama `id`."""
    db.expunge_all()
    return db.query(modelo).filter(columna == valor).count() > 0


def _existe(db, modelo, pk: str) -> bool:
    """¿Sigue la fila en la BASE DE DATOS?

    No vale `db.get()`: la purga borra con `delete(synchronize_session=False)`,
    de modo que la sesión conserva el objeto en su mapa de identidad y `get`
    lo devolvería aunque la fila ya no exista. Una aserción escrita así pasaría
    en verde con la purga rota. Se expulsa la sesión y se consulta de verdad.
    """
    db.expunge_all()
    return db.query(modelo).filter(modelo.id == pk).count() > 0


# ─────────────────────────── Positivos ───────────────────────────

def test_purga_borra_la_cuenta_sin_verificar_y_su_organizacion_vacia(db):
    org = _crear_org(db)
    u = _crear_usuario(db, org)

    resultado = _purgar(db)

    assert resultado.cuentas_borradas >= 1
    assert not _existe(db, models.Usuario, u.id)
    assert not _existe(db, models.Organizacion, org.id)


def test_purga_deja_constancia_en_auditoria_sin_escribir_el_email(db):
    """La traza es obligatoria, pero no debe duplicar una dirección no verificada."""
    org = _crear_org(db)
    u = _crear_usuario(db, org)

    _purgar(db)

    fila = (db.query(models.Auditoria)
            .filter(models.Auditoria.accion == "purga_sin_verificar",
                    models.Auditoria.entidad_id == u.id)
            .one())
    assert fila.quien == "sistema:purga"
    assert fila.delta["organizacion_borrada"] is True
    assert u.email not in str(fila.delta)


def _tablas_hija_de_usuario() -> set[str]:
    """Tablas con clave foránea a `usuario.id`, **derivadas del metadata**.

    Enumerarlas a mano fue el defecto de la primera versión de este test: se
    sembraban tres de las cuatro y `codigo_telegram` quedaba fuera, de modo que
    borrar su línea de la purga era indetectable. Peor: la próxima tabla hija que
    añada otra fase —la 13, con la suscripción— reabriría el mismo hueco en
    silencio. Derivándolas, una tabla nueva sin cubrir pone el test en rojo.
    """
    from app.core.db import Base

    return {tabla.name for tabla in Base.metadata.tables.values()
            for fk in tabla.foreign_keys
            if fk.column.table.name == "usuario"}


def test_la_purga_no_deja_filas_huerfanas_con_claves_foraneas_activas(db):
    """Único test que demuestra que el ORDEN de borrado es correcto y COMPLETO.

    Ninguna de las claves foráneas declara `ondelete`, y `Usuario` no tiene una
    sola `relationship()`, así que no hay cascada de ningún tipo: los hijos hay
    que borrarlos a mano y en orden. En SQLite eso no se comprueba salvo que se
    active el PRAGMA, y sin él este bloque tendría una batería decorativa que
    pasaría en verde mientras PostgreSQL aborta la transacción.

    Si la purga se dejara una tabla, en PostgreSQL el `DELETE FROM usuario`
    violaría su clave foránea, la excepción se contaría como una omisión más y
    **ninguna cuenta con esa relación se purgaría jamás**, sin que el resumen lo
    distinguiera de una omisión legítima.
    """
    org = _crear_org(db)
    u = _crear_usuario(db, org)
    db.add(models.PreferenciasNotificacion(usuario_id=u.id))
    db.add(models.CodigoTelegram(
        codigo=uuid.uuid4().hex[:6].upper(), usuario_id=u.id,
        expira_en=datetime.now(timezone.utc) + timedelta(minutes=10)))
    alerta = models.Alerta(id=str(uuid.uuid4()), usuario_id=u.id, nombre="a",
                           criterios={}, activa=True)
    db.add(alerta)
    db.commit()
    db.add(models.Notificacion(id=str(uuid.uuid4()), usuario_id=u.id,
                               alerta_id=alerta.id,
                               asunto="x", cuerpo="y", estado="pendiente"))
    # Con `alerta_id` nulo, que es la otra rama de esa clave foránea.
    db.add(models.Notificacion(id=str(uuid.uuid4()), usuario_id=u.id,
                               alerta_id=None,
                               asunto="z", cuerpo="w", estado="pendiente"))
    db.commit()

    db.add(models.Consentimiento(id=str(uuid.uuid4()), usuario_id=u.id,
                                 tipo="terminos", version="1", otorgado=True))
    db.commit()

    sembradas = {"preferencias_notificacion", "codigo_telegram", "alerta",
                 "notificacion", "consentimiento"}
    sin_cubrir = _tablas_hija_de_usuario() - sembradas
    assert not sin_cubrir, (
        f"Hay tablas con clave foránea a `usuario.id` que este test no siembra: "
        f"{sorted(sin_cubrir)}. Añádelas aquí Y a la purga, o el borrado quedará "
        "incompleto sin que nada lo detecte.")

    # El PRAGMA es POR CONEXIÓN, y la conexión vive en un pool. Medido: sobrevive
    # al `commit` que hace la purga —bien, es lo que hace efectivo este test— pero
    # **también sobrevive a la sesión**, de modo que sin el `finally` se filtraría
    # a los tests siguientes y sus fallos pasarían a depender del orden.
    db.execute(text("PRAGMA foreign_keys=ON"))
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    try:
        _purgar(db)

        assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1, (
            "el PRAGMA se perdió durante la purga: este test no estaría "
            "comprobando la integridad referencial que dice comprobar")
        assert not _existe(db, models.Usuario, u.id)
        for modelo in (models.Alerta, models.Notificacion,
                       models.PreferenciasNotificacion, models.CodigoTelegram):
            restantes = db.query(modelo).filter(modelo.usuario_id == u.id).count()
            assert restantes == 0, (
                f"quedaron filas huérfanas en {modelo.__tablename__}")
    finally:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        db.commit()


def test_modo_informar_cuenta_las_candidatas_y_no_borra_nada(db):
    """El modo por defecto. Entregar el mecanismo no es activarlo."""
    org = _crear_org(db)
    u = _crear_usuario(db, org)

    resultado = purga_service.purgar_cuentas_sin_verificar(
        db, modo=purga_service.MODO_INFORMAR)

    assert resultado.candidatas >= 1
    assert resultado.cuentas_borradas == 0
    assert _existe(db, models.Usuario, u.id)


def test_un_modo_no_reconocido_no_borra_nada(db):
    """Fallar en cerrado: una errata en la variable de entorno no puede borrar."""
    org = _crear_org(db)
    u = _crear_usuario(db, org)

    resultado = purga_service.purgar_cuentas_sin_verificar(db, modo="Borrarlo todo")

    assert resultado.modo == purga_service.MODO_INFORMAR
    assert _existe(db, models.Usuario, u.id)


# ─────────────────────────── Negativos ───────────────────────────

def test_no_borra_una_organizacion_con_analisis(db):
    """P9: un análisis es snapshot inmutable; borrar a su único usuario dejaría
    la organización inaccesible para siempre."""
    org = _crear_org(db)
    u = _crear_usuario(db, org)
    db.add(models.Analisis(id=str(uuid.uuid4()), organizacion_id=org.id,
                           perfil_codigo="flip_integral",
                           entrada={}, hechos={}, resultado={},
                           version_reglas="x", version_parametros="y"))
    db.commit()

    _purgar(db)

    assert _existe(db, models.Usuario, u.id)
    assert _existe(db, models.Organizacion, org.id)


def test_no_borra_una_cuenta_activa_aunque_no_este_verificada(db):
    """Aísla **P2**, que hasta ahora ningún test distinguía de P1.

    El alta pública nace `activo=False, email_verificado=False`. La combinación
    `activo=True, email_verificado=False` es una **anomalía** que el sistema no
    sabe interpretar —hoy ninguna ruta la produce— y ante lo que no se entiende
    la respuesta correcta es no borrar. Sin este test, quitar P2 del predicado
    dejaba la suite entera en verde.
    """
    org = _crear_org(db)
    u = _crear_usuario(db, org, activo=True, email_verificado=False)

    _purgar(db)

    assert _existe(db, models.Usuario, u.id)


def test_no_borra_la_cuenta_cuyo_email_es_el_del_admin_configurado(db, monkeypatch):
    """Aísla **P6**, que hasta ahora era un cinturón que nadie comprobaba.

    El admin bootstrap real sobrevive por P1 (está verificado) y por P3 (es
    superadmin), así que `test_no_toca_al_admin_bootstrap` pasaría igual sin P6.
    Aquí se apunta `admin_email` a una cuenta que **sí** cumple todo lo demás,
    que es la única forma de que P6 sea lo único que la salva.
    """
    from types import SimpleNamespace

    org = _crear_org(db)
    u = _crear_usuario(db, org)
    monkeypatch.setattr(purga_service, "get_settings",
                        lambda: SimpleNamespace(admin_email=u.email,
                                                purga_cuentas_dias=30,
                                                purga_cuentas_modo="borrar"))

    _purgar(db)

    assert _existe(db, models.Usuario, u.id), (
        "la cuenta configurada como admin no se purga aunque cumpla el resto "
        "del predicado")


def test_no_borra_un_usuario_verificado(db):
    org = _crear_org(db)
    u = _crear_usuario(db, org, email_verificado=True, activo=True)

    _purgar(db)

    assert _existe(db, models.Usuario, u.id)


def test_no_toca_al_admin_bootstrap(db):
    """Triple cinturón: está verificado, es superadmin y su email está excluido."""
    from app.core.config import get_settings
    from app.services import usuario_service

    admin = usuario_service.obtener_por_email(db, get_settings().admin_email)
    assert admin is not None, "el admin bootstrap debe existir en la fixture"

    _purgar(db)

    assert _existe(db, models.Usuario, admin.id)


def test_una_cuenta_dentro_de_la_ventana_sobrevive(db):
    """P7: quien se registra antes de un viaje no debe volver y no encontrar nada."""
    from app.core.config import get_settings

    org = _crear_org(db)
    u = _crear_usuario(db, org,
                       dias_de_antiguedad=get_settings().purga_cuentas_dias - 1)

    _purgar(db)

    assert _existe(db, models.Usuario, u.id)


def test_no_borra_si_la_organizacion_tiene_otro_miembro(db):
    """P8: la organización es de más gente; borrar a uno la dejaría coja."""
    org = _crear_org(db)
    sin_verificar = _crear_usuario(db, org)
    _crear_usuario(db, org, email_verificado=True, activo=True, rol_org="miembro")

    _purgar(db)

    assert _existe(db, models.Usuario, sin_verificar.id)


def test_no_borra_un_superadmin_aunque_este_sin_verificar(db):
    """P3: el gobierno de plataforma no se purga nunca, en ninguna circunstancia."""
    org = _crear_org(db)
    u = _crear_usuario(db, org, es_superadmin=True)

    _purgar(db)

    assert _existe(db, models.Usuario, u.id)


def test_no_borra_a_quien_no_es_propietario_de_su_organizacion(db):
    """P4: hoy solo el alta pública produce cuentas sin verificar, y siempre como
    propietario. Si mañana apareciera otro camino, esta condición lo detiene."""
    org = _crear_org(db)
    u = _crear_usuario(db, org, rol_org="miembro")

    _purgar(db)

    assert _existe(db, models.Usuario, u.id)


def test_no_borra_a_quien_se_verifico_entre_la_seleccion_y_el_borrado(db):
    """La carrera con `/verificar`, que es el caso que obliga a re-evaluar bajo bloqueo.

    Se simula el peor orden posible: la cuenta entra en la selección y se
    verifica antes de que la purga llegue a ella.
    """
    org = _crear_org(db)
    u = _crear_usuario(db, org)
    ahora = datetime.now(timezone.utc)

    candidatas = purga_service.candidatos_sin_verificar(db, ahora=ahora, dias=30)
    assert u.id in [c[0] for c in candidatas]

    u.email_verificado = True
    u.activo = True
    db.commit()

    borrado, org_borrada = purga_service.purgar_cuenta_sin_verificar(
        db, u.id, ahora=ahora, dias=30)

    assert (borrado, org_borrada) == (False, False)
    assert _existe(db, models.Usuario, u.id)


def test_la_auditoria_del_usuario_purgado_sobrevive_al_borrado_pero_anonimizada(db):
    """Una traza cuya vida depende de la existencia del auditado no es auditoría.

    Pero una traza que sigue nombrando a quien ya no está tampoco vale: hasta la
    Fase 14, la purga borraba la fila de `usuario` y **dejaba la dirección de
    correo** en `auditoria.quien` y `auditoria.entidad_id`, donde la escribe
    `registrar_usuario`. Se borraba la cuenta y se conservaba el dato personal
    más identificativo que hay.

    Ahora se conserva la fila y se sustituye la dirección por un seudónimo
    estable: la traza sigue siendo traza —dos acciones del mismo titular siguen
    agrupándose— y ya no nombra a nadie.
    """
    from app.services.borrado_service import (marca_anonima,
                                              marca_anonima_entidad)

    org = _crear_org(db)
    u = _crear_usuario(db, org)
    email, usuario_id = u.email, u.id
    db.add(models.Auditoria(quien=u.email, entidad="usuario", entidad_id=u.email,
                            accion="registro_self_service", delta={}))
    db.commit()

    _purgar(db)

    fila = (db.query(models.Auditoria)
            .filter(models.Auditoria.accion == "registro_self_service").one())
    assert fila.quien == marca_anonima(usuario_id)
    assert fila.entidad_id == marca_anonima_entidad(usuario_id)

    assert db.query(models.Auditoria).filter(
        or_(models.Auditoria.quien == email,
            models.Auditoria.entidad_id == email)).count() == 0, (
        "la dirección del titular sigue en la auditoría tras purgar su cuenta")


def test_no_borra_organizaciones_sin_usuarios_solo_las_cuenta(db):
    """§ organizaciones huérfanas: informar es correcto, improvisar un borrado no."""
    org = _crear_org(db, nombre="Huérfana")

    antes = purga_service.contar_organizaciones_huerfanas(db)
    resultado = _purgar(db)

    assert antes >= 1
    assert resultado.organizaciones_huerfanas_detectadas >= 1
    assert _existe(db, models.Organizacion, org.id)


def test_la_purga_de_cuentas_no_toca_token_consumido(db):
    """Las dos deudas del bloque son independientes: `token_consumido` no tiene
    columna de usuario, y borrar un `jti` reabriría la reutilización del enlace
    que la Fase 10 cerró."""
    org = _crear_org(db)
    _crear_usuario(db, org)
    db.add(models.TokenConsumido(jti="jti-que-debe-sobrevivir", proposito="verificar",
                                 consumido_en=datetime.now(timezone.utc)))
    db.commit()

    _purgar(db)

    assert _existe_por(db, models.TokenConsumido,
                       models.TokenConsumido.jti, "jti-que-debe-sobrevivir")
    db.query(models.TokenConsumido).delete()
    db.commit()

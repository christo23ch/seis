"""Fase 14 — RGPD: consentimientos, exportación y borrado con gracia.

El borrado de esta batería corre sobre SQLite. La MISMA comprobación de filas
huérfanas corre además contra PostgreSQL en `test_postgres.py`, y no es
duplicación: con las claves foráneas apagadas —como están en SQLite por
defecto— un borrado incompleto pasa en verde. SQLite dice que todo fue bien
justamente en el caso en que no fue bien.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import models
from tests.conftest import token_headers
from tests.escenario_rgpd import (PASSWORD, cobertura_de_tablas_hijas,
                                  comprobar_sin_huerfanas, sembrar_titular)

API = "/api/v1"
CONSENTIMIENTOS_OK = {"acepta_terminos": True, "acepta_privacidad": True}


def _sesion(db, api, email: str) -> dict:
    usuario_id, org_id = sembrar_titular(db, email=email)
    return {"headers": token_headers(api, email, PASSWORD),
            "usuario_id": usuario_id, "organizacion_id": org_id, "email": email}


@pytest.fixture
def db():
    from app.core.db import SessionLocal
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# ═══════════════════════ Consentimientos ═══════════════════════

def test_el_alta_no_se_completa_sin_los_consentimientos_obligatorios(api):
    """Sin esto, el responsable no puede demostrar qué aceptó nadie.

    Y hay una trampa concreta detrás: con `acepta_terminos: bool = False`, los
    campos PARECÍAN obligatorios y no lo eran — Pydantic v2 no valida los
    valores por defecto, así que un cliente que no los enviara pasaba con «no
    acepta» y creaba la cuenta igual. Requerirlos es lo único que convierte la
    ausencia en un 422 en vez de en un consentimiento inventado.
    """
    sin_campos = api.post(f"{API}/auth/registro", json={
        "email": f"sin-{uuid.uuid4().hex[:8]}@ejemplo.com", "password": "unaClaveLarga1"})
    assert sin_campos.status_code == 422, sin_campos.text

    rechazando = api.post(f"{API}/auth/registro", json={
        "email": f"no-{uuid.uuid4().hex[:8]}@ejemplo.com", "password": "unaClaveLarga1",
        "acepta_terminos": False, "acepta_privacidad": True})
    assert rechazando.status_code == 422, rechazando.text


def test_las_comunicaciones_comerciales_no_condicionan_el_alta(api, db):
    """Un consentimiento condicionado al servicio no es libre, y no vale.

    De ahí que rechazar la publicidad NO impida registrarse, y que ese «no»
    quede guardado: sin la fila, no habría forma de distinguir a quien la
    rechazó de quien nunca vio la casilla.
    """
    email = f"sin-publi-{uuid.uuid4().hex[:8]}@ejemplo.com"
    r = api.post(f"{API}/auth/registro", json={
        "email": email, "password": "unaClaveLarga1", **CONSENTIMIENTOS_OK,
        "acepta_comunicaciones_comerciales": False})
    assert r.status_code == 201, r.text

    from app.services import usuario_service
    usuario = usuario_service.obtener_por_email(db, email)
    filas = {c.tipo: c for c in db.query(models.Consentimiento).filter(
        models.Consentimiento.usuario_id == usuario.id).all()}
    assert filas["comunicaciones_comerciales"].otorgado is False
    assert filas["terminos"].otorgado is True


def test_cada_consentimiento_guarda_version_y_fecha(api, db):
    """Sin la versión, publicar una política nueva convertiría lo aceptado antes
    en un consentimiento a un texto que nadie leyó."""
    from app.legal import textos
    from app.services import usuario_service

    email = f"version-{uuid.uuid4().hex[:8]}@ejemplo.com"
    assert api.post(f"{API}/auth/registro", json={
        "email": email, "password": "unaClaveLarga1",
        **CONSENTIMIENTOS_OK}).status_code == 201

    usuario = usuario_service.obtener_por_email(db, email)
    filas = db.query(models.Consentimiento).filter(
        models.Consentimiento.usuario_id == usuario.id).all()
    assert filas, "el alta no guardó ningún consentimiento"
    for c in filas:
        assert c.version == textos.VERSION_VIGENTE
        assert c.otorgado_en is not None


def test_los_textos_legales_pendientes_estan_marcados_como_tales():
    """Impide que un marcador se publique como texto definitivo por descuido.

    Cuando lleguen los textos del abogado, este test se pone rojo y obliga a
    actualizarlo a mano — que es exactamente la revisión que se quiere forzar.
    """
    from app.legal import textos

    assert textos.hay_textos_pendientes(), (
        "Ya no hay textos pendientes: si son los definitivos, suba "
        "VERSION_VIGENTE y actualice este test. Si no, alguien borró el "
        "marcador sin escribir el texto.")
    assert textos.TEXTOS[textos.COMUNICACIONES_COMERCIALES].obligatorio is False, (
        "condicionar el alta a aceptar publicidad haría que el consentimiento "
        "no fuera libre, y entonces no valdría como consentimiento")


# ═══════════════════════ Exportación ═══════════════════════

def test_la_exportacion_devuelve_los_datos_del_titular(api, db):
    s = _sesion(db, api, f"export-{uuid.uuid4().hex[:8]}@ejemplo.com")
    r = api.get(f"{API}/cuenta/exportar", headers=s["headers"])

    assert r.status_code == 200, r.text
    assert "attachment" in r.headers.get("content-disposition", "")
    datos = r.json()
    assert datos["cuenta"]["email"] == s["email"]
    assert [a["nombre"] for a in datos["alertas"]] == ["mía"]
    assert len(datos["notificaciones"]) == 2
    assert "hash_pwd" not in datos["cuenta"], (
        "la exportación no puede incluir el hash de la contraseña: no le sirve "
        "de nada al titular y es material de ataque")


def test_la_exportacion_nunca_incluye_datos_de_otra_organizacion(api, db):
    """CONDICIÓN EXPLÍCITA DE LA FASE.

    El derecho de acceso cubre los datos personales de quien pide, no todo lo
    que su cuenta pueda ver. Este test falla si en la exportación de A aparece
    el correo de B, el nombre de su alerta, el texto de su notificación o su
    identificador de organización.

    Que hoy no pueda pasar no es casualidad: `exportar_datos` filtra SIEMPRE por
    `usuario_id` o por la dirección del titular, y no hay ni una consulta
    filtrada por organización. Este test es lo que impide que mañana alguien
    añada una «por comodidad».
    """
    import json

    a = _sesion(db, api, f"aisla-a-{uuid.uuid4().hex[:8]}@ejemplo.com")
    b = _sesion(db, api, f"aisla-b-{uuid.uuid4().hex[:8]}@ejemplo.com")

    # Un dato inconfundible en la organización de B.
    alerta_b = db.query(models.Alerta).filter(
        models.Alerta.usuario_id == b["usuario_id"]).one()
    alerta_b.nombre = "SECRETO-COMERCIAL-DE-B"
    db.add(models.Notificacion(id=str(uuid.uuid4()), usuario_id=b["usuario_id"],
                               alerta_id=alerta_b.id, asunto="ASUNTO-DE-B",
                               cuerpo="CUERPO-DE-B", estado="pendiente"))
    db.commit()

    exportado = json.dumps(api.get(f"{API}/cuenta/exportar",
                                   headers=a["headers"]).json(), ensure_ascii=False)

    for rastro in ("SECRETO-COMERCIAL-DE-B", "ASUNTO-DE-B", "CUERPO-DE-B",
                   b["email"], b["usuario_id"], b["organizacion_id"]):
        assert rastro not in exportado, (
            f"la exportación de un usuario incluye {rastro!r}, que es de otra "
            "organización")


def test_la_exportacion_no_arrastra_los_analisis_de_la_organizacion(api, db):
    """`Analisis` cuelga de la organización y no tiene autor: no es atribuible a
    una persona. Incluirlo convertiría el derecho de acceso de un miembro en una
    vía para llevarse el trabajo de toda su organización."""
    import json

    email = f"analisis-{uuid.uuid4().hex[:8]}@ejemplo.com"
    usuario_id, org_id = sembrar_titular(db, email=email, con_analisis=True)
    headers = token_headers(api, email, PASSWORD)

    analisis = db.query(models.Analisis).filter(
        models.Analisis.organizacion_id == org_id).one()

    datos = api.get(f"{API}/cuenta/exportar", headers=headers).json()
    assert "analisis" not in datos, "la exportación no debe traer una sección de análisis"
    assert analisis.id not in json.dumps(datos), (
        "el identificador de un análisis de la organización aparece en una "
        "exportación personal")


# ═══════════════════════ Borrado con gracia ═══════════════════════

def test_pedir_el_borrado_no_borra_nada_todavia(api, db):
    """La gracia es la única defensa que queda: el borrado no tiene vuelta atrás
    y no hay copia que restaurar por usuario."""
    s = _sesion(db, api, f"gracia-{uuid.uuid4().hex[:8]}@ejemplo.com")

    r = api.delete(f"{API}/cuenta", headers=s["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["se_ejecutara_en"]

    db.expire_all()
    assert db.get(models.Usuario, s["usuario_id"]) is not None
    assert db.get(models.Usuario, s["usuario_id"]).borrado_solicitado_en is not None


def test_pedirlo_dos_veces_no_reinicia_la_cuenta_atras(api, db):
    """Si la reiniciara, repetir la petición aplazaría el borrado indefinidamente
    —y un cliente que reintentase solo alargaría la espera sin que nadie lo pida."""
    s = _sesion(db, api, f"idem-{uuid.uuid4().hex[:8]}@ejemplo.com")

    primera = api.delete(f"{API}/cuenta", headers=s["headers"]).json()["se_ejecutara_en"]
    segunda = api.delete(f"{API}/cuenta", headers=s["headers"]).json()["se_ejecutara_en"]

    assert primera == segunda


def test_cancelar_dentro_de_la_gracia_salva_la_cuenta(api, db):
    from app.services import cuenta_service

    s = _sesion(db, api, f"cancela-{uuid.uuid4().hex[:8]}@ejemplo.com")
    api.delete(f"{API}/cuenta", headers=s["headers"])

    r = api.post(f"{API}/cuenta/borrado/cancelar", headers=s["headers"])
    assert r.status_code == 200, r.text

    # Aunque la tarea corra MUY después, esta cuenta ya no es candidata. Se
    # afirma sobre ESTE usuario y no sobre el recuento: la base del módulo es
    # compartida y otros tests dejan sus propias solicitudes pendientes.
    muy_despues = datetime.now(timezone.utc) + timedelta(days=365)
    assert s["usuario_id"] not in cuenta_service.borrados_vencidos(
        db, ahora=muy_despues)
    cuenta_service.ejecutar_borrados_vencidos(db, ahora=muy_despues)

    db.expire_all()
    assert db.get(models.Usuario, s["usuario_id"]) is not None


def test_dentro_de_la_gracia_la_tarea_no_borra(api, db):
    from app.services import cuenta_service

    s = _sesion(db, api, f"pronto-{uuid.uuid4().hex[:8]}@ejemplo.com")
    api.delete(f"{API}/cuenta", headers=s["headers"])

    # Un día antes de que venza.
    casi = datetime.now(timezone.utc) + timedelta(days=cuenta_service.DIAS_DE_GRACIA - 1)
    cuenta_service.ejecutar_borrados_vencidos(db, ahora=casi)

    db.expire_all()
    assert db.get(models.Usuario, s["usuario_id"]) is not None


def test_al_vencer_la_gracia_no_queda_ni_una_fila_del_titular(api, db):
    """CONDICIÓN EXPLÍCITA DE LA FASE, versión SQLite.

    Las tablas hijas se derivan del `metadata`, no de una lista escrita a mano:
    quien añada mañana una tabla colgando de `usuario` y no la cubra en
    `borrado_service` verá este test en rojo con el nombre de su tabla.

    La misma comprobación corre contra PostgreSQL en `test_postgres.py`, que es
    donde de verdad se demuestra: aquí las claves foráneas están apagadas y un
    borrado incompleto pasaría en verde.
    """
    from app.core.db import Base
    from app.services import cuenta_service

    sin_cubrir = cobertura_de_tablas_hijas(Base.metadata)
    assert not sin_cubrir, (
        f"El escenario no siembra estas tablas hijas de `usuario`: {sorted(sin_cubrir)}. "
        "Añádelas a `escenario_rgpd.sembrar_titular` Y a "
        "`borrado_service.TABLAS_HIJAS_DE_USUARIO`.")

    s = _sesion(db, api, f"borra-{uuid.uuid4().hex[:8]}@ejemplo.com")
    api.delete(f"{API}/cuenta", headers=s["headers"])

    despues = datetime.now(timezone.utc) + timedelta(
        days=cuenta_service.DIAS_DE_GRACIA + 1)
    resumen = cuenta_service.ejecutar_borrados_vencidos(db, ahora=despues)
    assert resumen["fallidas"] == 0, resumen
    assert resumen["borradas"] >= 1, resumen

    db.expire_all()
    comprobar_sin_huerfanas(db, Base.metadata, s["usuario_id"],
                            s["organizacion_id"], s["email"])


def test_el_borrado_no_se_lleva_por_delante_una_organizacion_con_analisis(api, db):
    """Los `Analisis` son snapshots inmutables (P1) y pueden ser de más gente.
    Borrar su organización rompería la referencia sin que nadie lo pidiera."""
    from app.core.db import Base
    from app.services import cuenta_service

    email = f"conserva-{uuid.uuid4().hex[:8]}@ejemplo.com"
    usuario_id, org_id = sembrar_titular(db, email=email, con_analisis=True)
    headers = token_headers(api, email, PASSWORD)
    api.delete(f"{API}/cuenta", headers=headers)

    despues = datetime.now(timezone.utc) + timedelta(
        days=cuenta_service.DIAS_DE_GRACIA + 1)
    cuenta_service.ejecutar_borrados_vencidos(db, ahora=despues)

    db.expire_all()
    comprobar_sin_huerfanas(db, Base.metadata, usuario_id, org_id, email)
    assert db.get(models.Organizacion, org_id) is not None, (
        "se borró una organización que todavía tiene análisis colgando")


def test_la_auditoria_del_borrado_no_reintroduce_la_direccion(api, db):
    """La constancia de que se borró no puede volver a escribir el correo que se
    acaba de anonimizar. Sería deshacer el borrado con la mano derecha."""
    from app.services import cuenta_service

    s = _sesion(db, api, f"constancia-{uuid.uuid4().hex[:8]}@ejemplo.com")
    api.delete(f"{API}/cuenta", headers=s["headers"])
    despues = datetime.now(timezone.utc) + timedelta(
        days=cuenta_service.DIAS_DE_GRACIA + 1)
    cuenta_service.ejecutar_borrados_vencidos(db, ahora=despues)

    constancia = (db.query(models.Auditoria)
                  .filter(models.Auditoria.accion == "borrado_a_peticion",
                          models.Auditoria.entidad_id == s["usuario_id"]).one())
    assert constancia.quien == "sistema:rgpd"
    assert s["email"] not in str(constancia.delta)


def test_ejecutar_borrado_no_toca_una_cuenta_que_nunca_lo_pidio(api, db):
    """La comprobación dentro de la transacción no es decorativa.

    `ejecutar_borrados_vencidos` selecciona y luego borra, pero `ejecutar_borrado`
    es invocable por su cuenta y no puede fiarse de que quien la llame haya
    comprobado nada. Sin la guarda, pasarle un id cualquiera borra esa cuenta.
    """
    from app.services import cuenta_service

    s = _sesion(db, api, f"jamas-{uuid.uuid4().hex[:8]}@ejemplo.com")
    muy_despues = datetime.now(timezone.utc) + timedelta(days=365)

    assert cuenta_service.ejecutar_borrado(
        db, s["usuario_id"], ahora=muy_despues) is False

    db.expire_all()
    assert db.get(models.Usuario, s["usuario_id"]) is not None, (
        "se ha borrado una cuenta que nunca pidió el borrado")


def test_cancelar_entre_la_seleccion_y_el_borrado_salva_la_cuenta(api, db):
    """La carrera real, y la única razón de revalidar dentro de la transacción.

    La selección de vencidos ocurre FUERA de la transacción de borrado. Entre
    ambos momentos el titular puede arrepentirse, y si el borrado se fiara de la
    lista que ya tiene en la mano, cancelar justo entonces no serviría de nada:
    el derecho a echarse atrás valdría solo hasta que la tarea empezara a correr.

    Se reproduce llamando a `ejecutar_borrado` con un id que ya estaba
    seleccionado, después de cancelar — que es exactamente lo que ocurre cuando
    la cancelación llega mientras la tarea recorre su lista.
    """
    from app.services import cuenta_service

    s = _sesion(db, api, f"carrera-{uuid.uuid4().hex[:8]}@ejemplo.com")
    api.delete(f"{API}/cuenta", headers=s["headers"])

    despues = datetime.now(timezone.utc) + timedelta(
        days=cuenta_service.DIAS_DE_GRACIA + 1)
    seleccionados = cuenta_service.borrados_vencidos(db, ahora=despues)
    assert s["usuario_id"] in seleccionados, "premisa: la cuenta estaba en la lista"

    # El titular cancela con la lista ya en la mano.
    api.post(f"{API}/cuenta/borrado/cancelar", headers=s["headers"])

    assert cuenta_service.ejecutar_borrado(
        db, s["usuario_id"], ahora=despues) is False

    db.expire_all()
    assert db.get(models.Usuario, s["usuario_id"]) is not None, (
        "la cancelación llegó a tiempo y aun así se borró la cuenta")

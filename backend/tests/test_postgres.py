"""Los tres caminos que solo existen en PostgreSQL.

Hasta la fila (b) de la puerta, la CI solo corría SQLite y **estos tres caminos
no se habían ejecutado nunca, en ninguna parte**:

1. `SET LOCAL statement_timeout` en la sonda de salud (`app/api/salud.py`).
2. `with_for_update(skip_locked=True)` en la purga (`app/services/purga_service.py`).
3. `_rollback_silencioso` tras un fallo de sonda (`app/api/salud.py`).

En SQLite los tres son inertes: no hay `statement_timeout`, `FOR UPDATE` se
ignora y una sentencia fallida no aborta la transacción. Es decir, los tres
podían estar rotos y la suite habría seguido verde.

CADA TEST DE ESTE MÓDULO ESTÁ ESCRITO PARA FALLAR SI SE QUITA SU CAMINO. Un test
que pasa tanto con el camino puesto como sin él no prueba nada; la demostración
por mutación de las tres está en el PR de la fila (b) y en `docs/PENDIENTES.md`.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from app import models
from sqlalchemy.orm import sessionmaker

POSTGRES_ENV_VAR = "SEIS_TEST_POSTGRES_URL"       # dedicada: nunca DATABASE_URL

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not os.environ.get(POSTGRES_ENV_VAR),
        reason=(f"Estos tres caminos solo existen en PostgreSQL. Defina "
                f"{POSTGRES_ENV_VAR} apuntando a una base desechable cuyo nombre "
                "contenga «test» para ejecutarlos."),
    ),
]


def _url_verificada() -> str:
    """Misma salvaguarda que T5: solo una base cuyo nombre grite que es de test.

    No es paranoia decorativa. Estos tests crean y BORRAN tablas; apuntar por
    descuido a una base real —un `DATABASE_URL` de producción exportado en el
    shell— la vaciaría. De ahí que la variable sea dedicada y el nombre se exija.
    """
    url = os.environ[POSTGRES_ENV_VAR]
    if not url.startswith(("postgresql://", "postgresql+psycopg://",
                           "postgresql+psycopg2://")):
        raise RuntimeError(f"{POSTGRES_ENV_VAR} no apunta a PostgreSQL: {url!r}")
    nombre = url.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in nombre.lower():
        raise RuntimeError(
            f"Guarda de aislamiento: la base {nombre!r} no lleva «test» en el "
            "nombre. Estos tests borran tablas; se niegan a tocar una base que no "
            "se declare desechable.")
    return url


@pytest.fixture(scope="module")
def motor():
    from app import models                        # noqa: F401 — puebla el metadata
    from app.core.db import Base

    assert models.Usuario.__tablename__            # el import no es decorativo

    motor = create_engine(_url_verificada(), pool_pre_ping=True)
    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)
    yield motor
    Base.metadata.drop_all(motor)
    motor.dispose()


@pytest.fixture
def sesiones(motor):
    return sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


# ═══════════════ 1 · SET LOCAL statement_timeout ═══════════════

def test_el_statement_timeout_corta_de_verdad_una_consulta_lenta(sesiones) -> None:
    """La sonda promete acotar su consulta. Aquí se comprueba que la acota.

    Sin el `SET LOCAL`, `pg_sleep(1)` termina tranquilamente y la sonda de salud
    puede quedarse colgada tanto como tarde la base — que es justo lo que una
    sonda de readiness no puede permitirse: un `/health/listo` lento hace que el
    balanceador considere viva una réplica que no lo está.
    """
    from app.api.salud import _aplicar_timeout_bd
    from sqlalchemy.exc import OperationalError

    db = sesiones()
    try:
        _aplicar_timeout_bd(db, 0.05)                # 50 ms
        with pytest.raises(OperationalError) as excinfo:
            db.execute(text("SELECT pg_sleep(1)"))
        assert "statement timeout" in str(excinfo.value).lower(), (
            "la consulta debía morir por el timeout, no por otra cosa")
    finally:
        db.rollback()
        db.close()


def test_el_timeout_es_local_y_desaparece_al_confirmar_la_transaccion(motor) -> None:
    """`SET LOCAL` vive dentro de la transacción y no viaja con la conexión.

    Importa porque con `SET` a secas la conexión volvería al pool con un techo de
    50 ms puesto, y la siguiente petición que la reutilizara —un informe, una
    ingesta— moriría a mitad sin que nada señalara a la sonda de salud como
    culpable. Un fallo que apunta al sitio equivocado, otra vez.

    MATIZ MEDIDO, NO SUPUESTO, y es la razón de que este test confirme la
    transacción en lugar de limitarse a cerrarla: en PostgreSQL un `SET` a secas
    **también** se deshace con el `ROLLBACK`. La diferencia entre las dos grafías
    solo se ve al CONFIRMAR:

        SET LOCAL  tras COMMIT → 0
        SET        tras COMMIT → 50ms

    Consecuencia honesta: por el camino real de hoy —`get_db` cierra sin
    confirmar— las dos grafías se comportarían igual, así que un test que
    reprodujera exactamente ese camino **no distinguiría nada** y sería
    precisamente el tipo de test que aquí no se acepta. Este confirma a
    propósito: fija la propiedad que el código dice tener, para el día en que un
    llamante nuevo escriba algo en la misma transacción que la sonda.
    """
    from app.api.salud import _aplicar_timeout_bd
    from sqlalchemy.orm import Session

    conexion = motor.connect()
    try:
        db = Session(bind=conexion)
        _aplicar_timeout_bd(db, 0.05)
        assert db.execute(text("SHOW statement_timeout")).scalar() == "50ms", (
            "premisa: el techo debe llegar a estar puesto dentro de la transacción")
        db.commit()
        db.close()

        vigente = conexion.execute(text("SHOW statement_timeout")).scalar()
        assert vigente != "50ms", (
            f"el statement_timeout sobrevivió a la transacción ({vigente}): la "
            "conexión vuelve al pool contaminada y romperá una consulta ajena. "
            "Señal de que `SET LOCAL` se ha convertido en `SET`.")
    finally:
        conexion.close()


# ═══════════════ 2 · with_for_update(skip_locked=True) ═══════════════

def _usuario_purgable(db, email: str):
    """Una cuenta que cumple el predicado de purga: sin verificar y antigua."""
    from app import models
    from app.services import usuario_service

    org = usuario_service.crear_organizacion(db, f"Org {email}")
    usuario = usuario_service.crear_usuario(db, email, "ClaveLarga-123", "Zombi",
                                            "analista", organizacion_id=org.id,
                                            rol_org="propietario")
    usuario.email_verificado = False
    usuario.activo = False
    usuario.creado_en = datetime.now(timezone.utc) - timedelta(days=90)
    db.commit()
    assert isinstance(usuario, models.Usuario)
    return usuario.id


def test_una_cuenta_bloqueada_por_otra_sesion_se_salta_en_vez_de_esperar(
        sesiones) -> None:
    """`skip_locked=True` es lo que impide que la purga se quede colgada.

    La purga corre a las 04:30 sobre una lista de candidatas. Si una de ellas
    está bloqueada por otra transacción —alguien verificando su cuenta en ese
    mismo instante—, sin `skip_locked` la tarea **espera**, y mientras espera no
    purga ninguna de las demás. Una fila en disputa congela el lote entero.

    Con `skip_locked` esa fila se salta y se atenderá mañana, que es lo correcto:
    quien está verificando su cuenta ahora mismo no es un abandono.

    Cómo se detecta la ausencia del salto: la sesión que purga lleva un
    `lock_timeout` de 1 s. Con `skip_locked` no llega a esperar nunca, así que el
    plazo no se usa; sin él, espera, agota el plazo y el test se pone rojo en vez
    de colgarse para siempre.
    """
    from app.services import purga_service

    db_alta = sesiones()
    try:
        usuario_id = _usuario_purgable(db_alta, "zombi-bloqueado@ejemplo.test")
    finally:
        db_alta.close()

    bloqueo_puesto = threading.Event()
    soltar_bloqueo = threading.Event()

    def retener():
        """Otra sesión mantiene la fila bloqueada mientras la purga la visita."""
        db = sesiones()
        try:
            db.execute(text("SELECT id FROM usuario WHERE id = :i FOR UPDATE"),
                       {"i": usuario_id}).fetchone()
            bloqueo_puesto.set()
            soltar_bloqueo.wait(timeout=30)
        finally:
            db.rollback()
            db.close()

    hilo = threading.Thread(target=retener, daemon=True)
    hilo.start()
    assert bloqueo_puesto.wait(timeout=10), "no se pudo bloquear la fila"

    db_purga = sesiones()
    try:
        db_purga.execute(text("SET LOCAL lock_timeout = '1s'"))
        borrado, org_borrada = purga_service.purgar_cuenta_sin_verificar(
            db_purga, usuario_id, ahora=datetime.now(timezone.utc), dias=30)
        assert (borrado, org_borrada) == (False, False), (
            "una fila bloqueada por otra sesión debe saltarse, no purgarse")
    finally:
        db_purga.rollback()
        db_purga.close()
        soltar_bloqueo.set()
        hilo.join(timeout=10)

    # Y saltarla no puede significar perderla: sigue ahí para el lote siguiente.
    from app import models
    db = sesiones()
    try:
        assert db.get(models.Usuario, usuario_id) is not None
    finally:
        db.close()


# ═══════════════ 3 · _rollback_silencioso ═══════════════

def test_un_fallo_de_sonda_no_arrastra_a_las_lecturas_siguientes(sesiones) -> None:
    """El caso exacto que documenta `_rollback_silencioso`.

    En PostgreSQL una sentencia fallida deja la transacción ABORTADA: todo lo que
    venga después en esa sesión falla con `InFailedSqlTransaction`. `/health/detalle`
    hace tres lecturas seguidas sobre la misma sesión, y la primera —`alembic_version`—
    falla legítimamente en cualquier base creada con `create_all`.

    Sin el rollback, ese fallo legítimo contagiaría a las dos siguientes y el
    diagnóstico diría que **el conocimiento no se puede leer**, mandando a quien
    esté de guardia a buscar un problema que no existe. Culpar a tres cosas
    cuando solo falla una es peor que no diagnosticar.
    """
    from app.api.salud import DESCONOCIDA, _revision_alembic, _versiones_conocimiento
    from scripts.sembrar import sembrar_conocimiento

    db = sesiones()
    try:
        sembrar_conocimiento(db)

        # La tabla de Alembic no existe: el esquema lo creó `create_all`.
        assert _revision_alembic(db) == DESCONOCIDA, (
            "premisa del test: esta lectura debe fallar de verdad. Si no falla, "
            "lo de abajo no prueba nada.")

        version_reglas, version_parametros = _versiones_conocimiento(db)

        assert version_reglas != DESCONOCIDA, (
            "el fallo de `alembic_version` se llevó por delante la lectura de "
            "reglas: la transacción quedó abortada y nadie la revirtió")
        assert version_parametros != DESCONOCIDA
    finally:
        db.rollback()
        db.close()


def test_el_rollback_deja_la_sesion_utilizable_para_cualquier_consulta(
        sesiones) -> None:
    """La versión mínima del mismo invariante, sin depender del conocimiento."""
    from app.api.salud import _rollback_silencioso
    from sqlalchemy.exc import ProgrammingError

    db = sesiones()
    try:
        with pytest.raises(ProgrammingError):
            db.execute(text("SELECT * FROM tabla_que_no_existe_jamas"))

        _rollback_silencioso(db)

        assert db.execute(text("SELECT 1")).scalar_one() == 1, (
            "tras un fallo, la sesión sigue abortada: el rollback no ocurrió")
    finally:
        db.rollback()
        db.close()


# ═══════════════ 4 · Borrado RGPD sin filas huérfanas (Fase 14) ═══════════════

def test_el_borrado_rgpd_no_deja_filas_huerfanas_en_postgres(sesiones) -> None:
    """La misma comprobación que en SQLite, en el motor donde SÍ demuestra algo.

    En SQLite las claves foráneas están apagadas por defecto y la suite no las
    enciende: si `borrado_service` se dejara una tabla hija, el `DELETE FROM
    usuario` pasaría igual y quedarían filas con datos personales colgando de un
    usuario inexistente, en verde. Aquí no: PostgreSQL rechaza el borrado y la
    transacción entera se aborta.

    Es decir, en SQLite este escenario comprueba que el borrado es COMPLETO;
    aquí comprueba además que es POSIBLE. Son dos cosas distintas y hacen falta
    las dos, que es el motivo de que el escenario viva en `escenario_rgpd.py` y
    no duplicado en dos módulos.
    """
    import uuid
    from datetime import datetime, timedelta, timezone

    from app.core.db import Base
    from app.services import cuenta_service
    from tests.escenario_rgpd import (cobertura_de_tablas_hijas,
                                      comprobar_sin_huerfanas, sembrar_titular)

    sin_cubrir = cobertura_de_tablas_hijas(Base.metadata)
    assert not sin_cubrir, (
        f"El escenario no siembra estas tablas hijas de `usuario`: {sorted(sin_cubrir)}")

    db = sesiones()
    try:
        email = f"rgpd-pg-{uuid.uuid4().hex[:8]}@ejemplo.test"
        usuario_id, org_id = sembrar_titular(db, email=email)

        usuario = db.get(models.Usuario, usuario_id)
        cuenta_service.solicitar_borrado(db, usuario)

        despues = datetime.now(timezone.utc) + timedelta(
            days=cuenta_service.DIAS_DE_GRACIA + 1)
        assert cuenta_service.ejecutar_borrado(db, usuario_id, ahora=despues) is True

        db.expire_all()
        comprobar_sin_huerfanas(db, Base.metadata, usuario_id, org_id, email)
    finally:
        db.rollback()
        db.close()


def test_en_postgres_un_borrado_incompleto_ABORTA_en_vez_de_pasar_en_verde(
        sesiones) -> None:
    """Por qué este módulo existe, demostrado sobre el propio motor.

    Se borra al usuario **sin** borrar antes sus hijas, que es exactamente lo
    que pasaría si alguien añadiera una tabla y olvidara ponerla en
    `TABLAS_HIJAS_DE_USUARIO`. PostgreSQL lo rechaza. En SQLite, con las claves
    foráneas apagadas, esto mismo pasaría en verde dejando datos personales
    colgando — y por eso el test de SQLite no basta.
    """
    import uuid

    from sqlalchemy.exc import IntegrityError
    from tests.escenario_rgpd import sembrar_titular

    db = sesiones()
    try:
        email = f"incompleto-{uuid.uuid4().hex[:8]}@ejemplo.test"
        usuario_id, _org = sembrar_titular(db, email=email)

        with pytest.raises(IntegrityError):
            db.query(models.Usuario).filter(
                models.Usuario.id == usuario_id).delete(synchronize_session=False)
            db.flush()
    finally:
        db.rollback()
        db.close()

"""Fixtures compartidas de la suite SEIS."""
import os
import shutil
import tempfile
from pathlib import Path

# Configuración de test: debe fijarse antes de importar la aplicación
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "1")
os.environ.setdefault("JWT_SECRET", "secreto-de-test")
os.environ.setdefault("ADMIN_PASSWORD", "admin")

# ─────────────────── Base de datos PROPIA de la suite ───────────────────
#
# `app.core.db` crea su `engine` al importarse, con `get_settings().database_url`,
# cuyo valor por defecto es `sqlite:///./seis_dev.db`: el MISMO fichero que usa el
# backend de desarrollo arrancado desde `backend/`. Sin esto, la fixture `api`
# hacía `drop_all` sobre esa base y después la borraba (incidente del 2026-09-24:
# la base de desarrollo quedó en 0 bytes tras ejecutar la suite).
#
# Por eso la URL se fija AQUÍ, antes de cualquier import de la app: pytest carga
# este fichero antes de recolectar ningún test, y los 26 módulos que hacen
# `from app.core.db import ...` se recolectan después. La base vive en un
# directorio temporal del sistema, FUERA del repositorio, con ruta absoluta: no
# depende del directorio desde el que se lance pytest.
#
# Asignación directa y no `setdefault`: un `DATABASE_URL` exportado en la terminal
# (el de desarrollo o, por descuido, uno de producción) no debe llegar nunca a una
# suite que hace `drop_all`. Mismo criterio que `SEIS_TEST_POSTGRES_URL`: PostgreSQL
# tiene su variable dedicada y sus propios engines.
#
# El directorio se anota en el entorno para que un segundo import de este módulo
# (`from tests.conftest import …`) reutilice la MISMA base en vez de crear otra.
_VAR_DIR_BD = "SEIS_PYTEST_DIR_BD"
if not os.environ.get(_VAR_DIR_BD) or not Path(os.environ[_VAR_DIR_BD]).is_dir():
    os.environ[_VAR_DIR_BD] = tempfile.mkdtemp(prefix="seis-pytest-")
DIR_BD_TESTS = Path(os.environ[_VAR_DIR_BD]).resolve()
RUTA_BD_TESTS = DIR_BD_TESTS / "tests.db"
os.environ["DATABASE_URL"] = f"sqlite:///{RUTA_BD_TESTS.as_posix()}"

RAIZ_REPO = Path(__file__).resolve().parents[2]
RUTA_BD_DESARROLLO = RAIZ_REPO / "backend" / "seis_dev.db"


def problema_de_aislamiento(url, esperada: Path, directorio: Path, raiz_repo: Path) -> str | None:
    """Motivo por el que la base EFECTIVA no es la desechable de la suite, o `None`.

    Recibe la URL del engine (no la variable de entorno): lo que cuenta es contra
    qué base va a ejecutarse `drop_all`, no lo que diga `os.environ`.
    """
    from sqlalchemy.engine import make_url

    url = make_url(str(url))
    if url.get_backend_name() != "sqlite" or not url.database:
        return f"la suite solo admite su SQLite desechable y el engine apunta a {url!r}"
    ruta = Path(url.database).resolve()
    if ruta.name == "seis_dev.db":
        return f"el engine apunta a la base de DESARROLLO ({ruta})"
    try:
        ruta.relative_to(directorio.resolve())
    except ValueError:
        return f"la base {ruta} está fuera del directorio temporal de la suite ({directorio})"
    if ruta != esperada.resolve():
        return f"la base {ruta} no es la esperada ({esperada})"
    try:
        directorio.resolve().relative_to(raiz_repo.resolve())
        return f"el directorio temporal {directorio} está DENTRO del repositorio"
    except ValueError:
        return None


def verificar_bd_de_tests() -> None:
    """Aborta la sesión entera si el engine global no es la base desechable.

    Se llama antes de cualquier `create_all`/`drop_all`. `pytest.exit` y no
    `assert`: un fallo aquí no es un test rojo, es una suite que no debe seguir.
    """
    from app.core.db import engine

    motivo = problema_de_aislamiento(engine.url, RUTA_BD_TESTS, DIR_BD_TESTS, RAIZ_REPO)
    if motivo:
        pytest.exit(f"Aislamiento de la base de tests ROTO: {motivo}. "
                    "No se ejecuta nada para no tocar datos reales.", returncode=3)

import pytest

from app.engine.contracts import (ActivoInput, AnalisisInput, ComparableInput,
                                  CostesInput, DocumentosInput, FinanciacionInput,
                                  OcupacionInput, ReformaInput, SubastaInput,
                                  ZonaInput, ZonaMacroInput, ZonaMicroInput)


def entrada_base(**overrides) -> AnalisisInput:
    """Entrada mínima válida tipo caso §19; los tests la mutan por campos."""
    base = dict(
        perfil="flip_integral",
        activo=ActivoInput(tipologia="vivienda", superficie_m2=82,
                           estado_conservacion="malo", anio_construccion=1975,
                           municipio="Ciudad Ejemplo", provincia="Ejemplo", ccaa="ejemplo"),
        subasta=SubastaInput(fuente="judicial_boe", valor_subasta=152000,
                             deposito_pct=0.05, horas_hasta_cierre=200),
        ocupacion=OcupacionInput(estado="precario"),
        documentos=DocumentosInput(nota_simple=True, nota_simple_dias=10, cert_cargas=True,
                                   avaluo=True, fotos_exterior=True, recibo_ibi=True,
                                   catastro_conciliado=True),
        comparables=[ComparableInput(precio_m2=v, estado="reformado")
                     for v in (2100, 2200, 2250, 2293, 2350, 2420, 2490)],
        zona=ZonaInput(macro=ZonaMacroInput(tendencia_5a_pct=3.0, stock_meses=6,
                                            dom_venta_dias=75, dom_alquiler_dias=25,
                                            crecimiento_pobl_5a_pct=0.5, renta_hogar=32000,
                                            y_zona_pct=5.5),
                       micro=ZonaMicroInput(transporte=70, seguridad=60, sanidad=65,
                                            educacion=60, comercio=70, zonas_verdes=55,
                                            pipeline_urbanistico=55, potencial_transformacion=60,
                                            entorno_construido=65)),
        reforma=ReformaInput(visita_interior=False),
        costes=CostesInput(itp_tipo_override=0.06),
        financiacion=FinanciacionInput(tipo="cash"),
    )
    base.update(overrides)
    return AnalisisInput(**base)


@pytest.fixture
def base_input():
    return entrada_base()


ADMIN = {"username": "admin@seis.local", "password": "admin"}


@pytest.fixture(autouse=True)
def _limpiar_rate_limit():
    """Cada test arranca y termina con el limitador anti-abuso a cero (Fase 10).

    Es `autouse` porque son estado de proceso compartido: sin esto, un test que
    agota los intentos de login dejaría bloqueado al siguiente, y el fallo
    aparecería en un fichero que no tiene nada que ver con la causa.
    """
    from app.api import salud
    from app.core import rate_limit, red

    # Tres estados DE PROCESO, no de base de datos: el limitador, los contadores
    # de resolución de IP (Fase 16, A-2) y la caché de la sonda de readiness
    # (M-2). Los tres se filtrarían entre tests y harían que un fallo dependiera
    # del orden — que es como se descubrieron los dos últimos.
    rate_limit.limpiar_todo()
    red.reiniciar_recuento()
    salud.reiniciar_cache_sonda()
    yield
    rate_limit.limpiar_todo()
    red.reiniciar_recuento()
    salud.reiniciar_cache_sonda()


@pytest.fixture(scope="session", autouse=True)
def _bd_de_tests_aislada():
    """Comprueba el aislamiento ANTES del primer test y retira la base al final.

    Al terminar: `engine.dispose()` suelta las conexiones (en Windows, sin esto el
    fichero sigue bloqueado) y se borra SOLO el directorio temporal de la suite,
    que la guarda ya ha verificado que está fuera del repositorio. Si Windows lo
    mantiene bloqueado, se deja en el TEMP del sistema: nunca se toca el repo.
    """
    verificar_bd_de_tests()
    yield
    from app.core.db import engine

    engine.dispose()
    if problema_de_aislamiento(engine.url, RUTA_BD_TESTS, DIR_BD_TESTS, RAIZ_REPO) is None:
        shutil.rmtree(DIR_BD_TESTS, ignore_errors=True)


@pytest.fixture(scope="module")
def api():
    """Cliente HTTP con esquema creado, admin superadmin sembrado y limpieza al terminar.

    Trabaja sobre la base desechable de la suite (ver cabecera del módulo), nunca
    sobre `seis_dev.db`: la guarda se repite aquí, junto a `create_all`/`drop_all`,
    porque son las dos operaciones que destruirían datos reales.
    """
    from fastapi.testclient import TestClient
    from app.core.db import Base, SessionLocal, engine
    from app.main import app
    from app.services import usuario_service

    verificar_bd_de_tests()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if not usuario_service.obtener_por_email(db, ADMIN["username"]):
            # Fase 9: el admin bootstrap es propietario + superadmin de la org por defecto.
            org = usuario_service.crear_organizacion(db, "Organización por defecto")
            usuario_service.crear_usuario(db, ADMIN["username"], ADMIN["password"],
                                          "Admin", "admin", organizacion_id=org.id,
                                          rol_org="propietario", es_superadmin=True)
    finally:
        db.close()
    with TestClient(app) as c:
        yield c
    # Cada módulo deja la base sin tablas, como antes. Ya no se borra ningún
    # fichero: el antiguo `os.remove("seis_dev.db")` borraba la base de desarrollo.
    verificar_bd_de_tests()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="module")
def headers(api):
    r = api.post("/api/v1/auth/login", data=ADMIN)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def token_headers(api, email: str, password: str) -> dict:
    """Atajo: inicia sesión y devuelve la cabecera Authorization."""
    r = api.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def dos_organizaciones(api):
    """Org A y Org B, cada una con un analista propio (patrón de test_multitenant.py).

    Compartida desde la Fase 17-A: el aislamiento del matcher (test_notificaciones)
    y el alcance del origen plataforma (test_ingesta) prueban caras opuestas del
    mismo escenario y deben mirar exactamente el mismo montaje.
    """
    from app.core.db import SessionLocal
    from app.services import usuario_service

    db = SessionLocal()
    try:
        org_a = usuario_service.crear_organizacion(db, "Org Aislamiento A")
        usuario_service.crear_usuario(db, "analistaA@example.com", "claveA123", "Ana A",
                                      rol="analista", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        org_b = usuario_service.crear_organizacion(db, "Org Aislamiento B")
        usuario_service.crear_usuario(db, "analistaB@example.com", "claveB123", "Ana B",
                                      rol="analista", organizacion_id=org_b.id,
                                      rol_org="miembro", es_superadmin=False)
    finally:
        db.close()
    return {"a_h": token_headers(api, "analistaA@example.com", "claveA123"),
            "b_h": token_headers(api, "analistaB@example.com", "claveB123")}

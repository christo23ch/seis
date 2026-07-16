"""Fixtures compartidas de la suite SEIS."""
import os

# Configuración de test: debe fijarse antes de importar la aplicación
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "1")
os.environ.setdefault("JWT_SECRET", "secreto-de-test")
os.environ.setdefault("ADMIN_PASSWORD", "admin")

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


@pytest.fixture(scope="module")
def api():
    """Cliente HTTP con esquema creado, admin superadmin sembrado y limpieza al terminar."""
    from fastapi.testclient import TestClient
    from app.core.db import Base, SessionLocal, engine
    from app.main import app
    from app.services import usuario_service

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
    Base.metadata.drop_all(engine)
    engine.dispose()
    if os.path.exists("seis_dev.db"):
        os.remove("seis_dev.db")


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


@pytest.fixture(autouse=True)
def _rate_limit_limpio():
    """Fase 10: evita que los intentos fallidos de un test de fuerza bruta
    contaminen el siguiente (el cliente `api` es de módulo, no por test)."""
    from app.core import rate_limit
    rate_limit.limpiar_todo()
    yield
    rate_limit.limpiar_todo()

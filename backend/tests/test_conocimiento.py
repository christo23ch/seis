"""Gobernanza del conocimiento: parámetros con vigencia, versiones de reglas y perfiles.
El motor debe reflejar los cambios de BD inmediatamente (fuente de verdad viva)."""
import json

import pytest

from app.engine.contracts import CostesInput
from tests.conftest import entrada_base


@pytest.fixture(scope="module", autouse=True)
def sembrar(api):
    """Siembra reglas/perfiles/parámetros de la semilla YAML en la BD de test."""
    from scripts.init_db import main
    main()


def _simular(api, headers, **overrides):
    payload = json.loads(entrada_base(**overrides).model_dump_json())
    r = api.post("/api/v1/analisis/simular", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_override_parametro_cambia_calculo(api, headers):
    # sin override de ITP en la entrada ⇒ el motor usa la tabla T3 (ccaa 'ejemplo' = 6%)
    antes = _simular(api, headers, costes=CostesInput())
    assert antes["costes"]["c_v"] == pytest.approx(0.064, abs=0.0005)

    r = api.put("/api/v1/parametros", headers=headers,
                json={"clave": "fiscal.itp_por_ccaa.ejemplo", "valor": 0.08,
                      "fuente_legal": "Simulación de subida autonómica (test)"})
    assert r.status_code == 200

    despues = _simular(api, headers, costes=CostesInput())
    assert despues["costes"]["c_v"] == pytest.approx(0.084, abs=0.0005)
    assert "+1ov" in despues["decision"]["version_parametros"]
    # los precios bajan al encarecerse la adquisición (prudencia coherente)
    assert despues["decision"]["precios"]["p_objetivo"] < antes["decision"]["precios"]["p_objetivo"]

    # restaurar para no contaminar módulos posteriores
    api.put("/api/v1/parametros", headers=headers,
            json={"clave": "fiscal.itp_por_ccaa.ejemplo", "valor": 0.06,
                  "fuente_legal": "restauración test"})


def test_parametro_ruta_desconocida_400(api, headers):
    r = api.put("/api/v1/parametros", headers=headers,
                json={"clave": "fiscal.no.existe", "valor": 1})
    assert r.status_code == 400


def test_nueva_version_de_regla_con_vigencia(api, headers):
    r = api.get("/api/v1/reglas", headers=headers)
    definicion = next(x for x in r.json()["reglas"] if x["codigo"] == "SEM-EJEC-01")
    nueva = {**definicion,
             "efecto": {"condicion": "Judicial: condición revisada por el comité (v2)"}}
    r = api.post("/api/v1/reglas", headers=headers,
                 json={"definicion": nueva, "justificacion": "Ajuste de redacción del comité"})
    assert r.status_code == 201
    version_nueva = r.json()["version"]

    hist = api.get("/api/v1/reglas/SEM-EJEC-01/historial", headers=headers).json()
    assert len(hist) == 2
    assert hist[0]["vigente_hasta"] is not None            # la antigua queda cerrada
    vigentes = api.get("/api/v1/reglas", headers=headers).json()["reglas"]
    activa = next(x for x in vigentes if x["codigo"] == "SEM-EJEC-01")
    assert activa["version"] == version_nueva

    # el motor usa ya la nueva redacción y estampa la versión del catálogo
    res = _simular(api, headers)
    assert any("v2" in c for c in res["decision"]["condiciones"])
    assert res["decision"]["version_reglas"] == version_nueva


def test_regla_invalida_400(api, headers):
    r = api.post("/api/v1/reglas", headers=headers,
                 json={"definicion": {"codigo": "X", "cuando": {"all": [{"hecho": "a", "op": "%%"}]},
                                      "efecto": {"condicion": "x"}},
                       "justificacion": "debe fallar"})
    assert r.status_code == 400


def test_actualizar_perfil_afecta_precios(api, headers):
    original = api.get("/api/v1/perfiles", headers=headers).json()["flip_integral"]
    antes = _simular(api, headers)["decision"]["precios"]["p_objetivo"]

    exigente = {**original, "m_objetivo": 0.35}
    r = api.put("/api/v1/perfiles/flip_integral", headers=headers,
                json={"parametros": exigente})
    assert r.status_code == 200
    despues = _simular(api, headers)["decision"]["precios"]["p_objetivo"]
    assert despues < antes                                  # más margen exigido ⇒ pagar menos

    api.put("/api/v1/perfiles/flip_integral", headers=headers,
            json={"parametros": original})                  # restaurar


def test_perfil_invalido(api, headers):
    r = api.put("/api/v1/perfiles/flip_integral", headers=headers,
                json={"parametros": {"tipo": "venta"}})
    assert r.status_code == 400
    r = api.put("/api/v1/perfiles/no_existe", headers=headers,
                json={"parametros": {"tipo": "venta", "m_objetivo": 0.2,
                                     "m_minimo": 0.1, "rvc_veto": 0.8}})
    assert r.status_code == 404

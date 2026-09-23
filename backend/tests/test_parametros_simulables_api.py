"""Fase 5F.7.2 — catálogo HTTP de parámetros simulables de un análisis.

`GET /analisis/{id}/parametros-simulables` entrega lo que un editor de
overrides necesita sin que el frontend tenga ninguna lista, tipo, rango ni
etiqueta propia. Solo lectura: no ejecuta el motor, no escribe, no audita.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app import models
from app.core.db import SessionLocal
from tests.conftest import entrada_base, token_headers

# Recuentos medidos en el Paso 0 de 5F.7.2 contra `cargar_conocimiento` y el
# catálogo de 5C/5C.1: 53 fijos + 50 instancias (22 perfil, 20 banda, 8 fuente).
N_EDITABLES, N_NUMERICOS, N_ESTRUCTURAS = 103, 92, 11
N_NO_EDITABLES, N_DERIVADOS = 12, 6


@pytest.fixture(scope="module")
def orgs(api):
    from app.services import usuario_service

    db = SessionLocal()
    try:
        org_a = usuario_service.crear_organizacion(db, "Org Catálogo A")
        usuario_service.crear_usuario(db, "cat-a@example.com", "claveA123", "Cat A",
                                      rol="analista", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        usuario_service.crear_usuario(db, "cat-lector-a@example.com", "claveL123", "Lector A",
                                      rol="lector", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        org_b = usuario_service.crear_organizacion(db, "Org Catálogo B")
        usuario_service.crear_usuario(db, "cat-b@example.com", "claveB123", "Cat B",
                                      rol="analista", organizacion_id=org_b.id,
                                      rol_org="miembro", es_superadmin=False)
    finally:
        db.close()
    return {"a_h": token_headers(api, "cat-a@example.com", "claveA123"),
            "b_h": token_headers(api, "cat-b@example.com", "claveB123"),
            "lector_h": token_headers(api, "cat-lector-a@example.com", "claveL123")}


def _analisis(api, h) -> str:
    payload = json.loads(entrada_base().model_dump_json())   # flip_integral · judicial_boe
    r = api.post("/api/v1/analisis", json=payload, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _url(aid: str) -> str:
    return f"/api/v1/analisis/{aid}/parametros-simulables"


def _catalogo(api, h, aid) -> dict:
    r = api.get(_url(aid), headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _por_clave(cat: dict) -> dict[str, dict]:
    return {e["clave"]: e for e in cat["editables"]}


def _contar(modelo) -> int:
    db = SessionLocal()
    try:
        return db.query(modelo).count()
    finally:
        db.close()


_CAMPOS_EDITABLE = {"clave", "nombre_legible", "modulo", "descripcion", "unidad", "tipo",
                    "rango", "advertencia", "impacto", "nivel_riesgo_modificacion",
                    "dependencia", "origen", "plantilla", "valor_vigente", "valor_original",
                    "difiere_de_original"}


# ─────────────────────────── A. Forma y recuentos ───────────────────────────

def test_recuentos_y_forma_de_la_respuesta(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    cat = _catalogo(api, orgs["a_h"], aid)

    assert set(cat) == {"analisis_id", "version_parametros_vigente",
                        "tiene_parametros_originales", "editables", "no_editables", "derivados"}
    assert cat["analisis_id"] == aid
    assert isinstance(cat["version_parametros_vigente"], str) and cat["version_parametros_vigente"]
    assert len(cat["editables"]) == N_EDITABLES
    assert len(cat["no_editables"]) == N_NO_EDITABLES
    assert len(cat["derivados"]) == N_DERIVADOS
    for e in cat["editables"]:
        assert set(e) == _CAMPOS_EDITABLE
    for e in cat["no_editables"]:
        assert set(e) == {"clave", "nombre_legible", "modulo", "descripcion", "unidad", "origen"}
    for d in cat["derivados"]:
        assert set(d) == {"nombre", "modulo", "descripcion", "origen"}


def test_tipo_lo_calcula_el_backend_numero_o_estructura(api, orgs):
    cat = _catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"]))
    tipos = [e["tipo"] for e in cat["editables"]]
    assert tipos.count("numero") == N_NUMERICOS
    assert tipos.count("estructura") == N_ESTRUCTURAS
    por_clave = _por_clave(cat)
    assert por_clave["capital.coste_capital_anual"]["tipo"] == "numero"
    assert por_clave["riesgos.bandas_ra"]["tipo"] == "estructura"
    assert por_clave["adjudicacion.ratios.judicial_boe"]["tipo"] == "estructura"


def test_grupos_disjuntos(api, orgs):
    cat = _catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"]))
    editables = [e["clave"] for e in cat["editables"]]
    no_editables = [e["clave"] for e in cat["no_editables"]]
    assert len(set(editables)) == len(editables)
    assert len(set(no_editables)) == len(no_editables)
    assert not set(editables) & set(no_editables)
    assert not set(editables) & {d["nombre"] for d in cat["derivados"]}


def test_rango_y_dependencia_tal_cual_del_catalogo(api, orgs):
    por_clave = _por_clave(_catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"])))
    assert por_clave["semaforo.verde.ico_min"]["rango"] == [0.0, 100.0]
    assert por_clave["capital.coste_capital_anual"]["rango"] == "pendiente_de_definir"
    assert {e["dependencia"] for e in por_clave.values()} <= {"A", "B"}


def test_orden_estable(api, orgs):
    cat = _catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"]))
    claves = [(e["modulo"], e["clave"]) for e in cat["editables"]]
    assert claves == sorted(claves)
    assert [e["clave"] for e in cat["no_editables"]] == sorted(e["clave"] for e in cat["no_editables"])
    assert [d["nombre"] for d in cat["derivados"]] == sorted(d["nombre"] for d in cat["derivados"])


# ─────────────────── B. El catálogo HTTP y el validador dicen lo mismo ───────────────────

def test_toda_clave_editable_es_aceptada_por_post_simulaciones(api, orgs):
    """Si el catálogo ofreciera una clave que el validador rechaza (o con un
    valor de otra forma), el editor construiría peticiones que dan 422."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    cat = _catalogo(api, h, aid)
    overrides = {e["clave"]: e["valor_vigente"] for e in cat["editables"]}

    r = api.post(f"/api/v1/analisis/{aid}/simulaciones", json={"overrides": overrides},
                 headers=h)

    assert r.status_code == 201, r.text
    assert len(r.json()["overrides"]) == N_EDITABLES


# ─────────────────────────── C. Valores original y vigente ───────────────────────────

def test_analisis_recien_creado_original_igual_a_vigente(api, orgs):
    cat = _catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"]))
    assert cat["tiene_parametros_originales"] is True
    for e in cat["editables"]:
        assert e["valor_original"] == e["valor_vigente"], e["clave"]
        assert e["difiere_de_original"] is False, e["clave"]


def test_valor_vigente_viene_del_mismo_arbol_que_usa_la_simulacion(api, orgs):
    from app.services import conocimiento_service

    cat = _catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"]))
    db = SessionLocal()
    try:
        params, _, _ = conocimiento_service.cargar_conocimiento(db)
    finally:
        db.close()
    assert cat["version_parametros_vigente"] == params.version
    for e in cat["editables"]:
        assert e["valor_vigente"] == params.get(e["clave"]), e["clave"]


def test_difiere_de_original_cuando_el_arbol_original_es_distinto(api, orgs):
    """Se altera el snapshot ORIGINAL del análisis (no el conocimiento global)
    para no contaminar a otros tests: la comparación la hace el backend."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    db = SessionLocal()
    try:
        a = db.get(models.Analisis, aid)
        arbol = json.loads(json.dumps(a.parametros_aplicados))
        arbol["capital"]["coste_capital_anual"] = 0.5
        a.parametros_aplicados = arbol
        db.commit()
    finally:
        db.close()

    e = _por_clave(_catalogo(api, h, aid))["capital.coste_capital_anual"]
    assert e["valor_original"] == 0.5
    assert e["valor_vigente"] != 0.5
    assert e["difiere_de_original"] is True


def test_analisis_sin_parametros_aplicados_declara_la_carencia(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    db = SessionLocal()
    try:
        db.get(models.Analisis, aid).parametros_aplicados = None
        db.commit()
    finally:
        db.close()

    cat = _catalogo(api, h, aid)

    assert cat["tiene_parametros_originales"] is False
    for e in cat["editables"]:
        assert e["valor_original"] is None, e["clave"]
        assert e["difiere_de_original"] is None, e["clave"]
        assert e["valor_vigente"] is not None, e["clave"]   # nunca se rellena con el vigente


# ─────────────────────────── D. Plantillas y coincidencia ───────────────────────────

def test_parametro_fijo_no_tiene_plantilla(api, orgs):
    por_clave = _por_clave(_catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"])))
    assert por_clave["capital.coste_capital_anual"]["plantilla"] is None


@pytest.mark.parametrize("clave_propia,clave_ajena,dimension,instancia", [
    ("perfiles.flip_integral.m_objetivo", "perfiles.flip_ligero.m_objetivo",
     "perfil", "flip_integral"),
    ("adjudicacion.ratios.judicial_boe", "adjudicacion.ratios.aeat",
     "fuente", "judicial_boe"),
])
def test_coincide_con_analisis_por_perfil_y_fuente(api, orgs, clave_propia, clave_ajena,
                                                   dimension, instancia):
    por_clave = _por_clave(_catalogo(api, orgs["a_h"], _analisis(api, orgs["a_h"])))
    propia = por_clave[clave_propia]["plantilla"]
    assert propia["dimension"] == dimension
    assert propia["instancia"] == instancia
    assert propia["coincide_con_analisis"] is True
    assert "{" in propia["patron"]
    assert por_clave[clave_ajena]["plantilla"]["coincide_con_analisis"] is False


def test_coincide_con_analisis_por_banda_del_resultado_original(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    db = SessionLocal()
    try:
        banda = db.get(models.Analisis, aid).resultado["riesgos"]["banda"]
    finally:
        db.close()

    cat = _catalogo(api, h, aid)
    de_banda = [e["plantilla"] for e in cat["editables"]
                if e["plantilla"] and e["plantilla"]["dimension"] == "banda"]
    assert de_banda
    for p in de_banda:
        assert p["coincide_con_analisis"] is (p["instancia"] == banda)


def test_coincidencia_desconocida_es_null_y_no_se_deduce(api, orgs):
    """Si el dato de la dimensión no está en el análisis, no se inventa."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    db = SessionLocal()
    try:
        a = db.get(models.Analisis, aid)
        resultado = json.loads(json.dumps(a.resultado))
        del resultado["riesgos"]["banda"]
        a.resultado = resultado
        db.commit()
    finally:
        db.close()

    cat = _catalogo(api, h, aid)
    for e in cat["editables"]:
        if e["plantilla"] and e["plantilla"]["dimension"] == "banda":
            assert e["plantilla"]["coincide_con_analisis"] is None


# ─────────────────────────── E. Sin efectos ───────────────────────────

def test_no_ejecuta_el_motor_ni_escribe_ni_audita(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    simulaciones, auditorias = _contar(models.Simulacion), _contar(models.Auditoria)

    with patch("app.engine.pipeline.ejecutar_analisis") as motor, \
         patch("app.services.simulacion_service.ejecutar_analisis") as motor_sim:
        _catalogo(api, h, aid)

    assert motor.call_count == 0 and motor_sim.call_count == 0
    assert _contar(models.Simulacion) == simulaciones
    assert _contar(models.Auditoria) == auditorias


# ─────────────────────────── F. Seguridad ───────────────────────────

def test_sin_token_401(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    assert api.get(_url(aid)).status_code == 401


def test_lector_puede_leer(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    assert api.get(_url(aid), headers=orgs["lector_h"]).status_code == 200


def test_analisis_de_otra_organizacion_404(api, orgs):
    aid_b = _analisis(api, orgs["b_h"])
    assert api.get(_url(aid_b), headers=orgs["a_h"]).status_code == 404


def test_analisis_inexistente_404(api, orgs):
    assert api.get(_url("no-existe"), headers=orgs["a_h"]).status_code == 404

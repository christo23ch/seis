"""Fase 5F.7.3 — comparación original / simulación.

`GET /analisis/{id}/simulaciones/{sid}/comparacion` compara la configuración
original del análisis con una simulación, en parámetros y en resultado clave.
Toda la comparación la hace el backend; solo lectura: no ejecuta el motor, no
escribe y no audita.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app import models
from app.core.db import SessionLocal
from tests.conftest import entrada_base, token_headers

N_EDITABLES = 103
CAMPOS_RESULTADO = {"semaforo", "ico", "ra", "ici", "icu", "p_ideal", "p_objetivo", "p_max",
                    "p_limite", "rvc", "p_adj_esperado", "margen_seguridad_valor"}
_RUTA_RESULTADO = {c: ("decision", c) for c in CAMPOS_RESULTADO}
_RUTA_RESULTADO.update({c: ("decision", "precios", c)
                        for c in ("p_ideal", "p_objetivo", "p_max", "p_limite")})


@pytest.fixture(scope="module")
def orgs(api):
    from app.services import usuario_service

    db = SessionLocal()
    try:
        org_a = usuario_service.crear_organizacion(db, "Org Comparación A")
        usuario_service.crear_usuario(db, "cmp-a@example.com", "claveA123", "Cmp A",
                                      rol="analista", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        usuario_service.crear_usuario(db, "cmp-lector-a@example.com", "claveL123", "Lector A",
                                      rol="lector", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        org_b = usuario_service.crear_organizacion(db, "Org Comparación B")
        usuario_service.crear_usuario(db, "cmp-b@example.com", "claveB123", "Cmp B",
                                      rol="analista", organizacion_id=org_b.id,
                                      rol_org="miembro", es_superadmin=False)
    finally:
        db.close()
    return {"a_h": token_headers(api, "cmp-a@example.com", "claveA123"),
            "b_h": token_headers(api, "cmp-b@example.com", "claveB123"),
            "lector_h": token_headers(api, "cmp-lector-a@example.com", "claveL123")}


# ─────────────────────────── helpers ───────────────────────────

def _analisis(api, h) -> str:
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _crear(api, h, aid, overrides=None) -> dict:
    r = api.post(f"/api/v1/analisis/{aid}/simulaciones",
                 json={"overrides": overrides or {}}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _url(aid, sid) -> str:
    return f"/api/v1/analisis/{aid}/simulaciones/{sid}/comparacion"


def _comparar(api, h, aid, sid) -> dict:
    r = api.get(_url(aid, sid), headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _filas(cmp: dict) -> dict[str, dict]:
    return {f["clave"]: f for f in cmp["parametros"]}


def _dato(arbol, ruta):
    for p in ruta:
        if not isinstance(arbol, dict) or p not in arbol:
            return None
        arbol = arbol[p]
    return arbol


def _contar(modelo) -> int:
    db = SessionLocal()
    try:
        return db.query(modelo).count()
    finally:
        db.close()


def _editar_arbol(modelo, fila_id, campo, cambio):
    """Altera un JSON persistido del test (nunca el conocimiento global)."""
    db = SessionLocal()
    try:
        fila = db.get(modelo, fila_id)
        valor = json.loads(json.dumps(getattr(fila, campo)))
        setattr(fila, campo, cambio(valor))
        db.commit()
    finally:
        db.close()


_CAMPOS_FILA = {"clave", "nombre_legible", "unidad", "editable", "valor_original", "override",
                "tiene_override", "valor_aplicado", "modificado", "causa"}


# ─────────────────────────── A. Forma ───────────────────────────

def test_forma_de_la_respuesta(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)

    cmp = _comparar(api, h, aid, sim["id"])

    assert set(cmp) == {"analisis_id", "simulacion", "original", "parametros", "resultado"}
    assert cmp["analisis_id"] == aid
    assert set(cmp["simulacion"]) == {"id", "estado", "creado_en", "fecha_validacion",
                                      "version_parametros_base", "version_reglas",
                                      "es_configuracion_actual"}
    assert cmp["simulacion"]["id"] == sim["id"]
    assert set(cmp["original"]) == {"creado_en", "version_parametros", "version_reglas",
                                    "parametros_disponibles"}
    assert cmp["original"]["parametros_disponibles"] is True
    for f in cmp["parametros"]:
        assert set(f) == _CAMPOS_FILA
    assert set(cmp["resultado"]) == {"original", "simulacion"}
    assert set(cmp["resultado"]["original"]) == CAMPOS_RESULTADO
    assert set(cmp["resultado"]["simulacion"]) == CAMPOS_RESULTADO


def test_sin_cambios_las_103_editables_sin_modificar(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    cmp = _comparar(api, h, aid, _crear(api, h, aid)["id"])

    editables = [f for f in cmp["parametros"] if f["editable"]]
    assert len(editables) == N_EDITABLES
    assert len(cmp["parametros"]) == N_EDITABLES          # ninguna hoja (b) difiere
    for f in editables:
        assert f["nombre_legible"] and f["unidad"], f["clave"]
        assert f["modificado"] is False and f["causa"] is None, f["clave"]
        assert f["tiene_override"] is False and f["override"] is None, f["clave"]
        assert f["valor_aplicado"] == f["valor_original"], f["clave"]


# ─────────────────────────── B. Override ───────────────────────────

def test_override_numerico(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31})

    f = _filas(_comparar(api, h, aid, sim["id"]))["capital.coste_capital_anual"]

    assert f["editable"] is True
    assert f["tiene_override"] is True and f["override"] == 0.31
    assert f["valor_aplicado"] == 0.31
    assert f["valor_original"] != 0.31
    assert f["modificado"] is True and f["causa"] == "override"


def test_override_igual_al_original_no_es_modificacion(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    db = SessionLocal()
    try:
        original = db.get(models.Analisis, aid).parametros_aplicados["capital"]["coste_capital_anual"]
    finally:
        db.close()
    sim = _crear(api, h, aid, {"capital.coste_capital_anual": original})

    f = _filas(_comparar(api, h, aid, sim["id"]))["capital.coste_capital_anual"]

    assert f["tiene_override"] is True and f["override"] == original
    assert f["modificado"] is False and f["causa"] is None


def test_estructura_se_compara_completa_en_una_sola_fila(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid, {"adjudicacion.ratios.aeat": {"default": 0.6}})

    cmp = _comparar(api, h, aid, sim["id"])
    filas = _filas(cmp)
    f = filas["adjudicacion.ratios.aeat"]

    assert f["valor_aplicado"] == {"default": 0.6}
    assert f["override"] == {"default": 0.6}
    assert isinstance(f["valor_original"], dict)
    assert f["modificado"] is True and f["causa"] == "override"
    assert not [c for c in filas if c.startswith("adjudicacion.ratios.aeat.")]


# ─────────────────────────── C. Deriva y hojas no editables ───────────────────────────

def test_deriva_del_conocimiento_vigente(api, orgs):
    """Un parámetro GLOBAL cambia después de crear el análisis: una simulación
    sin overrides lo recoge, y la causa no es un override."""
    from app.services import conocimiento_service

    h = orgs["a_h"]
    aid = _analisis(api, h)
    db = SessionLocal()
    try:
        original = db.get(models.Analisis, aid).parametros_aplicados["capital"]["coste_capital_anual"]
        conocimiento_service.set_parametro(db, "capital.coste_capital_anual", original + 0.01,
                                           None, "test-deriva")
    finally:
        db.close()
    try:
        sim = _crear(api, h, aid)
        filas = _filas(_comparar(api, h, aid, sim["id"]))
    finally:
        db = SessionLocal()   # el conocimiento global se restaura para el resto del módulo
        try:
            db.query(models.Parametro).filter_by(clave="capital.coste_capital_anual").delete()
            db.commit()
        finally:
            db.close()

    f = filas["capital.coste_capital_anual"]
    assert f["tiene_override"] is False
    assert f["valor_original"] == original
    assert f["valor_aplicado"] == pytest.approx(original + 0.01)
    assert f["modificado"] is True and f["causa"] == "conocimiento_vigente"
    # La versión del árbol también es una hoja y también difiere (2026.07 → 2026.07+1ov):
    # por la regla (b) aparece como fila no editable, sin interpretarla.
    v = filas["version"]
    assert v["editable"] is False and v["causa"] == "conocimiento_vigente"


def test_hoja_no_editable_que_difiere_aparece_como_no_editable(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)

    def cambiar_itp(arbol):
        ccaa = sorted(arbol["fiscal"]["itp_por_ccaa"])[0]
        arbol["fiscal"]["itp_por_ccaa"][ccaa] = 0.99
        cambiar_itp.clave = f"fiscal.itp_por_ccaa.{ccaa}"
        return arbol
    _editar_arbol(models.Simulacion, sim["id"], "parametros_aplicados", cambiar_itp)

    cmp = _comparar(api, h, aid, sim["id"])
    f = _filas(cmp)[cambiar_itp.clave]

    assert f["editable"] is False
    assert f["nombre_legible"] is None and f["unidad"] is None
    assert f["valor_aplicado"] == 0.99
    assert f["tiene_override"] is False and f["override"] is None
    assert f["modificado"] is True and f["causa"] == "conocimiento_vigente"
    assert len(cmp["parametros"]) == N_EDITABLES + 1


def test_lista_entera_cuenta_como_una_hoja(api, orgs):
    """Una lista no catalogada que difiere sale como UNA fila, sin índices."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)
    db = SessionLocal()
    try:
        arbol = db.get(models.Simulacion, sim["id"]).parametros_aplicados
    finally:
        db.close()
    ruta = _primera_lista_no_catalogada(arbol, _claves_editables(api, h, aid))
    assert ruta is not None, "el árbol de defaults debería tener alguna lista fuera del catálogo"

    def alargar(a):
        nodo = a
        for p in ruta[:-1]:
            nodo = nodo[p]
        nodo[ruta[-1]] = nodo[ruta[-1]] + nodo[ruta[-1]][:1]
        return a
    _editar_arbol(models.Simulacion, sim["id"], "parametros_aplicados", alargar)

    filas = _filas(_comparar(api, h, aid, sim["id"]))
    clave = ".".join(ruta)
    assert filas[clave]["editable"] is False and filas[clave]["modificado"] is True
    assert isinstance(filas[clave]["valor_aplicado"], list)
    assert not [c for c in filas if c.startswith(clave + ".") or c.startswith(clave + "[")]


def _claves_editables(api, h, aid) -> set[str]:
    r = api.get(f"/api/v1/analisis/{aid}/parametros-simulables", headers=h)
    return {e["clave"] for e in r.json()["editables"]}


def _primera_lista_no_catalogada(arbol, editables, prefijo=()):
    for k in sorted(arbol):
        ruta = (*prefijo, k)
        clave = ".".join(ruta)
        if any(clave == e or clave.startswith(e + ".") for e in editables):
            continue
        v = arbol[k]
        if isinstance(v, list) and v:
            return ruta
        if isinstance(v, dict):
            encontrada = _primera_lista_no_catalogada(v, editables, ruta)
            if encontrada:
                return encontrada
    return None


# ─────────────────────────── D. Sin árbol original ───────────────────────────

def test_analisis_sin_parametros_aplicados_declara_la_carencia(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    _editar_arbol(models.Analisis, aid, "parametros_aplicados", lambda _: None)
    sim = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31})

    cmp = _comparar(api, h, aid, sim["id"])

    assert cmp["original"]["parametros_disponibles"] is False
    assert len(cmp["parametros"]) == N_EDITABLES             # sin árbol, no hay hojas (b)
    for f in cmp["parametros"]:
        assert f["valor_original"] is None, f["clave"]
        assert f["valor_aplicado"] is not None, f["clave"]   # nunca se rellena el original
        assert f["modificado"] is f["tiene_override"], f["clave"]
        assert f["causa"] == ("override" if f["tiene_override"] else None), f["clave"]
    assert _filas(cmp)["capital.coste_capital_anual"]["causa"] == "override"


# ─────────────────────────── E. Orden ───────────────────────────

def test_las_modificadas_van_primero_y_despues_por_clave(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31,
                               "semaforo.verde.ico_min": 90})

    parametros = _comparar(api, h, aid, sim["id"])["parametros"]
    orden = [(not f["modificado"], f["clave"]) for f in parametros]

    assert orden == sorted(orden)
    assert [f["clave"] for f in parametros[:2]] == ["capital.coste_capital_anual",
                                                     "semaforo.verde.ico_min"]


# ─────────────────────────── F. Resultado ───────────────────────────

def test_resultado_se_lee_de_lo_persistido(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31})
    db = SessionLocal()
    try:
        res_original = db.get(models.Analisis, aid).resultado
        res_simulacion = db.get(models.Simulacion, sim["id"]).resultado
    finally:
        db.close()

    resultado = _comparar(api, h, aid, sim["id"])["resultado"]

    for campo, ruta in _RUTA_RESULTADO.items():
        assert resultado["original"][campo] == _dato(res_original, ruta), campo
        assert resultado["simulacion"][campo] == _dato(res_simulacion, ruta), campo
    assert resultado["original"] != resultado["simulacion"]


def test_campo_ausente_en_el_resultado_es_null(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)

    def quitar_rvc(res):
        del res["decision"]["rvc"]
        return res
    _editar_arbol(models.Analisis, aid, "resultado", quitar_rvc)

    resultado = _comparar(api, h, aid, sim["id"])["resultado"]
    assert resultado["original"]["rvc"] is None
    assert resultado["simulacion"]["rvc"] is not None


# ─────────────────────────── G. Configuración actual ───────────────────────────

def test_es_configuracion_actual_coincide_con_el_listado(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    a = _crear(api, h, aid)
    b = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31})
    base = f"/api/v1/analisis/{aid}"

    def comprobar():
        listado = {s["id"]: s["es_configuracion_actual"]
                   for s in api.get(f"{base}/simulaciones", headers=h).json()}
        for sid in (a["id"], b["id"]):
            actual = _comparar(api, h, aid, sid)["simulacion"]["es_configuracion_actual"]
            assert actual is listado[sid], sid
        return listado

    assert not any(comprobar().values())
    api.post(f"{base}/simulaciones/{a['id']}/validar", headers=h)
    assert comprobar()[a["id"]] is True
    api.post(f"{base}/simulaciones/{b['id']}/validar", headers=h)
    assert comprobar()[b["id"]] is True
    api.post(f"{base}/simulaciones/{a['id']}/seleccionar", headers=h)
    assert comprobar()[a["id"]] is True
    api.post(f"{base}/configuracion/original", headers=h)
    assert not any(comprobar().values())


# ─────────────────────────── H. Sin efectos ───────────────────────────

def test_no_ejecuta_el_motor_ni_escribe_ni_audita(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31})
    simulaciones, auditorias = _contar(models.Simulacion), _contar(models.Auditoria)

    with patch("app.engine.pipeline.ejecutar_analisis") as motor, \
         patch("app.services.simulacion_service.ejecutar_analisis") as motor_sim:
        _comparar(api, h, aid, sim["id"])

    assert motor.call_count == 0 and motor_sim.call_count == 0
    assert _contar(models.Simulacion) == simulaciones
    assert _contar(models.Auditoria) == auditorias


# ─────────────────────────── I. Seguridad ───────────────────────────

def test_sin_token_401(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    sim = _crear(api, orgs["a_h"], aid)
    assert api.get(_url(aid, sim["id"])).status_code == 401


def test_lector_puede_leer(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    sim = _crear(api, orgs["a_h"], aid)
    assert api.get(_url(aid, sim["id"]), headers=orgs["lector_h"]).status_code == 200


def test_analisis_de_otra_organizacion_404(api, orgs):
    aid_b = _analisis(api, orgs["b_h"])
    sim_b = _crear(api, orgs["b_h"], aid_b)
    assert api.get(_url(aid_b, sim_b["id"]), headers=orgs["a_h"]).status_code == 404


def test_simulacion_de_otro_analisis_404_igual_que_inexistente(api, orgs):
    """Ambos análisis son de la misma organización: bloquea el guardián de
    pertenencia, no el aislamiento organizativo."""
    h = orgs["a_h"]
    aid_1, aid_2 = _analisis(api, h), _analisis(api, h)
    sim_2 = _crear(api, h, aid_2)

    ajena = api.get(_url(aid_1, sim_2["id"]), headers=h)
    inexistente = api.get(_url(aid_1, "no-existe"), headers=h)

    assert ajena.status_code == inexistente.status_code == 404
    assert ajena.json() == inexistente.json() == {"detail": "Simulación no encontrada"}

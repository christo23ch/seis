"""Fase 5F.6 — API HTTP de simulaciones.

Cubre lo que aporta la superficie HTTP sobre `simulacion_service` (ya probado
en `test_simulacion.py` y `test_configuracion_validada.py`): aislamiento por
organización, IDOR entre análisis, traducción de errores, auditoría atómica de
las escrituras y procedencia de los informes oficiales emitidos después de
validar o seleccionar una simulación.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app import models
from app.core.db import SessionLocal
from tests.conftest import entrada_base, token_headers

# `capital.coste_capital_anual` y no `financiacion.dscr_minimo`: este último
# solo actúa en la rama rentista y `entrada_base` es un perfil de venta.
OVERRIDE_VALIDO = {"capital.coste_capital_anual": 0.31}


@pytest.fixture(scope="module")
def orgs(api):
    """Org A (analista + lector) y Org B (analista), con usuarios propios de este módulo."""
    from app.services import usuario_service

    db = SessionLocal()
    try:
        org_a = usuario_service.crear_organizacion(db, "Org Simulaciones A")
        usuario_service.crear_usuario(db, "sim-a@example.com", "claveA123", "Sim A",
                                      rol="analista", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        usuario_service.crear_usuario(db, "sim-lector-a@example.com", "claveL123", "Lector A",
                                      rol="lector", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        org_b = usuario_service.crear_organizacion(db, "Org Simulaciones B")
        usuario_service.crear_usuario(db, "sim-b@example.com", "claveB123", "Sim B",
                                      rol="analista", organizacion_id=org_b.id,
                                      rol_org="miembro", es_superadmin=False)
        id_usuario_a = usuario_service.obtener_por_email(db, "sim-a@example.com").id
    finally:
        db.close()
    return {"a_h": token_headers(api, "sim-a@example.com", "claveA123"),
            "b_h": token_headers(api, "sim-b@example.com", "claveB123"),
            "lector_h": token_headers(api, "sim-lector-a@example.com", "claveL123"),
            "id_usuario_a": id_usuario_a}


# ─────────────────────────── helpers ───────────────────────────

def _analisis(api, h) -> str:
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _url(aid: str, sid: str | None = None, accion: str | None = None) -> str:
    url = f"/api/v1/analisis/{aid}/simulaciones"
    if sid is not None:
        url += f"/{sid}"
    if accion is not None:
        url += f"/{accion}"
    return url


def _crear(api, h, aid, overrides=None) -> dict:
    body = {} if overrides is None else {"overrides": overrides}
    r = api.post(_url(aid), json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _accion(api, h, aid, sid, accion):
    return api.post(_url(aid, sid, accion), headers=h)


def _original(api, h, aid):
    return api.post(f"/api/v1/analisis/{aid}/configuracion/original", headers=h)


def _puntero(aid: str) -> str | None:
    db = SessionLocal()
    try:
        return db.get(models.Analisis, aid).simulacion_validada_id
    finally:
        db.close()


def _estado(sid: str) -> str:
    db = SessionLocal()
    try:
        return db.get(models.Simulacion, sid).estado
    finally:
        db.close()


def _contar(modelo, **filtros) -> int:
    db = SessionLocal()
    try:
        return db.query(modelo).filter_by(**filtros).count()
    finally:
        db.close()


_CAMPOS_DETALLE = {"id", "analisis_id", "estado", "overrides", "parametros_aplicados",
                   "resultado", "version_parametros_base", "version_reglas", "usuario",
                   "creado_en", "fecha_validacion"}
_CAMPOS_RESUMEN = {"id", "estado", "creado_en", "fecha_validacion", "usuario", "overrides",
                   "semaforo", "ico", "p_objetivo", "p_max", "es_configuracion_actual"}


# ─────────────────────────── A. Aislamiento por organización ───────────────────────────

def test_a_lista_sus_simulaciones(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    sim = _crear(api, orgs["a_h"], aid)
    r = api.get(_url(aid), headers=orgs["a_h"])
    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [sim["id"]]


def test_cross_org_todas_las_rutas_devuelven_404_sin_efectos(api, orgs):
    """A no ve ni opera sobre lo de B — y nunca 403, que confirmaría que existe."""
    aid_b = _analisis(api, orgs["b_h"])
    sim_b = _crear(api, orgs["b_h"], aid_b)
    a_h = orgs["a_h"]

    assert api.get(_url(aid_b), headers=a_h).status_code == 404
    assert api.post(_url(aid_b), json={}, headers=a_h).status_code == 404
    assert api.get(_url(aid_b, sim_b["id"]), headers=a_h).status_code == 404
    for accion in ("validar", "descartar", "seleccionar"):
        assert _accion(api, a_h, aid_b, sim_b["id"], accion).status_code == 404
    assert _original(api, a_h, aid_b).status_code == 404

    assert _contar(models.Simulacion, analisis_id=aid_b) == 1
    assert _estado(sim_b["id"]) == "pendiente"
    assert _puntero(aid_b) is None


def test_simulacion_de_b_bajo_analisis_de_a_da_404(api, orgs):
    aid_a = _analisis(api, orgs["a_h"])
    aid_b = _analisis(api, orgs["b_h"])
    sim_b = _crear(api, orgs["b_h"], aid_b)
    a_h = orgs["a_h"]

    assert api.get(_url(aid_a, sim_b["id"]), headers=a_h).status_code == 404
    for accion in ("validar", "descartar", "seleccionar"):
        assert _accion(api, a_h, aid_a, sim_b["id"], accion).status_code == 404
    assert _estado(sim_b["id"]) == "pendiente"
    assert _puntero(aid_a) is None and _puntero(aid_b) is None


# ─────────────────────────── B. IDOR entre análisis de la MISMA organización ───────────────────────────

def test_idor_entre_analisis_de_la_misma_organizacion(api, orgs):
    """Ambos análisis son de Org A: lo que bloquea aquí es el guardián de
    pertenencia, no el aislamiento organizativo."""
    h = orgs["a_h"]
    aid_1, aid_2 = _analisis(api, h), _analisis(api, h)
    sim_2 = _crear(api, h, aid_2)

    r = api.get(_url(aid_1, sim_2["id"]), headers=h)
    assert r.status_code == 404
    assert r.json()["detail"] == "Simulación no encontrada"
    for accion in ("validar", "descartar", "seleccionar"):
        r = _accion(api, h, aid_1, sim_2["id"], accion)
        assert r.status_code == 404
        assert r.json()["detail"] == "Simulación no encontrada"

    assert sim_2["id"] not in {s["id"] for s in api.get(_url(aid_1), headers=h).json()}
    assert _estado(sim_2["id"]) == "pendiente"
    assert _puntero(aid_1) is None and _puntero(aid_2) is None


def test_ajena_e_inexistente_son_indistinguibles(api, orgs):
    """No revelar mediante el código ni el mensaje si la simulación ajena existe."""
    h = orgs["a_h"]
    aid_1, aid_2 = _analisis(api, h), _analisis(api, h)
    sim_2 = _crear(api, h, aid_2)
    ajena = api.get(_url(aid_1, sim_2["id"]), headers=h)
    inexistente = api.get(_url(aid_1, "no-existe"), headers=h)
    assert ajena.status_code == inexistente.status_code == 404
    assert ajena.json() == inexistente.json()


def test_analisis_inexistente_da_404(api, orgs):
    h = orgs["a_h"]
    assert api.get(_url("no-existe"), headers=h).status_code == 404
    assert api.post(_url("no-existe"), json={}, headers=h).status_code == 404
    assert _original(api, h, "no-existe").status_code == 404


# ─────────────────────────── C. Creación ───────────────────────────

def test_crear_con_override_valido_201_y_detalle_completo(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    original = api.get(f"/api/v1/analisis/{aid}", headers=h).json()

    sim = _crear(api, h, aid, OVERRIDE_VALIDO)

    assert set(sim) == _CAMPOS_DETALLE
    assert sim["analisis_id"] == aid
    assert sim["estado"] == "pendiente"
    assert sim["overrides"] == OVERRIDE_VALIDO
    assert sim["parametros_aplicados"]["capital"]["coste_capital_anual"] == 0.31
    assert sim["fecha_validacion"] is None
    assert sim["resultado"]["informe_markdown"]
    assert sim["resultado"] != original["resultado"]


def test_crear_guarda_el_id_de_usuario_no_el_correo(api, orgs):
    sim = _crear(api, orgs["a_h"], _analisis(api, orgs["a_h"]))
    assert sim["usuario"] == orgs["id_usuario_a"]
    assert "@" not in sim["usuario"]


def test_crear_con_overrides_vacios_y_sin_body(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    assert _crear(api, h, aid, {})["overrides"] == {}
    r = api.post(_url(aid), headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["overrides"] == {}
    assert _contar(models.Simulacion, analisis_id=aid) == 2


@pytest.mark.parametrize("clave", [
    "no.existe.nunca",                        # clave desconocida
    "hardcode.m12.divisor_score_maximo",      # constante TIPO 2, no editable
    "perfiles.{perfil}.m_objetivo",           # patrón de plantilla sin resolver
])
def test_override_invalido_422_sin_crear_filas(api, orgs, clave):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    auditorias_antes = _contar(models.Auditoria)
    r = api.post(_url(aid), json={"overrides": {clave: 1}}, headers=h)
    assert r.status_code == 422, r.text
    assert clave in r.json()["detail"]
    assert _contar(models.Simulacion, analisis_id=aid) == 0
    assert _contar(models.Auditoria) == auditorias_antes
    assert _puntero(aid) is None


def test_body_mal_formado_422(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    r = api.post(_url(aid), json={"overrides": ["no", "es", "objeto"]}, headers=h)
    assert r.status_code == 422
    assert _contar(models.Simulacion, analisis_id=aid) == 0


# ─────────────── C.1 Forma de los valores de override (Fase 5F.7.1) ───────────────

@pytest.mark.parametrize("clave,valor", [
    ("semaforo.verde.ico_min", "abc"),
    ("semaforo.verde.ico_min", None),
    ("semaforo.verde.ico_min", [1, 2]),
    ("semaforo.verde.ico_min", {"x": 1}),
    ("semaforo.verde.ico_min", True),
    ("riesgos.bandas_ra", 5),
    ("riesgos.bandas_ra", [{"max": "x", "banda": "bajo"}]),
    ("adjudicacion.ratios.aeat", {}),
    ("adjudicacion.ratios.aeat", {"default": 0.5, "otra": 1}),
])
def test_valor_con_forma_invalida_422_sin_filas_ni_auditoria(api, orgs, clave, valor):
    """Antes de 5F.7.1 todos estos llegaban al motor y respondían 500."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    auditorias_antes = _contar(models.Auditoria)

    r = api.post(_url(aid), json={"overrides": {clave: valor}}, headers=h)

    assert r.status_code == 422, r.text
    assert clave in r.json()["detail"]
    assert _contar(models.Simulacion, analisis_id=aid) == 0
    assert _contar(models.Auditoria) == auditorias_antes


def test_nan_en_cuerpo_crudo_422(api, orgs):
    """El parser JSON de Python acepta el literal `NaN`; el valor no es finito."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    auditorias_antes = _contar(models.Auditoria)

    r = api.post(_url(aid), content='{"overrides":{"capital.coste_capital_anual":NaN}}',
                 headers={**h, "Content-Type": "application/json"})

    assert r.status_code == 422, r.text
    assert _contar(models.Simulacion, analisis_id=aid) == 0
    assert _contar(models.Auditoria) == auditorias_antes


def test_campo_desconocido_en_el_cuerpo_422(api, orgs):
    """`override` (singular) no es `overrides`: antes se ignoraba y se creaba
    una simulación con `{}` sin avisar."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    r = api.post(_url(aid), json={"override": {"capital.coste_capital_anual": 0.03}},
                 headers=h)
    assert r.status_code == 422, r.text
    assert _contar(models.Simulacion, analisis_id=aid) == 0


@pytest.mark.parametrize("overrides", [
    {"capital.coste_capital_anual": 1},                # int donde la referencia es float
    {"adjudicacion.ratios.aeat": {"default": 0.6}},    # estructura con su forma exacta
])
def test_valor_con_forma_valida_201(api, orgs, overrides):
    sim = _crear(api, orgs["a_h"], _analisis(api, orgs["a_h"]), overrides)
    assert sim["overrides"] == overrides
    assert sim["estado"] == "pendiente"


def test_crear_no_modifica_el_analisis_original(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    db = SessionLocal()
    try:
        a = db.get(models.Analisis, aid)
        entrada, resultado = dict(a.entrada), dict(a.resultado)
        parametros = dict(a.parametros_aplicados)
    finally:
        db.close()

    _crear(api, h, aid, OVERRIDE_VALIDO)

    db = SessionLocal()
    try:
        a = db.get(models.Analisis, aid)
        assert a.entrada == entrada
        assert a.resultado == resultado
        assert a.parametros_aplicados == parametros
        assert a.simulacion_validada_id is None
    finally:
        db.close()


# ─────────────────────────── D. Listado y detalle ───────────────────────────

def test_listado_resumen_sin_resultado_completo_y_mas_reciente_primero(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    s1 = _crear(api, h, aid)
    s2 = _crear(api, h, aid, OVERRIDE_VALIDO)
    _accion(api, h, aid, s1["id"], "validar")

    listado = api.get(_url(aid), headers=h).json()

    assert [s["id"] for s in listado] == [s2["id"], s1["id"]]
    for fila in listado:
        assert set(fila) == _CAMPOS_RESUMEN
    por_id = {s["id"]: s for s in listado}
    assert por_id[s1["id"]]["es_configuracion_actual"] is True
    assert por_id[s2["id"]]["es_configuracion_actual"] is False
    decision = s2["resultado"]["decision"]
    assert por_id[s2["id"]]["semaforo"] == decision["semaforo"]
    assert por_id[s2["id"]]["ico"] == decision["ico"]
    assert por_id[s2["id"]]["p_objetivo"] == decision["precios"]["p_objetivo"]
    assert por_id[s2["id"]]["p_max"] == decision["precios"]["p_max"]


def test_listado_vacio(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    r = api.get(_url(aid), headers=orgs["a_h"])
    assert r.status_code == 200 and r.json() == []


def test_detalle_devuelve_el_snapshot_persistido_sin_ejecutar_el_motor(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    creada = _crear(api, h, aid, OVERRIDE_VALIDO)

    with patch("app.services.simulacion_service.ejecutar_analisis") as motor, \
         patch("app.services.simulacion_service.conocimiento_service.cargar_conocimiento") as ck:
        r = api.get(_url(aid, creada["id"]), headers=h)
        listado = api.get(_url(aid), headers=h)

    assert r.status_code == 200 and listado.status_code == 200
    assert motor.call_count == 0 and ck.call_count == 0
    assert r.json() == creada


def test_get_no_genera_auditoria(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)
    antes = _contar(models.Auditoria)
    api.get(_url(aid), headers=h)
    api.get(_url(aid, sim["id"]), headers=h)
    assert _contar(models.Auditoria) == antes


# ─────────────────────────── E. Estados ───────────────────────────

def test_pendiente_a_validada(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)
    r = _accion(api, h, aid, sim["id"], "validar")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert set(cuerpo) == _CAMPOS_DETALLE
    assert cuerpo["estado"] == "validada"
    assert cuerpo["fecha_validacion"] is not None
    assert cuerpo["resultado"] == sim["resultado"]
    assert _puntero(aid) == sim["id"]


def test_pendiente_a_descartada_no_toca_el_puntero(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    actual = _crear(api, h, aid)
    _accion(api, h, aid, actual["id"], "validar")
    otra = _crear(api, h, aid, OVERRIDE_VALIDO)

    r = _accion(api, h, aid, otra["id"], "descartar")

    assert r.status_code == 200, r.text
    assert set(r.json()) == _CAMPOS_DETALLE
    assert r.json()["estado"] == "descartada"
    assert r.json()["resultado"] == otra["resultado"]
    assert _puntero(aid) == actual["id"]


@pytest.mark.parametrize("estado_previo,accion", [
    ("validar", "validar"), ("validar", "descartar"),
    ("descartar", "validar"), ("descartar", "descartar"),
])
def test_estados_terminales_dan_409(api, orgs, estado_previo, accion):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)
    assert _accion(api, h, aid, sim["id"], estado_previo).status_code == 200
    puntero_antes = _puntero(aid)
    estado_antes = _estado(sim["id"])

    r = _accion(api, h, aid, sim["id"], accion)

    assert r.status_code == 409, r.text
    assert _estado(sim["id"]) == estado_antes
    assert _puntero(aid) == puntero_antes


def test_simulacion_inexistente_en_acciones_da_404(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    for accion in ("validar", "descartar", "seleccionar"):
        assert _accion(api, h, aid, "no-existe", accion).status_code == 404


# ─────────────────────────── F. Selección y puntero ───────────────────────────

def test_validar_una_segunda_mueve_el_puntero_y_la_primera_sigue_validada(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    a = _crear(api, h, aid)
    b = _crear(api, h, aid, OVERRIDE_VALIDO)

    _accion(api, h, aid, a["id"], "validar")
    assert _puntero(aid) == a["id"]
    _accion(api, h, aid, b["id"], "validar")
    assert _puntero(aid) == b["id"]
    assert _estado(a["id"]) == "validada" and _estado(b["id"]) == "validada"


def test_seleccionar_una_validada_mueve_el_puntero_sin_cambiar_estados(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    a = _crear(api, h, aid)
    b = _crear(api, h, aid, OVERRIDE_VALIDO)
    va = _accion(api, h, aid, a["id"], "validar").json()
    _accion(api, h, aid, b["id"], "validar")

    r = _accion(api, h, aid, a["id"], "seleccionar")

    assert r.status_code == 200, r.text
    assert r.json()["id"] == a["id"]
    assert r.json()["estado"] == "validada"
    assert r.json()["fecha_validacion"] == va["fecha_validacion"]
    assert _puntero(aid) == a["id"]
    assert _estado(b["id"]) == "validada"
    # GET /analisis/{id} (configuración actual) refleja la selección.
    detalle = api.get(f"/api/v1/analisis/{aid}", headers=h).json()
    assert detalle["simulacion_validada_id"] == a["id"]
    assert detalle["resultado"] == a["resultado"]


def test_seleccionar_la_ya_seleccionada_es_idempotente(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    a = _crear(api, h, aid)
    _accion(api, h, aid, a["id"], "validar")
    assert _accion(api, h, aid, a["id"], "seleccionar").status_code == 200
    assert _puntero(aid) == a["id"]


@pytest.mark.parametrize("preparar", [None, "descartar"])
def test_seleccionar_pendiente_o_descartada_da_409(api, orgs, preparar):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)
    if preparar:
        _accion(api, h, aid, sim["id"], preparar)
    estado_antes = _estado(sim["id"])

    r = _accion(api, h, aid, sim["id"], "seleccionar")

    assert r.status_code == 409, r.text
    assert _puntero(aid) is None
    assert _estado(sim["id"]) == estado_antes


def test_volver_a_original_limpia_el_puntero_sin_tocar_simulaciones(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    a = _crear(api, h, aid)
    b = _crear(api, h, aid, OVERRIDE_VALIDO)
    c = _crear(api, h, aid)
    _accion(api, h, aid, a["id"], "validar")
    _accion(api, h, aid, c["id"], "descartar")

    r = _original(api, h, aid)

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["id"] == aid
    assert cuerpo["simulacion_validada_id"] is None
    assert _puntero(aid) is None
    assert (_estado(a["id"]), _estado(b["id"]), _estado(c["id"])) == (
        "validada", "pendiente", "descartada")
    assert _contar(models.Simulacion, analisis_id=aid) == 3
    # La configuración actual vuelve a ser el resultado original.
    db = SessionLocal()
    try:
        assert cuerpo["resultado"] == db.get(models.Analisis, aid).resultado
    finally:
        db.close()


def test_volver_a_original_es_idempotente(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    assert _original(api, h, aid).status_code == 200
    assert _original(api, h, aid).status_code == 200
    assert _puntero(aid) is None


def test_original_no_esta_bajo_simulaciones(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    assert api.post(f"{_url(aid)}/original", headers=h).status_code in (404, 405)


# ─────────────────────────── G. Informes: procedencia ───────────────────────────

def test_informes_toman_la_procedencia_de_la_simulacion_seleccionada(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    a = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31})
    b = _crear(api, h, aid, {"capital.coste_capital_anual": 0.62})

    _accion(api, h, aid, a["id"], "validar")
    i_a = api.post(f"/api/v1/analisis/{aid}/informes", headers=h)
    assert i_a.status_code == 201, i_a.text
    i_a = i_a.json()
    assert i_a["simulacion_id"] == a["id"]
    assert i_a["resultado"] == a["resultado"]

    # B se valida y luego se vuelve a A y otra vez a B por `seleccionar`.
    _accion(api, h, aid, b["id"], "validar")
    _accion(api, h, aid, a["id"], "seleccionar")
    assert _accion(api, h, aid, b["id"], "seleccionar").status_code == 200
    i_b = api.post(f"/api/v1/analisis/{aid}/informes", headers=h).json()
    assert i_b["simulacion_id"] == b["id"]
    assert i_b["resultado"] == b["resultado"]

    _original(api, h, aid)
    i_o = api.post(f"/api/v1/analisis/{aid}/informes", headers=h).json()
    assert i_o["simulacion_id"] is None

    releido = api.get(f"/api/v1/analisis/{aid}/informes/{i_a['id']}", headers=h).json()
    assert releido["simulacion_id"] == a["id"]
    assert releido["resultado"] == i_a["resultado"]


# ─────────────────────────── H. Auditoría ───────────────────────────

def _auditorias(entidad, entidad_id, accion) -> list[models.Auditoria]:
    db = SessionLocal()
    try:
        return (db.query(models.Auditoria)
                .filter_by(entidad=entidad, entidad_id=entidad_id, accion=accion).all())
    finally:
        db.close()


def test_cada_escritura_deja_una_auditoria_exacta(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    quien = "sim-a@example.com"

    a = _crear(api, h, aid, {"capital.coste_capital_anual": 0.31,
                             "semaforo.verde.ico_min": 80})
    (fila,) = _auditorias("simulacion", a["id"], "crear")
    assert fila.quien == quien
    assert fila.delta == {"analisis_id": aid, "n_overrides": 2}

    _accion(api, h, aid, a["id"], "validar")
    (fila,) = _auditorias("simulacion", a["id"], "validar")
    assert fila.quien == quien and fila.delta == {"analisis_id": aid}

    d = _crear(api, h, aid)
    _accion(api, h, aid, d["id"], "descartar")
    (fila,) = _auditorias("simulacion", d["id"], "descartar")
    assert fila.quien == quien and fila.delta == {"analisis_id": aid}

    _accion(api, h, aid, a["id"], "seleccionar")
    (fila,) = _auditorias("analisis", aid, "seleccionar_configuracion")
    assert fila.quien == quien and fila.delta == {"simulacion_id": a["id"]}

    _original(api, h, aid)
    (fila,) = _auditorias("analisis", aid, "volver_configuracion_original")
    assert fila.quien == quien and fila.delta == {}


def test_delta_no_contiene_valores_de_overrides(api, orgs):
    """Los valores los escribe el usuario: no deben llegar nunca a `delta`."""
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid, OVERRIDE_VALIDO)
    (fila,) = _auditorias("simulacion", sim["id"], "crear")
    assert "0.31" not in json.dumps(fila.delta)
    assert "capital" not in json.dumps(fila.delta)


def test_operacion_rechazada_no_audita(api, orgs):
    h = orgs["a_h"]
    aid = _analisis(api, h)
    sim = _crear(api, h, aid)
    _accion(api, h, aid, sim["id"], "descartar")
    antes = _contar(models.Auditoria)
    assert _accion(api, h, aid, sim["id"], "validar").status_code == 409
    assert api.post(_url(aid), json={"overrides": {"no.existe": 1}},
                    headers=h).status_code == 422
    assert _contar(models.Auditoria) == antes


_FALLO = "app.services.simulacion_service.auditoria_service.auditar"
_OPERACIONES = ("crear", "validar", "descartar", "seleccionar", "original")


def _escenario(api, h) -> dict:
    """Análisis con A validada, B validada y seleccionada, y P pendiente: cada
    una de las cinco escrituras tiene aquí algo legítimo que cambiar."""
    aid = _analisis(api, h)
    a, b, p = _crear(api, h, aid), _crear(api, h, aid), _crear(api, h, aid)
    _accion(api, h, aid, a["id"], "validar")
    _accion(api, h, aid, b["id"], "validar")
    return {"aid": aid, "a": a["id"], "b": b["id"], "p": p["id"]}


def _foto(aid: str) -> dict:
    """Estado PERSISTIDO relevante, leído con una sesión nueva."""
    db = SessionLocal()
    try:
        sims = db.query(models.Simulacion).filter_by(analisis_id=aid).all()
        return {"puntero": db.get(models.Analisis, aid).simulacion_validada_id,
                "simulaciones": {s.id: (s.estado, s.fecha_validacion) for s in sims},
                "auditorias": db.query(models.Auditoria).count()}
    finally:
        db.close()


def _peticion(esc: dict, operacion: str) -> str:
    aid = esc["aid"]
    return {"crear": _url(aid),
            "validar": _url(aid, esc["p"], "validar"),
            "descartar": _url(aid, esc["p"], "descartar"),
            "seleccionar": _url(aid, esc["a"], "seleccionar"),
            "original": f"/api/v1/analisis/{aid}/configuracion/original"}[operacion]


@pytest.mark.parametrize("operacion", _OPERACIONES)
def test_fallo_de_auditoria_via_http_no_persiste_nada(api, orgs, operacion):
    """La petición falla y la BD queda EXACTAMENTE como estaba: ni la
    modificación de negocio, ni la fila de auditoría, ni el puntero."""
    h = orgs["a_h"]
    esc = _escenario(api, h)
    antes = _foto(esc["aid"])
    assert antes["puntero"] == esc["b"]

    with patch(_FALLO, side_effect=RuntimeError("fallo de auditoría simulado")):
        with pytest.raises(RuntimeError):   # TestClient propaga la excepción del servidor
            api.post(_peticion(esc, operacion), json={}, headers=h)

    assert _foto(esc["aid"]) == antes


@pytest.mark.parametrize("operacion", _OPERACIONES)
def test_fallo_de_auditoria_hace_rollback_aunque_el_llamador_confirme_despues(
        api, orgs, operacion):
    """Defecto B-1 (Fase 5F.3.1). Por HTTP, la sesión se cierra y descarta lo
    no confirmado de todos modos, así que el test anterior no distingue un
    `rollback` real de su ausencia. Aquí el llamador reutiliza la MISMA sesión
    y hace `commit` después del fallo: sin el `rollback` del servicio, la
    simulación ya volcada por `flush` o los cambios de estado pendientes se
    confirmarían sin su evento de auditoría."""
    from app.services import simulacion_service as ss

    esc = _escenario(api, orgs["a_h"])
    aid = esc["aid"]
    antes = _foto(aid)
    llamadas = {
        "crear": lambda db: ss.crear_simulacion(db, aid, {}, quien="x"),
        "validar": lambda db: ss.validar_simulacion(db, aid, esc["p"], quien="x"),
        "descartar": lambda db: ss.descartar_simulacion(db, aid, esc["p"], quien="x"),
        "seleccionar": lambda db: ss.seleccionar_simulacion_validada(db, aid, esc["a"],
                                                                     quien="x"),
        "original": lambda db: ss.volver_a_configuracion_original(db, aid, quien="x"),
    }

    db = SessionLocal()
    try:
        with patch(_FALLO, side_effect=RuntimeError("fallo de auditoría simulado")):
            with pytest.raises(RuntimeError):
                llamadas[operacion](db)
        db.commit()   # el llamador confirma su sesión por otro motivo
    finally:
        db.close()

    assert _foto(aid) == antes


# ─────────────────────────── I. Autenticación y roles ───────────────────────────

def _todas_las_rutas(aid, sid):
    return [("post", _url(aid)), ("get", _url(aid)), ("get", _url(aid, sid)),
            ("post", _url(aid, sid, "validar")), ("post", _url(aid, sid, "descartar")),
            ("post", _url(aid, sid, "seleccionar")),
            ("post", f"/api/v1/analisis/{aid}/configuracion/original")]


def test_sin_autenticacion_401_en_las_siete_rutas(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    sim = _crear(api, orgs["a_h"], aid)
    for metodo, url in _todas_las_rutas(aid, sim["id"]):
        assert getattr(api, metodo)(url).status_code == 401, (metodo, url)


def test_lector_403_en_escrituras_y_200_en_lecturas(api, orgs):
    aid = _analisis(api, orgs["a_h"])
    sim = _crear(api, orgs["a_h"], aid)
    lector = orgs["lector_h"]
    for metodo, url in _todas_las_rutas(aid, sim["id"]):
        esperado = 403 if metodo == "post" else 200
        assert getattr(api, metodo)(url, headers=lector).status_code == esperado, (metodo, url)
    assert _estado(sim["id"]) == "pendiente"
    assert _puntero(aid) is None

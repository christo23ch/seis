"""Fase 5J-1 — datos del procedimiento a través de la API (ADR-0022).

`/opciones` ofrece al formulario las preguntas del procedimiento; el alta las acepta,
las persiste (migración 0016) y devuelve el resultado informativo. Un cuerpo anterior
a la fase, sin estos campos, sigue funcionando.
"""
from __future__ import annotations

import copy

from app import models
from app.core.db import SessionLocal
from tests.test_formulario_alta_5i import CUERPO_MINIMO


def _cuerpo(subasta: dict | None = None, activo: dict | None = None) -> dict:
    c = copy.deepcopy(CUERPO_MINIMO)
    c["subasta"].update(subasta or {})
    c["activo"].update(activo or {})
    return c


def test_opciones_ofrece_las_preguntas_del_procedimiento(api, headers):
    d = api.get("/api/v1/opciones", headers=headers).json()
    assert list(d["procedimientos"]) == ["judicial", "aeat", "tgss", "notarial", "extrajudicial",
                                         "concursal", "no_aplica"]
    assert d["procedimiento_por_fuente"]["judicial_boe"] == "judicial"
    assert d["procedimiento_por_fuente"]["banco"] == "no_aplica"
    # Toda fuente que ofrece el formulario tiene procedimiento preseleccionable… salvo
    # la genérica `default` de los ratios, que no es una fuente real.
    assert set(d["fuentes"]) - {"default"} <= set(d["procedimiento_por_fuente"])
    assert d["fecha_lo_1_2025"] == "2025-04-03"


def test_el_alta_persiste_lo_declarado_y_devuelve_el_resultado(api, headers):
    cuerpo = _cuerpo({"procedimiento": "judicial", "regimen_judicial": "anterior",
                      "cantidad_reclamada": 30000, "identificador_externo": "SUB-5J1-PERSISTE"},
                     {"vivienda_habitual_ejecutado": "no"})
    r = api.post("/api/v1/analisis", json=cuerpo, headers=headers)
    assert r.status_code == 200, r.text
    proc = r.json()["resultado"]["procedimiento"]
    assert proc["regimen"] == "judicial_lec_2015" and proc["deposito_eur"] == 7600.0
    assert proc["puja_minima_aprobable"] == 30000.0

    db = SessionLocal()
    try:
        subasta = db.query(models.Subasta).filter_by(identificador_externo="SUB-5J1-PERSISTE").one()
        assert (subasta.procedimiento, subasta.regimen_judicial) == ("judicial", "anterior")
        assert float(subasta.cantidad_reclamada) == 30000.0
        assert subasta.activos[0].vivienda_habitual_ejecutado == "no"
    finally:
        db.close()


def test_un_cuerpo_anterior_a_la_fase_sigue_valiendo_y_no_inventa_respuestas(api, headers):
    cuerpo = _cuerpo({"identificador_externo": "SUB-5J1-ANTIGUO"})
    r = api.post("/api/v1/analisis", json=cuerpo, headers=headers)
    assert r.status_code == 200, r.text
    proc = r.json()["resultado"]["procedimiento"]
    assert proc["procedimiento_deducido"] and proc["regimen_asumido"] and proc["vivienda_habitual_asumida"]

    db = SessionLocal()
    try:
        subasta = db.query(models.Subasta).filter_by(identificador_externo="SUB-5J1-ANTIGUO").one()
        # Lo no preguntado no se guarda como respondido: el supuesto vive en el resultado.
        assert subasta.procedimiento is None and subasta.cantidad_reclamada is None
        assert subasta.regimen_judicial == "no_se"            # el valor por defecto del contrato
        assert subasta.activos[0].vivienda_habitual_ejecutado is None
    finally:
        db.close()


def test_simular_devuelve_el_procedimiento(api, headers):
    r = api.post("/api/v1/analisis/simular", json=_cuerpo({"procedimiento": "aeat"}), headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["procedimiento"]["deposito_eur"] == 7600.0


def test_valores_no_admitidos_son_422(api, headers):
    for cuerpo, campo in ((_cuerpo({"procedimiento": "subastilla"}), "procedimiento"),
                          (_cuerpo({"regimen_judicial": "tal_vez"}), "regimen_judicial"),
                          (_cuerpo({"cantidad_reclamada": -5}), "cantidad_reclamada"),
                          (_cuerpo(activo={"vivienda_habitual_ejecutado": "quizas"}), "vivienda_habitual_ejecutado")):
        r = api.post("/api/v1/analisis/simular", json=cuerpo, headers=headers)
        assert r.status_code == 422, campo
        assert any(e["loc"][-1] == campo for e in r.json()["detail"]), r.json()

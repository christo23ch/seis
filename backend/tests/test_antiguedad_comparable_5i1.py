"""Fase 5I.1-A — la antigüedad de un comparable no puede ser negativa.

Antes, el contrato aceptaba `meses_antiguedad < 0` y M03 ponderaba con
1/(1 + meses/6): con −3 meses el comparable pesaba el doble que uno de hoy y con −6
la API respondía 500 (división por cero). Ahora es un error del cliente: 422 con el
`loc` del campo, antes de llegar al motor.
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.engine.contracts import ComparableInput
from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base
from tests.test_golden_caso19 import entrada_caso_19

NO_FINITOS = [pytest.param(float("inf"), id="inf"), pytest.param(float("-inf"), id="-inf"),
              pytest.param(float("nan"), id="nan")]


def _cuerpo_con_antiguedad(meses: float) -> dict[str, Any]:
    cuerpo = json.loads(entrada_base().model_dump_json())
    assert cuerpo["comparables"], "la entrada base debe traer al menos un comparable"
    cuerpo["comparables"][0]["meses_antiguedad"] = meses
    return cuerpo


@pytest.mark.parametrize("meses", [-1.0, -6.0, -0.5, -1e-9])
@pytest.mark.parametrize("ruta", ["/api/v1/analisis/simular", "/api/v1/analisis"])
def test_una_antiguedad_negativa_es_422_con_el_loc_del_campo(api, headers, ruta, meses):
    r = api.post(ruta, json=_cuerpo_con_antiguedad(meses), headers=headers)
    assert r.status_code == 422, r.text
    locs = [e["loc"] for e in r.json()["detail"]]
    assert ["body", "comparables", 0, "meses_antiguedad"] in locs


@pytest.mark.parametrize("meses", NO_FINITOS)
def test_el_contrato_rechaza_una_antiguedad_no_finita(meses):
    """Con solo `ge=0`, `inf` pasaba (peso 0 en M03; todos los testigos con `inf` ⇒ suma de
    pesos 0); `-inf` y `nan` ya los rechazaba `ge`. Se prueba contra el contrato y no por
    HTTP: el JSON estricto no representa NaN ni Infinity (un navegador envía `null`), y con
    JSON no estándar la API responde 500 al serializar el 422
    cuando el campo falla la validación: deuda 27 de docs/ESTADO_ACTUAL.md)."""
    with pytest.raises(ValidationError) as exc:
        ComparableInput(precio_m2=2000, meses_antiguedad=meses)
    assert exc.value.errors()[0]["loc"] == ("meses_antiguedad",)
    assert exc.value.errors()[0]["type"] == "finite_number"      # lo rechaza `allow_inf_nan`, no `ge`


def test_antiguedad_cero_sigue_funcionando(api, headers):
    r = api.post("/api/v1/analisis/simular", json=_cuerpo_con_antiguedad(0), headers=headers)
    assert r.status_code == 200, r.text


def test_el_contrato_rechaza_la_negativa_y_admite_cero():
    with pytest.raises(ValidationError) as exc:
        ComparableInput(precio_m2=2000, meses_antiguedad=-6)
    assert exc.value.errors()[0]["loc"] == ("meses_antiguedad",)
    assert exc.value.errors()[0]["type"] == "greater_than_equal"
    assert ComparableInput(precio_m2=2000, meses_antiguedad=0).meses_antiguedad == 0.0


def test_el_caso_dorado_tiene_antiguedades_validas_y_se_analiza():
    """El §19 no usa antigüedades negativas: la restricción no le afecta (y la guarda
    `test_invariante_5h1` vigila que no cambie ni un valor)."""
    entrada = entrada_caso_19()
    assert all(c.meses_antiguedad >= 0 for c in entrada.comparables)
    assert ejecutar_analisis(entrada).decision.semaforo == "amarillo"

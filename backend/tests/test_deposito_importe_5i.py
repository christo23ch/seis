"""Fase 5I-C — depósito como importe: se guarda el importe escrito, el motor no cambia.

El formulario convierte el importe a `deposito_pct` (fracción del valor de subasta)
en un solo sitio (`frontend/lib/schema.ts`, `depositoFraccion`) y envía ADEMÁS el
importe original en `subasta.deposito_importe`, para que el análisis guardado
conserve lo que se escribió. Ese campo es informativo: ningún módulo lo lee.
"""
from __future__ import annotations

import json

import pytest

from app.engine.contracts import AnalisisInput
from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base
from tests.test_golden_caso19 import entrada_caso_19
from tests.test_invariante_5h1 import con_hipoteca


def _con_importe(entrada: AnalisisInput, importe: float | None) -> AnalisisInput:
    return entrada.model_copy(update={"subasta": entrada.subasta.model_copy(update={"deposito_importe": importe})})


@pytest.mark.parametrize("hipoteca", [False, True], ids=["caso19", "caso19_hipoteca"])
@pytest.mark.parametrize("factor", [1.0, 0.0001, 10.0], ids=["coherente", "minimo", "diez_veces"])
def test_el_importe_del_deposito_no_cambia_ningun_calculo(hipoteca: bool, factor: float):
    """Ni coherente con el % ni absurdo: el resultado COMPLETO (informe incluido) es idéntico."""
    entrada = con_hipoteca(entrada_caso_19()) if hipoteca else entrada_caso_19()
    importe = entrada.subasta.deposito_pct * entrada.subasta.valor_subasta * factor
    sin = ejecutar_analisis(entrada).model_dump(mode="json")
    con = ejecutar_analisis(_con_importe(entrada, importe)).model_dump(mode="json")
    assert con == sin


def test_ningun_modulo_del_motor_ni_servicio_lee_el_importe():
    """El comentario del contrato promete que nadie lo lee; esto lo vigila."""
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1] / "app"
    lectores = [str(f.relative_to(raiz)) for carpeta in ("engine", "services", "api")
                for f in (raiz / carpeta).rglob("*.py")
                if "deposito_importe" in f.read_text(encoding="utf-8") and f.name != "contracts.py"]
    assert lectores == []


def test_el_importe_se_conserva_en_la_entrada_guardada(api, headers):
    entrada = entrada_base()
    cuerpo = json.loads(entrada.model_dump_json())
    cuerpo["subasta"]["deposito_importe"] = 7600
    r = api.post("/api/v1/analisis", json=cuerpo, headers=headers)
    assert r.status_code == 200, r.text
    det = api.get(f"/api/v1/analisis/{r.json()['id']}", headers=headers).json()
    assert det["entrada"]["subasta"]["deposito_importe"] == 7600
    assert det["entrada"]["subasta"]["deposito_pct"] == entrada.subasta.deposito_pct


def test_sin_importe_el_campo_queda_vacio():
    assert AnalisisInput.model_validate(json.loads(entrada_base().model_dump_json())).subasta.deposito_importe is None


@pytest.mark.parametrize("importe", [0, -7600, "inf", "nan"])
def test_un_importe_no_positivo_o_no_finito_es_un_error_del_cliente(api, headers, importe):
    cuerpo = json.loads(entrada_base().model_dump_json())
    cuerpo["subasta"]["deposito_importe"] = importe
    r = api.post("/api/v1/analisis/simular", json=cuerpo, headers=headers)
    assert r.status_code == 422
    assert any(e["loc"][-2:] == ["subasta", "deposito_importe"] for e in r.json()["detail"])

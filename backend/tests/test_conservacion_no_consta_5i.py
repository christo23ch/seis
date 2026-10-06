"""Fase 5I-D — estado de conservación «No consta» (ADR-0020).

Criterio: ante un estado desconocido el motor asume el nivel que fija el parámetro
T3 `conservacion.desconocido_usa` («malo» de fábrica: prudencia P5, mismo patrón
que `ocupacion.desconocida.usa`). No cambia ningún peso ni fórmula: el resultado
es el del estado asumido, más un aviso en el informe y un ítem de verificación en
el checklist.
"""
from __future__ import annotations

import json
import re

import pytest
from pydantic import ValidationError

from app.engine.conservacion import EstadoAsumidoInvalidoError, estado_efectivo
from app.engine.contracts import AnalisisInput
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base
from tests.test_golden_caso19 import entrada_caso_19

ITEM = "Estado de conservación verificado con visita interior o fotos interiores"


def _con_estado(entrada: AnalisisInput, estado: str) -> AnalisisInput:
    return entrada.model_copy(update={"activo": entrada.activo.model_copy(update={"estado_conservacion": estado})})


def _sin(d: dict, *claves: str) -> dict:
    return {k: v for k, v in d.items() if k not in claves}


def test_no_consta_calcula_exactamente_como_el_estado_asumido():
    """Mismo resultado numérico que «malo» (caso §19): solo cambian el informe y el checklist."""
    malo = ejecutar_analisis(entrada_caso_19()).model_dump(mode="json")
    nc = ejecutar_analisis(_con_estado(entrada_caso_19(), "desconocido")).model_dump(mode="json")
    assert _sin(nc, "informe_markdown", "checklist") == _sin(malo, "informe_markdown", "checklist")
    assert nc["reforma"]["nivel"] == malo["reforma"]["nivel"]
    assert nc["valoracion"]["vm"] == malo["valoracion"]["vm"]


def test_no_consta_no_cambia_el_ici_ni_el_semaforo():
    """El ICI ya penaliza la falta de fotos interiores o visita; no se toca su fórmula."""
    malo = ejecutar_analisis(entrada_caso_19())
    nc = ejecutar_analisis(_con_estado(entrada_caso_19(), "desconocido"))
    assert nc.decision.ici == malo.decision.ici
    assert nc.decision.semaforo == malo.decision.semaforo
    assert nc.decision.ico == malo.decision.ico


def test_el_informe_avisa_de_que_el_estado_no_consta():
    md = ejecutar_analisis(_con_estado(entrada_caso_19(), "desconocido")).informe_markdown
    assert "estado de conservación **no consta**" in md
    assert "se asume «malo» (P5)" in md


def test_el_checklist_pide_verificarlo_y_sigue_pendiente_mientras_no_conste():
    """Con fotos o visita el ítem NO se da por hecho: el estado sigue sin declarar, y el
    informe sigue diciendo «no consta». Lo que cambia es la indicación: elija el real."""
    entrada = _con_estado(entrada_caso_19(), "desconocido")
    res = ejecutar_analisis(entrada)
    item = next(c for c in res.checklist if c.texto == ITEM)
    assert item.estado == "pendiente" and item.bloqueante is False
    # Al final: no desplaza la numeración del checklist de la especificación (§13).
    assert res.checklist[-1].texto == ITEM
    con_fotos = entrada.model_copy(update={"documentos": entrada.documentos.model_copy(
        update={"fotos_interior_o_visita": True})})
    item = next(c for c in ejecutar_analisis(con_fotos).checklist if c.texto == ITEM)
    assert item.estado == "pendiente" and "elija el estado real" in item.detalle


def test_con_estado_conocido_no_hay_item_ni_aviso():
    res = ejecutar_analisis(entrada_caso_19())
    assert all(c.texto != ITEM for c in res.checklist)
    assert re.search(r"m² en .*?, estado malo\.", res.informe_markdown)
    assert "estado de conservación **no consta**" not in res.informe_markdown


def test_un_perfil_con_nivel_propio_manda_sobre_el_estado_asumido():
    """flip_ligero fija su nivel de reforma: «No consta» no lo cambia (como con un estado conocido)."""
    entrada = _con_estado(entrada_caso_19(), "desconocido").model_copy(update={"perfil": "flip_ligero"})
    assert ejecutar_analisis(entrada).reforma.nivel == "ligera"


@pytest.mark.parametrize("valor", ["desconocido", "pesimo", 3, None])
def test_un_estado_asumido_invalido_falla_con_los_valores_validos(valor):
    params = cargar_defaults().con_overrides({"conservacion.desconocido_usa": valor})
    with pytest.raises(EstadoAsumidoInvalidoError, match="reformado, bueno, regular, malo, ruina"):
        estado_efectivo("desconocido", params)
    assert estado_efectivo("bueno", params) == "bueno"      # con estado conocido no se consulta


@pytest.mark.parametrize("valor", ["desconocido", "pesimo", 3])
def test_no_se_puede_guardar_un_estado_asumido_invalido(api, headers, valor):
    r = api.put("/api/v1/parametros", headers=headers,
                json={"clave": "conservacion.desconocido_usa", "valor": valor, "fuente_legal": "test 5I-D"})
    assert r.status_code == 400
    assert "reformado, bueno, regular, malo, ruina" in r.json()["detail"]
    assert api.get("/api/v1/opciones", headers=headers).json()["valores_defecto"][
        "estado_conservacion_desconocido"] == "malo"


def test_si_se_puede_guardar_un_estado_asumido_valido(api, headers):
    def poner(valor: str) -> None:
        r = api.put("/api/v1/parametros", headers=headers,
                    json={"clave": "conservacion.desconocido_usa", "valor": valor, "fuente_legal": "test 5I-D"})
        assert r.status_code == 200, r.text
    try:
        poner("ruina")
        assert api.get("/api/v1/opciones", headers=headers).json()["valores_defecto"][
            "estado_conservacion_desconocido"] == "ruina"
    finally:
        poner("malo")


def test_el_estado_asumido_es_un_parametro_T3():
    params = cargar_defaults()
    assert params.get("conservacion.desconocido_usa") == "malo"
    ruina = params.con_overrides({"conservacion.desconocido_usa": "ruina"})
    res = ejecutar_analisis(_con_estado(entrada_caso_19(), "desconocido"), params=ruina)
    assert res.reforma.nivel == ejecutar_analisis(_con_estado(entrada_caso_19(), "ruina")).reforma.nivel
    assert "se asume «ruina» (P5)" in res.informe_markdown


def test_los_comparables_no_admiten_no_consta():
    """«No consta» es del inmueble analizado: un comparable sin estado no sirve."""
    cuerpo = json.loads(entrada_base().model_dump_json())
    cuerpo["comparables"][0]["estado"] = "desconocido"
    with pytest.raises(ValidationError) as exc:
        AnalisisInput.model_validate(cuerpo)
    assert [e["loc"] for e in exc.value.errors()] == [("comparables", 0, "estado")]


def test_opciones_ofrece_no_consta_y_su_estado_asumido(api, headers):
    d = api.get("/api/v1/opciones", headers=headers).json()
    assert "desconocido" in d["estados_conservacion"]
    assert d["valores_defecto"]["estado_conservacion_desconocido"] == "malo"


def test_el_alta_con_no_consta_funciona_por_la_api(api, headers):
    cuerpo = json.loads(_con_estado(entrada_base(), "desconocido").model_dump_json())
    r = api.post("/api/v1/analisis", json=cuerpo, headers=headers)
    assert r.status_code == 200, r.text
    det = api.get(f"/api/v1/analisis/{r.json()['id']}", headers=headers).json()
    assert det["entrada"]["activo"]["estado_conservacion"] == "desconocido"

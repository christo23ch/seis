"""Fase 5H.1 — guarda invariante del motor.

`datos/invariante_5h1.json` es la foto del resultado COMPLETO (salvo el Markdown del
informe, que vigila `test_informe_coherencia.py`) del caso §19 y del §19 con hipoteca,
tomada con el motor de `ea60803` ANTES de tocar nada en la 5H.1.

- Caso §19: no puede cambiar NI UNA hoja. Los campos que añade la 5H.1 (VAN, colchón…)
  no están en la foto y no se comparan: añadir no es cambiar.
- Caso con hipoteca: solo puede cambiar lo que lista `CAMBIOS_HIPOTECA`, y exactamente
  al valor indicado. Cualquier otra diferencia hace fallar el test.

Nunca se regenera la foto para «arreglar» este test: si un cambio es legítimo, se añade
a `CAMBIOS_HIPOTECA` con su justificación.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.contracts import AnalisisInput, FinanciacionInput
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19

FOTO = json.loads((Path(__file__).parent / "datos" / "invariante_5h1.json").read_text(encoding="utf-8"))

# Ruta → valor nuevo. Cada entrada, con el bloque de la 5H.1 que la justifica.
CAMBIOS_HIPOTECA: dict[str, object] = {
    # 5H.1-B (D5, auditoría E1): el coste de capital deja de cobrarse a la parte financiada
    # (0,7 · P_max). 3.659,05 − 2.603,76 = 1.055,29 €, y el límite sube 1.056 € al redondear.
    "decision.precios.detalle.coste_capital": 2603.76,
    "decision.precios.p_limite": 78156.0,
    # 5H.1-B: los dos textos que citan el límite, y solo esa cifra.
    "checklist[17].detalle": "Objetivo 57.812 € · Máx 66.266 € · Límite 78.156 €",
    "puja.plan[0]": ("Cargar límites en la interfaz antes de abrir la puja: objetivo 57.812 € · "
                     "máximo 66.266 € · límite absoluto 78.156 € (infranqueable por software)"),
}


def con_hipoteca(entrada: AnalisisInput) -> AnalisisInput:
    return entrada.model_copy(update={"financiacion": FinanciacionInput(
        tipo="hipoteca", preaprobada=True, ltv=0.7, interes_anual_pct=3.5)})


def _hojas(nodo: object, ruta: str = "") -> dict[str, object]:
    if isinstance(nodo, dict):
        out: dict[str, object] = {}
        for k, v in nodo.items():
            out.update(_hojas(v, f"{ruta}.{k}" if ruta else str(k)))
        return out
    if isinstance(nodo, list):
        out = {f"{ruta}[#]": len(nodo)}
        for i, v in enumerate(nodo):
            out.update(_hojas(v, f"{ruta}[{i}]"))
        return out
    return {ruta: nodo}


def _diferencias(foto: dict, entrada: AnalisisInput) -> dict[str, tuple[object, object]]:
    actual = ejecutar_analisis(entrada).model_dump(mode="json")
    actual.pop("informe_markdown")
    antes, ahora = _hojas(foto), _hojas(actual)
    return {r: (v, ahora.get(r, "<AUSENTE>")) for r, v in antes.items() if ahora.get(r, "<AUSENTE>") != v}


def test_la_foto_es_la_de_antes_de_la_fase():
    assert "ea60803" in FOTO["_origen"]
    assert FOTO["caso19"]["decision"]["precios"]["p_limite"] == 80022.0
    assert FOTO["hipoteca"]["decision"]["precios"]["p_limite"] == 77100.0


def test_el_caso_dorado_no_cambia_ni_un_valor():
    difs = _diferencias(FOTO["caso19"], entrada_caso_19())
    assert difs == {}, f"{len(difs)} hojas del §19 han cambiado: {dict(list(difs.items())[:10])}"


def test_el_caso_con_hipoteca_solo_cambia_lo_previsto():
    difs = _diferencias(FOTO["hipoteca"], con_hipoteca(entrada_caso_19()))
    inesperadas = {r: d for r, d in difs.items() if r not in CAMBIOS_HIPOTECA}
    assert inesperadas == {}, f"cambios no previstos: {dict(list(inesperadas.items())[:10])}"
    for ruta, nuevo in CAMBIOS_HIPOTECA.items():
        assert ruta in difs, f"{ruta} debía cambiar y no ha cambiado"
        assert difs[ruta][1] == pytest.approx(nuevo) if isinstance(nuevo, float) else difs[ruta][1] == nuevo, ruta

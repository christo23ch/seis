"""Fase 5H.1 — guarda invariante del motor.

`datos/invariante_5h1.json` es la foto del resultado COMPLETO (salvo el Markdown del
informe, que vigila `test_informe_coherencia.py`) del caso §19 y del §19 con hipoteca.

- Caso §19: no puede cambiar NI UNA hoja. Los campos que se añadan después de la foto
  no están en ella y no se comparan: añadir no es cambiar.
- Caso con hipoteca: solo puede cambiar lo que lista `CAMBIOS_HIPOTECA`, y exactamente
  al valor indicado. Cualquier otra diferencia hace fallar el test.

Nunca se regenera la foto para «arreglar» este test: si un cambio es legítimo, se añade
a `CAMBIOS_HIPOTECA` con su justificación. La única excepción es una fase que cambia
cifras por decisión expresa del responsable, con su tabla antes/después aprobada:

- Tomada con el motor de `ea60803`, antes de la 5H.1.
- **Regenerada en la Fase 5J-2b** (ADR-0024, ADR-0025, ADR-0026): el depósito sale del
  régimen del procedimiento, la táctica de puja depende de la forma de puja y el plazo
  suma la inmovilización entre el cierre y la posesión. Con la regeneración la foto
  vigila también los campos añadidos desde la 5H.1 (176 hojas más por caso), y los
  cambios previstos de la 5H.1 en el caso con hipoteca quedan dentro de ella.
- **Regenerada en la Fase 5J-3** (ADR-0027): aviso de la franja del letrado (techo naranja en el
  §19, ningún número cambia) y cesión de remate de SEM-EJEC-01 y M13. 13 hojas por caso.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.contracts import AnalisisInput, FinanciacionInput
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19

FOTO = json.loads((Path(__file__).parent / "datos" / "invariante_5h1.json").read_text(encoding="utf-8"))

# Ruta → valor nuevo. Cada entrada, con el bloque que la justifica. Vacío desde la
# regeneración de la 5J-2b: los cambios de la 5H.1-B (coste de capital sobre el capital
# propio, D5) ya están dentro de la foto.
CAMBIOS_HIPOTECA: dict[str, object] = {}


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


def test_la_foto_es_la_de_la_5j3():
    assert "5J-3" in FOTO["_origen"]
    assert FOTO["caso19"]["decision"]["semaforo"] == "naranja"
    assert FOTO["caso19"]["procedimiento"]["aviso_aprobacion"]["franja"] == "bajo_suelo"
    assert FOTO["caso19"]["decision"]["precios"]["p_limite"] == 78529.0
    assert FOTO["hipoteca"]["decision"]["precios"]["p_limite"] == 76499.0
    assert FOTO["caso19"]["costes"]["plazo_desglose"]["inmovilizacion"] == 2.5


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

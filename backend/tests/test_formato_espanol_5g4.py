"""Fase 5G.4-B — decimales en formato español en el texto que lee una persona.

El informe (M14), el plan de puja (M13) y las razones del semáforo (M12) usaban
el formato de Python: «25.0%», «6.40%», «RVC 1.08», «CV 5.3%». Pasan a coma
decimal y a «25,0 %» con `app/engine/formato.py` (`decimal`, `pct`). Solo
cambia el texto: el redondeo es el mismo y ningún cálculo se toca (la guarda
numérica de M11/M12 está en `test_coste_capital_5g4.py`, la de M13 en
`test_informe_coherencia.py`).
"""
from __future__ import annotations

import re

import pytest

from app.engine.contracts import AnalisisInput, FinanciacionInput, RentistaInput
from app.engine.formato import decimal, pct
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import caso_19  # noqa: F401 — fixture reutilizada
from tests.test_puja_inviable import _caso_inviable

# Puntos LEGÍTIMOS entre dígitos, que no son decimales: miles de un importe en
# euros, referencias a secciones (§8.7.2) y versiones de reglas/parámetros.
_EUROS = re.compile(r"-?\d{1,3}(?:\.\d{3})+ €")
_SECCION = re.compile(r"§\d+(?:\.\d+)*")
_VERSION = re.compile(r"(?<!\d)v?\d{4}\.\d{2}(?:\+\d+ov)?(?!\d)")   # «v2026.07», «2026.07+1ov»
_DECIMAL_CON_PUNTO = re.compile(r"\d\.\d")
# Única cifra con «%» pegado que queda: el texto de la regla SEM-EJEC-01 del
# catálogo T2 («depósito del 5%»). Era una regla versionada, no texto de un
# módulo, y se anotó como deuda. La 5J-2b la corrigió (SEM-EJEC-01 2026.10, ADR-0024):
# el depósito depende del régimen y el texto ya escribe «20 %» y «5 %» con espacio.
_PORCENTAJE_DE_REGLA = "depósito del 5%"


def _decimales_con_punto(texto: str) -> list[str]:
    limpio = _VERSION.sub("", _SECCION.sub("", _EUROS.sub("", texto)))
    return [limpio[max(0, m.start() - 15):m.end() + 5] for m in _DECIMAL_CON_PUNTO.finditer(limpio)]


def _porcentajes_sin_espacio(texto: str) -> list[str]:
    return re.findall(r".{0,15}\d%", texto)


# ─────────────────────────── formato.py ───────────────────────────

@pytest.mark.parametrize("valor,decimales,signo,esperado", [
    (1.077, 2, False, "1,08"),
    (-1.809, 2, False, "-1,81"),
    (3.0, 1, True, "+3,0"),
    (-2.5, 1, True, "-2,5"),
    (1234.5, 1, False, "1.234,5"),
])
def test_decimal(valor, decimales, signo, esperado):
    assert decimal(valor, decimales, signo=signo) == esperado


@pytest.mark.parametrize("valor,decimales,esperado", [
    (0.25, 1, "25,0 %"), (0.064, 2, "6,40 %"), (0.05, 0, "5 %"),
    (0.2287, 1, "22,9 %"), (-0.0612, 1, "-6,1 %"), (0.053, 1, "5,3 %"),
])
def test_pct(valor, decimales, esperado):
    assert pct(valor, decimales) == esperado


@pytest.mark.parametrize("valor,decimales", [(0.2287, 1), (0.3387, 1), (0.064, 2), (0.248, 1),
                                             (0.0612, 1), (0.42, 0), (0.05, 0), (0.0055, 1)])
def test_pct_redondea_igual_que_el_formato_que_sustituye(valor, decimales):
    """Solo cambian los separadores: mismos dígitos que `:.N%`."""
    antes = f"{valor:.{decimales}%}"
    assert pct(valor, decimales) == antes.replace(".", ",").replace("%", " %")


# ─────────────────────────── casos ───────────────────────────

def _con(caso: AnalisisInput, **cambios) -> AnalisisInput:
    datos = caso.model_dump()
    datos.update(cambios)
    return AnalisisInput(**datos)


@pytest.fixture(scope="module")
def casos(caso_19):  # noqa: F811
    vacio = caso_19.model_dump()
    vacio["ocupacion"] = {"estado": "vacio"}
    vacio["documentos"].update(posesion_verificada=True, fotos_interior_o_visita=True,
                               cert_comunidad=True, ite_cee=True)
    sin_naranja = cargar_defaults().con_overrides({f"semaforo.{c}.ico_min": 99
                                                   for c in ("verde", "amarillo", "naranja")})
    return {
        "dorado": ejecutar_analisis(caso_19),
        "degenerado": ejecutar_analisis(
            caso_19, params=cargar_defaults().con_overrides({"capital.coste_capital_anual": 0.31})),
        "inviable": ejecutar_analisis(_caso_inviable()),
        "hipoteca": ejecutar_analisis(_con(caso_19, financiacion=FinanciacionInput(
            tipo="hipoteca", preaprobada=True, ltv=0.7, interes_anual_pct=3.5))),
        "rentista": ejecutar_analisis(_con(caso_19, perfil="rentista", rentista=RentistaInput(
            renta_mensual_estimada=950, ibi_anual=350, comunidad_mensual=60))),
        "verde": ejecutar_analisis(AnalisisInput(**vacio), params=cargar_defaults().con_overrides(
            {"semaforo.verde.ico_min": 60})),
        "no_alcanza_naranja": ejecutar_analisis(caso_19, params=sin_naranja),
    }


NOMBRES = ["dorado", "degenerado", "inviable", "hipoteca", "rentista", "verde", "no_alcanza_naranja"]


@pytest.mark.parametrize("nombre", NOMBRES)
def test_ninguna_cifra_decimal_del_informe_usa_punto(casos, nombre):
    r = casos[nombre]
    assert _decimales_con_punto(r.informe_markdown) == []
    assert _decimales_con_punto(" ".join(r.puja.plan)) == []
    assert _decimales_con_punto(" ".join(r.decision.razones)) == []


@pytest.mark.parametrize("nombre", NOMBRES)
def test_los_porcentajes_llevan_espacio_antes_del_simbolo(casos, nombre):
    r = casos[nombre]
    assert _porcentajes_sin_espacio(r.informe_markdown) == []
    assert _porcentajes_sin_espacio(" ".join(r.puja.plan)) == []
    assert _porcentajes_sin_espacio(" ".join(r.decision.razones)) == []


def test_las_razones_de_m12_con_cifras_salen_en_formato_espanol(casos):
    """Las dos razones de M12 que llevan decimales, ejercidas de verdad."""
    assert casos["verde"].decision.semaforo == "verde"
    verde = casos["verde"].decision.razones[0]
    assert re.search(r"MS \d+ %; RVC \d+,\d{2}$", verde), verde
    assert casos["no_alcanza_naranja"].decision.razones == [
        "No alcanza Naranja: ICO insuficiente (ICO 64, RVC 1,06)"]     # 1,08 antes de la 5J-2b


def test_la_deuda_de_la_regla_esta_saldada(casos):
    """La regla SEM-EJEC-01 (T2) era el único «%» pegado; desde la 5J-2b no queda ninguno."""
    assert _PORCENTAJE_DE_REGLA not in casos["dorado"].informe_markdown
    assert _porcentajes_sin_espacio(casos["dorado"].informe_markdown) == []

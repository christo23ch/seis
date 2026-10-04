"""Fase 5G.2 — coherencia del texto del informe (M13/M14).

Dos defectos vistos en un PDF oficial real:

1. Con la escalera de precios degenerada (§9.3) el semáforo salía ROJO, pero la
   tabla seguía presentando el precio límite como «infranqueable» y el plan de
   puja instruía a «cargar límites» con ese valor (incluso negativo).
2. El plan de puja de M13 formateaba con `:,.0f` («60,011 €», «7,600 €»)
   mientras el resto del informe usa el formato español («60.011 €»).

Lo que se cambia es REDACCIÓN: M13 y M14 siguen calculando exactamente lo mismo.
`test_m13_no_cambia_ningun_valor_numerico` lo fija con valores capturados ANTES
del cambio, y el informe del caso dorado §19 se compara con su texto anterior
(`datos/informe_caso19_antes_5g2.md`), del que solo pueden cambiar las cifras
mal formateadas.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import caso_19  # noqa: F401 — fixture reutilizada
from tests.test_puja_inviable import _caso_inviable

TEXTO_TABLA_DEGENERADA = "| **Precio límite absoluto** | No utilizable: escalera de precios degenerada (§9.3) |"
TEXTO_PLAN_DEGENERADA = ("No cargar límites ni pujar: la escalera de precios es degenerada (§9.3); "
                         "la estructura de costes consume el valor y no hay precio límite utilizable")
TEXTO_CHECKLIST = "Escalera de precios cargada en la interfaz de puja"
DETALLE_CHECKLIST_DEGENERADA = "Escalera de precios degenerada (§9.3): no hay escalera utilizable para pujar."
# Cifra con separador de miles inglés seguida de euros: «60,011 €», «-13,894 €».
MILES_INGLES = re.compile(r"\d{1,3}(?:,\d{3})+ ?€")
ANTES = Path(__file__).parent / "datos" / "informe_caso19_antes_5g2.md"


@pytest.fixture(scope="module")
def dorado(caso_19):  # noqa: F811
    return ejecutar_analisis(caso_19)


@pytest.fixture(scope="module")
def dorado_degenerado(caso_19):  # noqa: F811
    """El caso §19 con el coste de capital de la simulación del hallazgo (0,31):
    el límite cae por debajo del máximo y la escalera queda degenerada."""
    params = cargar_defaults().con_overrides({"capital.coste_capital_anual": 0.31})
    return ejecutar_analisis(caso_19, params=params)


@pytest.fixture(scope="module")
def inviable():
    return ejecutar_analisis(_caso_inviable())


# ─────────────── M13: solo texto, ni un número distinto ───────────────

# Capturados con el código ANTERIOR a 5G.2 (commit a1591bc).
NUMEROS_M13_ANTES = {
    "dorado": {"p_adj_esperado": 63840.0, "ratio_base": 0.42, "rvc": 1.077,
               "banda_rvc": "alcanzable"},
    "dorado_degenerado": {"p_adj_esperado": 63840.0, "ratio_base": 0.42, "rvc": 1.077,
                          "banda_rvc": "alcanzable"},
    "inviable": {"p_adj_esperado": 12865.45, "ratio_base": 0.55, "rvc": -1.809,
                 "banda_rvc": "inviable"},
}
ESCALERA_ANTES = {
    "dorado": (51317.0, 60011.0, 68731.0, 80022.0, False),
    "dorado_degenerado": (51317.0, 60011.0, 68731.0, 8061.0, True),
    "inviable": (-25242.0, -24153.0, -23272.0, -20842.0, True),
}


@pytest.mark.parametrize("caso", ["dorado", "dorado_degenerado", "inviable"])
def test_m13_no_cambia_ningun_valor_numerico(caso, request):
    r = request.getfixturevalue(caso)
    p = r.puja
    numeros = {"p_adj_esperado": p.p_adj_esperado, "ratio_base": p.ratio_base,
               "rvc": p.rvc, "banda_rvc": p.banda_rvc}
    assert numeros == NUMEROS_M13_ANTES[caso]
    e = r.decision.precios
    assert (e.p_ideal, e.p_objetivo, e.p_max, e.p_limite, e.degenerada) == ESCALERA_ANTES[caso]


# ─────────────── formato ───────────────

@pytest.mark.parametrize("caso", ["dorado", "dorado_degenerado", "inviable"])
def test_ninguna_cifra_usa_separador_de_miles_ingles(caso, request):
    r = request.getfixturevalue(caso)
    assert not MILES_INGLES.findall(r.informe_markdown)
    assert not MILES_INGLES.findall(" ".join(r.puja.plan))


# Fase 5G.4-A: línea explicativa del coste de capital, al final de la tabla de
# escenarios de la sección 7. Es la única línea nueva del informe en esa fase.
FILA_OPTIMISTA = "| optimista | 20% | 186.996 € | 133.996 € | 53.000 € | 39.6% | 43.6% | 11 m |\n"
LINEA_COSTE_CAPITAL = ("\nEl coste de capital (1,5 % anual, coste de oportunidad del capital propio) "
                       "solo se descuenta del precio límite (§9.1); ROI y TIR no lo incluyen. "
                       "Importe aplicado: 3.659 €.\n")
# Fase 5H.1-A (ADR-0017): VAN y diferencial, justo después de la línea anterior.
LINEA_VAN_5H1A = ("\nVAN al coste de capital (1,5 %): 33.230 € · "
                  "TIR frente a coste de capital: +32,37 puntos\n")


# Fase 5G.4-B: decimales en formato español. Cada par es un fragmento EXACTO del
# texto anterior y su sustituto; ninguna cifra cambia, solo «.»→«,» y «%»→« %».
# Se aplican uno a uno y cada uno debe aparecer el número de veces indicado: si
# el informe cambiara en cualquier otra cosa, la igualdad final fallaría.
FORMATO_5G4B = [
    # §1 página de decisión
    ("| ROI base (a P objetivo) | 25.0% (22.9% anualizado) |",
     "| ROI base (a P objetivo) | 25,0 % (22,9 % anualizado) |", 1),
    ("| TIR anual | 33.9% |", "| TIR anual | 33,9 % |", 1),
    ("| Margen de seguridad (caída de VS soportable) | 24.8% |",
     "| Margen de seguridad (caída de VS soportable) | 24,8 % |", 1),
    ("63.840 € · **1.08** (alcanzable)", "63.840 € · **1,08** (alcanzable)", 1),
    # §2 activo y subasta
    ("depósito 5%. Ocupación", "depósito 5 %. Ocupación", 1),
    # §3 valoración
    ("(CV 5.3%, confianza 76%)", "(CV 5,3 %, confianza 76 %)", 1),
    ("δ_v aplicado 6.0% ⇒", "δ_v aplicado 6,0 % ⇒", 1),
    # §4 mercado
    ("Tendencia +3.0 %/a", "Tendencia +3,0 %/a", 1),
    # §5 costes
    ("c_v = 6.40% (ITP)", "c_v = 6,40 % (ITP)", 1),
    ("Contingencia 10%.", "Contingencia 10 %.", 1),
    # §7 escenarios
    ("| pesimista | 25% | 160.837 € | 151.559 € | 9.278 € | 6.1% | 4.0% | 18 m |",
     "| pesimista | 25 % | 160.837 € | 151.559 € | 9.278 € | 6,1 % | 4,0 % | 18 m |", 1),
    ("| base | 55% | 176.744 € | 141.396 € | 35.349 € | 25.0% | 22.9% | 13 m |",
     "| base | 55 % | 176.744 € | 141.396 € | 35.349 € | 25,0 % | 22,9 % | 13 m |", 1),
    ("| optimista | 20% | 186.996 € | 133.996 € | 53.000 € | 39.6% | 43.6% | 11 m |",
     "| optimista | 20 % | 186.996 € | 133.996 € | 53.000 € | 39,6 % | 43,6 % | 11 m |", 1),
    # §8 estrategia de puja (M13)
    ("Ratio histórico del segmento: 42% sobre", "Ratio histórico del segmento: 42 % sobre", 1),
    ("(5% del valor de subasta)", "(5 % del valor de subasta)", 1),
]


def test_sin_escalera_degenerada_el_informe_es_el_de_antes_salvo_el_formato(dorado):
    """Diferencias permitidas con el texto anterior, y ninguna más:
    - 5G.2: las cuatro cifras del plan de puja que salían con separador inglés;
    - 5G.4-A: la línea del coste de capital tras la fila «optimista» (§7);
    - 5H.1-A: la línea del VAN y el diferencial, a continuación;
    - 5G.4-B: los fragmentos de `FORMATO_5G4B` (solo separadores decimales y «%»)."""
    antes = ANTES.read_text(encoding="utf-8")
    corregido = MILES_INGLES.sub(lambda m: m.group(0).replace(",", "."), antes)
    assert corregido != antes, "premisa: el texto anterior tenía cifras en formato inglés"
    assert corregido.count(FILA_OPTIMISTA) == 1
    corregido = corregido.replace(FILA_OPTIMISTA, FILA_OPTIMISTA + LINEA_COSTE_CAPITAL + LINEA_VAN_5H1A)
    for viejo, nuevo, veces in FORMATO_5G4B:
        assert corregido.count(viejo) == veces, viejo
        # Mismos dígitos en el mismo orden: solo pueden cambiar separadores y espacios.
        assert re.findall(r"\d", viejo) == re.findall(r"\d", nuevo), viejo
        assert re.sub(r"[\d.,% ]", "", viejo) == re.sub(r"[\d.,% ]", "", nuevo), viejo
        corregido = corregido.replace(viejo, nuevo)
    assert dorado.informe_markdown == corregido


def test_sin_escalera_degenerada_el_plan_es_el_de_antes_salvo_el_formato(dorado):
    assert dorado.puja.plan == [
        "Cargar límites en la interfaz antes de abrir la puja: objetivo 60.011 € · "
        "máximo 68.731 € · límite absoluto 80.022 € (infranqueable por software)",
        "Pujar siempre el tramo mínimo; sin pujas psicológicas redondas",
        "Entrar tarde con límites precargados: la extensión automática del cierre neutraliza "
        "el sniping; la ventaja es la disciplina",
        "Depósito requerido: 7.600 € (5 % del valor de subasta)",   # 5G.4-B
        "Si aparece información nueva durante la subasta, re-análisis exprés; si el semáforo "
        "cae, retirada",
    ]
    assert "| **Precio límite absoluto** | 80.022 € — infranqueable |" in dorado.informe_markdown


# ─────────────── escalera degenerada ───────────────

@pytest.mark.parametrize("caso", ["dorado_degenerado", "inviable"])
def test_con_escalera_degenerada_no_se_instruye_cargar_el_limite(caso, request):
    r = request.getfixturevalue(caso)
    inf = r.informe_markdown

    assert "Cargar límites" not in inf
    assert "infranqueable" not in inf
    assert TEXTO_TABLA_DEGENERADA in inf
    assert f"- {TEXTO_PLAN_DEGENERADA}" in inf
    # Las instrucciones de cómo pujar desaparecen; lo informativo se queda.
    assert r.puja.plan[0] == TEXTO_PLAN_DEGENERADA
    assert not any(p.startswith(("Pujar siempre", "Entrar tarde")) for p in r.puja.plan)
    assert any(p.startswith("Depósito requerido:") for p in r.puja.plan)
    assert any(p.startswith("Si aparece información nueva") for p in r.puja.plan)


def test_con_escalera_degenerada_el_limite_no_aparece_como_cifra(dorado_degenerado):
    """El valor calculado sigue en el resultado; el texto no lo ofrece."""
    assert dorado_degenerado.decision.precios.p_limite == 8061.0
    assert "8.061 €" not in dorado_degenerado.informe_markdown


def test_con_escalera_degenerada_la_escalera_es_un_bloqueante_pendiente(dorado_degenerado):
    item = next(c for c in dorado_degenerado.checklist if c.texto == TEXTO_CHECKLIST)
    assert item.bloqueante and item.estado == "pendiente"
    assert item.detalle == DETALLE_CHECKLIST_DEGENERADA

    seccion = dorado_degenerado.informe_markdown.split("## 9 · Checklist")[1].split("## 10")[0]
    assert TEXTO_CHECKLIST in seccion
    assert DETALLE_CHECKLIST_DEGENERADA in seccion


def test_sin_escalera_degenerada_la_escalera_sigue_ok(dorado):
    item = next(c for c in dorado.checklist if c.texto == TEXTO_CHECKLIST)
    assert item.estado == "ok"
    assert item.detalle == "Objetivo 60.011 € · Máx 68.731 € · Límite 80.022 €"

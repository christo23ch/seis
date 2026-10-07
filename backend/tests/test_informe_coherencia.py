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

from app.engine import procedimiento
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

# Capturados con el código ANTERIOR a 5G.2 (commit a1591bc) y recapturados en la Fase 5J-2b,
# que cambia cifras con aprobación del responsable (el plazo suma la inmovilización, ADR-0026).
# Antes de la 5J-2b: RVC 1,077 / 1,077 / −1,809; escaleras (51.317, 60.011, 68.731, 80.022),
# (…, 8.061) y (−25.242, −24.153, −23.272, −20.842).
NUMEROS_M13_ANTES = {
    "dorado": {"p_adj_esperado": 63840.0, "ratio_base": 0.42, "rvc": 1.064,
               "banda_rvc": "alcanzable"},
    "dorado_degenerado": {"p_adj_esperado": 63840.0, "ratio_base": 0.42, "rvc": 1.064,
                          "banda_rvc": "alcanzable"},
    "inviable": {"p_adj_esperado": 12865.45, "ratio_base": 0.55, "rvc": -1.85,
                 "banda_rvc": "inviable"},
}
ESCALERA_ANTES = {
    "dorado": (50753.0, 59447.0, 67941.0, 78529.0, False),
    "dorado_degenerado": (50753.0, 59447.0, 67941.0, -7271.0, True),
    "inviable": (-25622.0, -24533.0, -23804.0, -21421.0, True),
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
# Fase 5H.1-C (§9.5, ADR-0019): colchón de plazo, a continuación.
LINEA_COLCHON_5H1C = ("\nColchón de plazo: 84,8 meses a precio objetivo (60,9 a precio máximo), "
                      "hasta beneficio cero por tenencia y coste de capital.\n")


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


# Fase 5J-2a: textos legibles (`app/engine/textos.py`). Cada par es un fragmento EXACTO del
# texto anterior y su sustituto; ninguna cifra cambia, solo nombres de códigos y símbolos.
TEXTOS_5J2A = [
    # §2 activo y subasta
    ("Subasta judicial_boe,", "Subasta judicial (Portal de Subastas del BOE),", 1),
    # §3 valoración
    ("Método comparables_ajustados con 7 comparables", "Método: comparables ajustados, con 7 comparables", 1),
    ("δ_v aplicado 6,0 %", "descuento de prudencia aplicado 6,0 %", 1),
    # §5 costes
    ("c_v = 6,40 % (ITP)", "Costes proporcionales al precio: 6,40 % (ITP)", 1),
    ("| Partida C_F (P50) |", "| Partida de costes fijos (P50) |", 1),
    ("| reforma | 50.053 € |", "| Reforma | 50.053 € |", 1),
    ("| ocupacion_desalojo |", "| Ocupación y desalojo |", 1),
    ("| atrasos_comunidad_ibi |", "| Atrasos de comunidad e IBI |", 1),
    ("| adquisicion_fija |", "| Costes fijos de adquisición |", 1),
    ("| tenencia |", "| Tenencia |", 1),
    ("| comercializacion |", "| Comercialización |", 1),
    ("| contingencia |", "| Contingencia |", 1),
    ("| cargas_subsistentes |", "| Cargas subsistentes |", 1),
    ("| plusvalia_municipal |", "| Plusvalía municipal |", 1),
    ("| **Total C_F P50 / P80** |", "| **Total de costes fijos P50 / P80** |", 1),
    # §6 riesgos
    ("| juridico |", "| jurídico |", 1),
    ("Subsanar: posesion_verificada; Subsanar: fotos_interior_o_visita; Subsanar: cert_comunidad; "
     "Subsanar: ite_cee",
     "Subsanar: posesión verificada; Subsanar: fotos interiores o visita; Subsanar: certificado de la "
     "comunidad; Subsanar: ITE y certificado energético", 1),
    ("| ocupacion |", "| ocupación |", 1),
    ("| urbanistico |", "| urbanístico |", 1),
    ("| tecnico |", "| técnico |", 1),
    ("dominancia: una_alta)", "dominancia: una dimensión alta)", 1),
    # §9 checklist (el texto del dato no cambia: se redacta legible)
    ("y aplicada en c_v —", "y aplicada en costes proporcionales —", 1),
    # §10 trazabilidad
    ("(semaforo)", "(semáforo)", 2),
]


# Fase 5J-2b: la fase CAMBIA CIFRAS con aprobación expresa del responsable (ADR-0024 depósito,
# ADR-0025 táctica de puja, ADR-0026 plazo). Cada par es un fragmento EXACTO del texto anterior
# y su sustituto; aquí sí cambian dígitos, y la tabla antes/después aprobada es la referencia.
CAMBIOS_5J2B = [
    # §1 página de decisión: la escalera baja (más tenencia y coste de capital, ADR-0026)
    ("| **Precio ideal** | 51.317 € |", "| **Precio ideal** | 50.753 € |", 1),
    ("| **Precio objetivo** | 60.011 € |", "| **Precio objetivo** | 59.447 € |", 1),
    ("| **Precio máximo recomendado** | 68.731 € |", "| **Precio máximo recomendado** | 67.941 € |", 1),
    ("| **Precio límite absoluto** | 80.022 € — infranqueable |",
     "| **Precio límite absoluto** | 78.529 € — infranqueable |", 1),
    ("(22,9 % anualizado)", "(18,9 % anualizado)", 1),
    ("| TIR anual | 33,9 % |", "| TIR anual | 26,4 % |", 1),
    ("| Valor esperado (3 escenarios) | 32.361 € |", "| Valor esperado (3 escenarios) | 32.301 € |", 1),
    ("63.840 € · **1,08** (alcanzable)", "63.840 € · **1,06** (alcanzable)", 1),
    # §1 condiciones: SEM-EJEC-01 2026.10 (ADR-0024)
    ("depósito del 5% y pago del remate",
     "depósito según el régimen del procedimiento (20 % con la LO 1/2025; 5 % si se inició antes del "
     "3-4-2025) y pago del remate", 1),
    # §2 activo y subasta: el depósito exigido por el régimen (ADR-0024)
    ("depósito 5 %. Ocupación",
     "depósito 30.400 € (20 % del valor de subasta); supuesto desfavorable: no consta cuándo se inició "
     "el procedimiento judicial (si fue antes del 3-4-2025, es menor). Ocupación", 1),
    # §5 costes: + 2,5 meses de inmovilización (ADR-0026)
    # y desde la revisión de la fase, con su decimal: `:.0f` redondeaba 15,5 a 16 (a par).
    ("Plazo total 13 m (P50) / 18 m (P80).", "Plazo total 15,5 m (P50) / 21,7 m (P80).", 1),
    ("| Tenencia | 3.120 € |", "| Tenencia | 3.720 € |", 1),
    ("**77.544 € / 87.708 €**", "**78.144 € / 88.548 €**", 1),
    # §7 análisis financiero
    ("(a precio objetivo 60.011 €)", "(a precio objetivo 59.447 €)", 1),
    ("| pesimista | 25 % | 160.837 € | 151.559 € | 9.278 € | 6,1 % | 4,0 % | 18 m |",
     "| pesimista | 25 % | 160.837 € | 151.799 € | 9.038 € | 5,9 % | 3,2 % | 21,7 m |", 1),
    ("| base | 55 % | 176.744 € | 141.396 € | 35.349 € | 25,0 % | 22,9 % | 13 m |",
     "| base | 55 % | 176.744 € | 141.396 € | 35.349 € | 25,0 % | 18,9 % | 15,5 m |", 1),
    ("| optimista | 20 % | 186.996 € | 133.996 € | 53.000 € | 39,6 % | 43,6 % | 11 m |",
     "| optimista | 20 % | 186.996 € | 133.996 € | 53.000 € | 39,6 % | 35,5 % | 13,2 m |", 1),
    ("Importe aplicado: 3.659 €.", "Importe aplicado: 4.363 €.", 1),
    ("(1,5 %): 33.230 € · TIR frente a coste de capital: +32,37 puntos",
     "(1,5 %): 32.721 € · TIR frente a coste de capital: +24,91 puntos", 1),
    ("(60,9 a precio máximo)", "(61,5 a precio máximo)", 1),
    # §8 plan de puja: táctica por forma de puja (ADR-0025) y depósito del régimen (ADR-0024)
    ("- Cargar límites en la interfaz antes de abrir la puja: objetivo 60.011 € · máximo 68.731 € · "
     "límite absoluto 80.022 € (infranqueable por software)\n"
     "- Pujar siempre el tramo mínimo; sin pujas psicológicas redondas\n"
     "- Entrar tarde con límites precargados: la extensión automática del cierre neutraliza el sniping; "
     "la ventaja es la disciplina\n"
     "- Depósito requerido: 7.600 € (5 % del valor de subasta)\n",
     "- Decidir la cifra antes de abrir la puja, entre objetivo 59.447 € · máximo 67.941 € · "
     "límite absoluto 78.529 € (infranqueable por software)\n"
     "- Pujas secretas y cierre improrrogable (LO 1/2025): no se ven las pujas ajenas ni hay prórroga, "
     "así que no cabe reaccionar al final ni subir por tramos; se puja directamente la cifra decidida; "
     "si el procedimiento se inició antes del 3-4-2025, las pujas se ven y el cierre se prorroga, y esta "
     "táctica sigue siendo válida\n"
     "- No apurar el cierre: sin prórroga, una puja que no llegue a tiempo por un fallo técnico queda fuera\n"
     "- Depósito requerido: 30.400 € (20 % del valor de subasta); supuesto desfavorable: no consta cuándo "
     "se inició el procedimiento judicial (si fue antes del 3-4-2025, es menor)\n", 1),
    # §9 checklist y §10 trazabilidad
    ("Depósito disponible y transferido en plazo — _7.600 €_",
     "Depósito disponible y transferido en plazo — _30.400 €_", 1),
    ("`SEM-EJEC-01` v2026.07", "`SEM-EJEC-01` v2026.10", 1),
]


# Fase 5J-3 (ADR-0027): aviso de la franja del letrado y cesión de remate. Ningún número cambia:
# el semáforo pasa a naranja, se añade el bloque destacado (su texto lo fija
# `tests/test_aviso_aprobacion_5j3.py`), una condición, un bloqueante y la cesión de remate.
CESION_5J2B = "cesión de remate solo por el ejecutante (§3.2)"
CESION_5J3 = ("cesión de remate solo por el ejecutante y, con la LO 1/2025, también por los acreedores "
              "posteriores (LEC, art. 647, apdo. 3) (§3.2)")


def _cambios_5j3(dorado) -> list[tuple[str, str, int]]:
    aviso = dorado.procedimiento.aviso_aprobacion
    condiciones = "; ".join(dorado.decision.condiciones)
    return [
        ("# 🟡 AMARILLO\n", f"# 🟠 NARANJA\n\n{procedimiento.bloque_aviso_aprobacion(aviso)}\n", 1),
        ("o límites de Verde no alcanzados\n",
         f"o límites de Verde no alcanzados · {aviso.titulo} ⇒ techo Naranja con condición (5J-3) · "
         "Techo aplicado: naranja\n", 1),
        (f"{CESION_5J2B}\n", f"{CESION_5J3}\n- {aviso.condicion}\n", 1),
        ("- Cesión de remate solo disponible para el ejecutante: la estructura compradora final debe pujar "
         "directamente\n", f"- {dorado.puja.riesgo_ejecucion[-1]}\n", 1),
        ("Depósito disponible y transferido en plazo — _30.400 €_\n",
         "Depósito disponible y transferido en plazo — _30.400 €_\n"
         "- [ ] **[B]** Semáforo Verde/Amarillo, o Naranja con todas sus condiciones verificadas y firmadas "
         f"— _{condiciones}_\n"
         f"- [ ] **[B]** Riesgo de aprobación del remate asumido por escrito — _{aviso.condicion}_\n", 1),
        ("`SEM-EJEC-01` v2026.10 ", "`SEM-EJEC-01` v2026.10.07 ", 1),
    ]


def test_sin_escalera_degenerada_el_informe_es_el_de_antes_salvo_el_formato(dorado):
    """Diferencias permitidas con el texto anterior, y ninguna más:
    - 5G.2: las cuatro cifras del plan de puja que salían con separador inglés;
    - 5G.4-A: la línea del coste de capital tras la fila «optimista» (§7);
    - 5H.1-A: la línea del VAN y el diferencial, a continuación;
    - 5H.1-C: la línea del colchón de plazo, a continuación;
    - 5G.4-B: los fragmentos de `FORMATO_5G4B` (solo separadores decimales y «%»);
    - 5J-1: el subapartado informativo del procedimiento, al final del §8 y antes del
      §9. Su texto lo fijan `tests/test_procedimiento_5j1.py`; aquí se vigila que sea
      lo ÚNICO añadido y que esté en su sitio;
    - 5J-2a: los fragmentos de `TEXTOS_5J2A` (nombres de códigos y símbolos, mismos dígitos);
    - 5J-2b: los fragmentos de `CAMBIOS_5J2B`, que sí cambian cifras (tabla aprobada);
    - 5J-3: `_cambios_5j3` (semáforo, aviso de la franja del letrado y cesión de remate)."""
    antes = ANTES.read_text(encoding="utf-8")
    corregido = MILES_INGLES.sub(lambda m: m.group(0).replace(",", "."), antes)
    assert corregido != antes, "premisa: el texto anterior tenía cifras en formato inglés"
    assert corregido.count(FILA_OPTIMISTA) == 1
    corregido = corregido.replace(FILA_OPTIMISTA, FILA_OPTIMISTA + LINEA_COSTE_CAPITAL + LINEA_VAN_5H1A
                                  + LINEA_COLCHON_5H1C)
    for viejo, nuevo, veces in FORMATO_5G4B:
        assert corregido.count(viejo) == veces, viejo
        # Mismos dígitos en el mismo orden: solo pueden cambiar separadores y espacios.
        assert re.findall(r"\d", viejo) == re.findall(r"\d", nuevo), viejo
        assert re.sub(r"[\d.,% ]", "", viejo) == re.sub(r"[\d.,% ]", "", nuevo), viejo
        corregido = corregido.replace(viejo, nuevo)
    for viejo, nuevo, veces in TEXTOS_5J2A:
        assert corregido.count(viejo) == veces, viejo
        assert re.findall(r"\d", viejo) == re.findall(r"\d", nuevo), viejo
        corregido = corregido.replace(viejo, nuevo)
    for viejo, nuevo, veces in CAMBIOS_5J2B:
        assert corregido.count(viejo) == veces, viejo
        corregido = corregido.replace(viejo, nuevo)
    for viejo, nuevo, veces in _cambios_5j3(dorado):
        assert corregido.count(viejo) == veces, viejo
        corregido = corregido.replace(viejo, nuevo)
    ancla = "\n\n## 9 · Checklist"
    assert corregido.count(ancla) == 1
    corregido = corregido.replace(ancla, procedimiento.seccion_informe(dorado.procedimiento) + ancla)
    assert dorado.informe_markdown == corregido


def test_sin_escalera_degenerada_el_plan_es_el_de_antes_salvo_el_formato(dorado):
    # Fase 5J-2b: régimen judicial sin fecha de inicio ⇒ táctica de pujas secretas (ADR-0025)
    # y depósito del 20 % (ADR-0024).
    assert dorado.puja.plan == [
        "Decidir la cifra antes de abrir la puja, entre objetivo 59.447 € · "
        "máximo 67.941 € · límite absoluto 78.529 € (infranqueable por software)",
        "Pujas secretas y cierre improrrogable (LO 1/2025): no se ven las pujas ajenas ni hay prórroga, "
        "así que no cabe reaccionar al final ni subir por tramos; se puja directamente la cifra decidida; "
        "si el procedimiento se inició antes del 3-4-2025, las pujas se ven y el cierre se prorroga, y "
        "esta táctica sigue siendo válida",
        "No apurar el cierre: sin prórroga, una puja que no llegue a tiempo por un fallo técnico queda fuera",
        "Depósito requerido: 30.400 € (20 % del valor de subasta); supuesto desfavorable: no consta "
        "cuándo se inició el procedimiento judicial (si fue antes del 3-4-2025, es menor)",
        "Si aparece información nueva durante la subasta, re-análisis exprés; si el semáforo "
        "cae, retirada",
    ]
    assert "| **Precio límite absoluto** | 78.529 € — infranqueable |" in dorado.informe_markdown


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
    assert not any(p.startswith(("Pujar siempre", "Entrar tarde", "Decidir la cifra", "Pujas secretas",
                                 "No apurar")) for p in r.puja.plan)
    assert any(p.startswith("Depósito requerido:") for p in r.puja.plan)
    assert any(p.startswith("Si aparece información nueva") for p in r.puja.plan)


def test_con_escalera_degenerada_el_limite_no_aparece_como_cifra(dorado_degenerado):
    """El valor calculado sigue en el resultado; el texto no lo ofrece."""
    assert dorado_degenerado.decision.precios.p_limite == -7271.0      # 8.061 antes de la 5J-2b
    assert "7.271 €" not in dorado_degenerado.informe_markdown


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
    assert item.detalle == "Objetivo 59.447 € · Máx 67.941 € · Límite 78.529 €"

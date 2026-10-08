"""Fase 5J-4 — puja mínima aprobable como recomendación y veredicto (ADR-0028).

Decisiones del responsable (parada 2 aprobada con el semáforo C):

- El informe muestra tres cifras: precio máximo económico (P_max), puja mínima aprobable según
  régimen y vivienda habitual, y puja de aprobación segura; los umbrales son parámetros T3.
- La puja recomendada solo se ofrece si la mínima aprobable cabe en P_max (la mayor entre el
  precio objetivo y la mínima). Si no, «inviable con estas condiciones»: no se recomienda ninguna
  puja, se explica qué tendría que cambiar y la rentabilidad, el ICO y el margen se calculan a la
  mínima aprobable, con aviso.
- Semáforo C: inviable y mínima aprobable > P_límite ⇒ rojo; si cabe en P_límite ⇒ como máximo
  naranja, con la condición de aceptar un margen menor que el del perfil. Los viables conservan su
  semáforo. Nunca hay veto.
- Cantidad reclamada: el suelo del 40 % solo si se informó. Vivienda habitual «no consta» ⇒ se
  asume que sí, y el informe da la mínima aprobable si no lo fuera.
- Segunda línea del veredicto inviable: qué pasaría con una puja de P_max (no aprobable, solo si
  cubre la deuda o aprobación discrecional). No cambia el veredicto.
"""
from __future__ import annotations

import pytest

from app.engine import procedimiento
from app.engine.contracts import AnalisisInput, DecisionFinal, EscaleraPrecios
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19

POSTERIOR = {"procedimiento": "judicial", "regimen_judicial": "posterior"}
ANTERIOR = {"procedimiento": "judicial", "regimen_judicial": "anterior"}


def _entrada(vivienda: str | None = None, **subasta) -> AnalisisInput:
    base = entrada_caso_19()
    activo = base.activo if vivienda is None else base.activo.model_copy(
        update={"vivienda_habitual_ejecutado": vivienda})
    return base.model_copy(update={"subasta": base.subasta.model_copy(update=subasta), "activo": activo})


def _analizar(vivienda: str | None = None, **subasta):
    return ejecutar_analisis(_entrada(vivienda, **subasta))


# ─────────────────────── tabla aprobada en la parada 2 ───────────────────────

@pytest.mark.parametrize("vivienda,subasta,minima,segura,estado,semaforo,ico", [
    (None, {}, 106400.0, 106400.0, "inviable", "rojo", 49),                  # §19
    ("si", {}, 106400.0, 106400.0, "inviable", "rojo", 49),
    ("no", {}, 76000.0, 106400.0, "inviable", "naranja", 52),
    (None, ANTERIOR, 106400.0, 106400.0, "inviable", "rojo", 49),
    ("no", ANTERIOR, 76001.0, 106400.0, "inviable", "naranja", 52),         # hay que superar el 50 %
    (None, {"procedimiento": "aeat"}, 76000.0, 76000.0, "inviable", "naranja", 52),
    ("no", {**POSTERIOR, "cantidad_reclamada": 60000.0}, 60800.0, 106400.0, "viable", "amarillo", 63),
    ("no", {**POSTERIOR, "valor_subasta": 80000.0}, 40000.0, 56000.0, "viable", "amarillo", 64),
])
def test_tabla_de_la_parada_2(vivienda, subasta, minima, segura, estado, semaforo, ico):
    r = _analizar(vivienda, **subasta)
    v = r.decision.veredicto
    assert (v.puja_minima_efectiva, v.puja_aprobacion_segura, v.estado) == (minima, segura, estado)
    assert (r.decision.semaforo, r.decision.ico) == (semaforo, ico)
    assert r.rentabilidad.precio_evaluado == v.puja_evaluada
    assert not r.decision.vetos


def test_la_escalera_los_costes_y_el_rvc_no_cambian():
    """El veredicto solo añade un suelo legal: la escalera económica es la de la 5J-3."""
    r = _analizar()
    p = r.decision.precios
    assert (p.p_ideal, p.p_objetivo, p.p_max, p.p_limite) == (50753.0, 59447.0, 67941.0, 78529.0)
    assert r.decision.rvc == pytest.approx(1.064, abs=0.001)


# ─────────────────────────── viable ───────────────────────────

def test_viable_al_precio_objetivo_no_cambia_nada():
    r = _analizar("no", **POSTERIOR, valor_subasta=80000.0)
    v = r.decision.veredicto
    assert v.puja_recomendada == v.puja_evaluada == r.decision.precios.p_objetivo
    assert v.aviso_rentabilidad is None and v.cambios == [] and v.condicion is None
    assert v.titulo == "Puja aprobable dentro del precio máximo"
    assert "| ROI base (a P objetivo) |" in r.informe_markdown
    assert r.puja.plan[0].startswith("Decidir la cifra antes de abrir la puja")


def test_viable_a_la_minima_aprobable_la_recomienda_y_evalua_ahi():
    r = _analizar("no", **POSTERIOR, cantidad_reclamada=60000.0)
    v = r.decision.veredicto
    assert r.decision.precios.p_objetivo < v.puja_minima_efectiva <= r.decision.precios.p_max
    assert v.puja_recomendada == v.puja_evaluada == 60800.0
    assert v.aviso_rentabilidad == ("La rentabilidad se calcula a la puja recomendada (60.800 €), no al "
                                    "precio objetivo (59.605 €).")
    assert r.puja.plan[0] == ("Puja recomendada: 60.800 €, la mínima aprobable (el objetivo de 59.605 € no se "
                              "aprobaría sin depender de la autoridad)")
    assert "| ROI base (a puja recomendada 60.800 €) |" in r.informe_markdown
    assert "## 7 · Análisis financiero (a puja recomendada 60.800 €)" in r.informe_markdown


# ─────────────────────────── inviable ───────────────────────────

def test_inviable_fuera_del_limite_es_rojo_y_no_recomienda():
    r = _analizar()
    v = r.decision.veredicto
    assert v.puja_recomendada is None and v.puja_evaluada == 106400.0
    assert v.cabe_en_limite is False and v.condicion is None
    assert r.decision.semaforo == "rojo"
    assert r.decision.razones == ["Inviable con estas condiciones: la puja mínima aprobable (106.400 €) supera "
                                  "el precio máximo económico (67.941 €) y el precio límite absoluto (78.529 €)"]
    assert r.puja.plan[0].startswith("No pujar con estas condiciones")
    assert v.cambios[:2] == [
        "Que el precio máximo económico llegue a 106.400 € (38.459 € más): más valor de salida, menos costes "
        "o un margen exigido menor.",
        "O un valor de subasta de 97.059 € como máximo (un 36 % menos que el actual): con él, la puja mínima "
        "aprobable quedaría dentro del precio máximo."]


def test_inviable_dentro_del_limite_es_naranja_con_condicion():
    r = _analizar("no")
    v, d = r.decision.veredicto, r.decision
    assert v.cabe_en_limite is True and d.semaforo == "naranja"
    assert v.condicion == ("Inviable con estas condiciones: la puja mínima aprobable (76.000 €) supera el precio "
                           "máximo económico (67.941 €) y cabe en el límite absoluto (78.529 €); solo se "
                           "plantearía aceptando por escrito un margen menor que el que exige el perfil")
    assert v.condicion in d.condiciones and "naranja" in d.techos_aplicados
    assert any(x.startswith("Inviable con estas condiciones") and x.endswith("⇒ techo Naranja con condición")
               for x in d.razones)
    assert v.puja_recomendada is None
    # La deuda no informada: el informe dice que informarla podría hacer aprobable una puja.
    assert v.cambios[-1] == ("O que lo debido al ejecutante no supere 67.941 €: una puja que lo cubra, desde el "
                             "40 % del valor de subasta, sería aprobable. Informe la cantidad reclamada si la conoce.")


def test_el_naranja_del_veredicto_es_un_techo_y_nunca_sube_un_rojo():
    p = cargar_defaults().con_overrides({f"semaforo.{c}.ico_min": 99 for c in ("verde", "amarillo", "naranja")})
    r = ejecutar_analisis(_entrada("no"), params=p)
    assert r.decision.veredicto.cabe_en_limite and r.decision.semaforo == "rojo" and not r.decision.vetos


def test_lejos_del_limite_es_rojo_aunque_la_aprobacion_sea_discrecional():
    """Lo que separa rojo de naranja es P_límite, no la franja legal."""
    r = _analizar("no", **POSTERIOR, valor_subasta=300000.0)
    v = r.decision.veredicto
    assert v.aprobacion == "discrecional" and not v.cabe_en_limite and r.decision.semaforo == "rojo"


# ─────────────────── segunda línea: qué pasaría a P_max ───────────────────

def test_segunda_linea_no_aprobable_bajo_el_suelo_de_la_vivienda_habitual():
    v = _analizar().decision.veredicto
    assert v.aprobacion == "no_aprobable"
    assert v.aprobacion_texto == ("No aprobable: el precio máximo económico (67.941 €) queda por debajo del suelo "
                                  "de la vivienda habitual del ejecutado (91.200 €, 60 %), y la ley no aprueba el "
                                  "remate por debajo de esa cifra en ningún caso. No consta si es la vivienda "
                                  "habitual: se asume que sí.")


def test_segunda_linea_vivienda_habitual_entre_suelo_y_umbral_solo_si_cubre_la_deuda():
    """En la vivienda habitual no hay discrecionalidad (LEC 670.3, último párrafo)."""
    r = _analizar("si", **POSTERIOR, valor_subasta=100000.0)
    v = r.decision.veredicto
    assert v.estado == "inviable" and v.aprobacion == "solo_si_cubre_deuda"
    assert v.aprobacion_texto.startswith("Aprobable solo si cubre la deuda: con una puja de hasta el precio "
                                         "máximo económico (69.202 €)")
    assert "nunca por debajo del suelo (60.000 €, 60 %)" in v.aprobacion_texto
    assert "decisión" not in v.aprobacion_texto


def test_segunda_linea_discrecional_del_letrado_y_de_la_mesa_de_la_aeat():
    letrado = _analizar("no").decision.veredicto
    assert letrado.aprobacion == "discrecional"
    assert letrado.aprobacion_texto == ("Aprobación discrecional: una puja de hasta el precio máximo económico "
                                        "(67.941 €) quedaría a decisión del letrado de la Administración de "
                                        "Justicia, que puede no aprobar el remate.")
    aeat = _analizar(procedimiento="aeat").decision.veredicto
    assert aeat.aprobacion_texto == ("Aprobación discrecional: una puja de hasta el precio máximo económico "
                                     "(68.194 €) quedaría a decisión de la Mesa de la subasta, que puede no aprobar "
                                     "el remate. Por debajo del 50 % del valor de subasta no hay precio mínimo legal.")


def test_la_segunda_linea_no_cambia_el_veredicto_ni_el_semaforo():
    """El mismo §19 con VH «sí» y supuesta: misma segunda línea salvo el supuesto, mismo resultado."""
    a, b = _analizar().decision, _analizar("si").decision
    assert (a.semaforo, a.veredicto.estado, a.veredicto.aprobacion) == (b.semaforo, b.veredicto.estado,
                                                                       b.veredicto.aprobacion)


# ─────────────────── vivienda habitual y cantidad reclamada ───────────────────

def test_vivienda_habitual_no_consta_da_la_alternativa():
    v = _analizar().decision.veredicto
    assert v.puja_minima_sin_vivienda == 76000.0
    assert v.alternativa_vivienda == ("Si no es la vivienda habitual del ejecutado, la puja mínima aprobable sería "
                                      "de 76.000 € (50 % del valor de subasta), también por encima del precio "
                                      "máximo económico (67.941 €).")
    assert v.alternativa_vivienda in _analizar().informe_markdown
    # Régimen anterior: la alternativa hay que superarla (+1 €).
    assert _analizar(**ANTERIOR).decision.veredicto.puja_minima_sin_vivienda == 76001.0


@pytest.mark.parametrize("vivienda", ["si", "no"])
def test_vivienda_habitual_conocida_no_da_alternativa(vivienda):
    v = _analizar(vivienda).decision.veredicto
    assert v.puja_minima_sin_vivienda is None and v.alternativa_vivienda is None


def test_el_suelo_del_40_solo_si_se_informa_la_cantidad_reclamada():
    sin = _analizar("no", **POSTERIOR).decision.veredicto
    con = _analizar("no", **POSTERIOR, cantidad_reclamada=60000.0).decision.veredicto
    assert sin.puja_minima_efectiva == 76000.0 and con.puja_minima_efectiva == 60800.0


# ─────────────────────────── sin umbral ───────────────────────────

@pytest.mark.parametrize("subasta", [{"procedimiento": "concursal"}, {"procedimiento": "notarial"},
                                     {"procedimiento": "no_aplica"}])
def test_sin_umbral_la_recomendacion_es_la_economica(subasta):
    r = _analizar(**subasta)
    v = r.decision.veredicto
    assert v.estado == "sin_umbral" and v.puja_recomendada == r.decision.precios.p_objetivo
    assert v.puja_minima_efectiva is None and v.condicion is None
    assert "| **Puja mínima aprobable** |" not in r.informe_markdown
    assert "**Veredicto: sin puja mínima aprobable en la norma.**" in r.informe_markdown


# ─────────────────────────── fronteras ───────────────────────────

def _escalera(p_max: float, p_limite: float) -> EscaleraPrecios:
    return EscaleraPrecios(p_ideal=p_max * 0.7, p_objetivo=p_max * 0.85, p_max=p_max, p_limite=p_limite,
                           detalle={}, tramos_fiscales={})


def test_frontera_minima_igual_a_p_max_es_viable_e_igual_a_p_limite_cabe():
    params = cargar_defaults()
    inp = _entrada("no", **POSTERIOR)
    r = procedimiento.calcular(inp, params)                      # mínima 76.000 (50 %)
    assert procedimiento.veredicto_puja(inp, params, r, _escalera(76000.0, 90000.0)).estado == "viable"
    v = procedimiento.veredicto_puja(inp, params, r, _escalera(75999.0, 76000.0))
    assert v.estado == "inviable" and v.cabe_en_limite is True
    assert procedimiento.veredicto_puja(inp, params, r, _escalera(75998.0, 75999.0)).cabe_en_limite is False


def test_frontera_regimen_anterior_igualar_el_50_no_basta():
    params = cargar_defaults()
    inp = _entrada("no", **ANTERIOR)
    r = procedimiento.calcular(inp, params)
    assert procedimiento.veredicto_puja(inp, params, r, _escalera(76000.0, 90000.0)).estado == "inviable"
    assert procedimiento.veredicto_puja(inp, params, r, _escalera(76001.0, 90000.0)).estado == "viable"


def test_con_escalera_degenerada_no_hay_veredicto():
    r = ejecutar_analisis(entrada_caso_19(),
                          params=cargar_defaults().con_overrides({"capital.coste_capital_anual": 0.31}))
    assert r.decision.precios.degenerada and r.decision.veredicto is None


# ─────────────────────────── informe y contrato ───────────────────────────

def test_el_informe_muestra_el_veredicto_y_las_tres_cifras():
    md = _analizar().informe_markdown
    cabeza = md[:md.index("| Métrica")]
    assert "**Veredicto: inviable con estas condiciones.**\n\n**No aprobable:** el precio máximo" in cabeza
    assert ("Precio máximo económico 67.941 € · puja mínima aprobable 106.400 € · aprobación segura "
            "106.400 €.") in cabeza
    assert "Qué tendría que cambiar:\n- Que el precio máximo económico llegue a 106.400 €" in cabeza
    for fila in ("| **Precio máximo económico** | 67.941 € |", "| **Puja mínima aprobable** | 106.400 € |",
                 "| Puja de aprobación segura | 106.400 € |", "| **Veredicto** | Inviable con estas condiciones |",
                 "| ROI base (a puja mínima aprobable 106.400 €) |"):
        assert fila in md, fila


def test_determinista():
    assert _analizar().decision.veredicto == _analizar().decision.veredicto


def test_un_resultado_anterior_a_la_fase_se_lee_sin_veredicto():
    d = _analizar().decision.model_dump(mode="json")
    d.pop("veredicto")
    assert DecisionFinal.model_validate(d).veredicto is None

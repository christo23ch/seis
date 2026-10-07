"""Fase 5J-2b — depósito, táctica de puja y plazo reales (ADR-0024, ADR-0025, ADR-0026).

Esta fase CAMBIA CIFRAS, con la tabla antes/después aprobada por el responsable:

1. El depósito del plan de puja, del §2 y del checklist sale del régimen del procedimiento
   (parámetros T3 de la 5J-1), no del porcentaje del alta. Régimen judicial sin fecha de
   inicio ⇒ el desfavorable (20 %), con aviso.
2. La táctica de M13 depende de la forma de puja del régimen (contrastada con el BOE):
   pujas secretas sin prórroga en el judicial de la LO 1/2025, visibles con prórroga en el
   anterior y en la AEAT, presencial en la TGSS.
3. El plazo de la operación suma los meses de inmovilización entre el cierre y la posesión
   (parámetro T3, al plazo legal máximo), con su tenencia y su coste de capital. Sin plazo
   legal, 2,5 meses: estimación prudente, sin base legal. Régimen judicial sin fecha de
   inicio ⇒ el plazo más largo de los dos regímenes.
"""
from __future__ import annotations

import pytest

from app.engine import procedimiento
from app.engine.contracts import AnalisisInput, ProcedimientoResultado
from app.engine.modules import m06_costes, m13_puja
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import cargar_catalogo, ejecutar_analisis
from tests.test_golden_caso19 import entrada_caso_19

VT = 152000.0
POSTERIOR = {"procedimiento": "judicial", "regimen_judicial": "posterior"}
ANTERIOR = {"procedimiento": "judicial", "regimen_judicial": "anterior"}


def _entrada(**subasta) -> AnalisisInput:
    base = entrada_caso_19()
    return base.model_copy(update={"subasta": base.subasta.model_copy(update=subasta)})


def _analizar(params=None, **subasta):
    return ejecutar_analisis(_entrada(**subasta), params=params)


def _deposito(r) -> str:
    return next(x for x in r.puja.plan if x.startswith("Depósito requerido:"))


# ─────────────────────────── plazo (ADR-0026) ───────────────────────────

@pytest.mark.parametrize("subasta,meses,sin_base", [
    ({}, 2.5, False),                                   # §19: judicial sin fecha ⇒ el más largo
    (POSTERIOR, 1.8, False),
    (ANTERIOR, 2.5, False),
    ({"procedimiento": "aeat"}, 1.7, False),
    ({"procedimiento": "tgss"}, 0.3, False),
    ({"procedimiento": "notarial"}, 1.2, False),
    ({"procedimiento": "extrajudicial"}, 2.5, True),
    ({"procedimiento": "concursal"}, 2.5, True),
    ({"procedimiento": "no_aplica"}, 2.5, True),
])
def test_el_plazo_suma_la_inmovilizacion_del_procedimiento(subasta, meses, sin_base):
    r = _analizar(**subasta)
    d, c = r.costes.plazo_desglose, r.costes
    assert d["inmovilizacion"] == meses == r.procedimiento.meses_inmovilizacion_aplicados
    assert r.procedimiento.meses_inmovilizacion_asumidos is sin_base
    assert c.plazo_meses_p50 == d["ocupacion"] + d["obra"] + d["comercializacion"] + meses
    assert c.plazo_meses_p80 == round(c.plazo_meses_p50 * d["multiplicador_p80"], 1)      # M06 redondea el P80


def test_la_inmovilizacion_genera_tenencia_y_coste_de_capital():
    r = _analizar()
    c, e = r.costes, r.decision.precios
    assert c.desglose_p50["tenencia"] == pytest.approx(c.tenencia_mensual * c.plazo_meses_p50)
    assert e.detalle["coste_capital"] == pytest.approx(
        0.015 * e.detalle["capital_propio"] * c.plazo_meses_p80 / 12, abs=0.01)


def test_mas_inmovilizacion_mas_coste_y_menos_precio():
    corto, largo = _analizar(**POSTERIOR), _analizar(**ANTERIOR)        # 1,8 frente a 2,5 meses
    assert largo.costes.desglose_p50["tenencia"] - corto.costes.desglose_p50["tenencia"] == \
        pytest.approx(largo.costes.tenencia_mensual * 0.7)
    for campo in ("p_ideal", "p_objetivo", "p_max", "p_limite"):
        assert getattr(largo.decision.precios, campo) < getattr(corto.decision.precios, campo), campo
    assert largo.decision.precios.detalle["coste_capital"] > corto.decision.precios.detalle["coste_capital"]
    assert largo.rentabilidad.tir_anual < corto.rentabilidad.tir_anual


def test_mismos_meses_mismas_cifras_aunque_cambie_el_procedimiento():
    """Lo que mueve las cifras es el plazo: con los mismos meses, la escalera y la
    rentabilidad coinciden; cambian el plan de puja y los avisos."""
    base = _analizar()                                   # 2,5: régimen judicial más largo
    for subasta in (ANTERIOR, {"procedimiento": "concursal"}, {"procedimiento": "no_aplica"}):
        otro = _analizar(**subasta)
        assert otro.decision.precios == base.decision.precios, subasta
        assert otro.rentabilidad == base.rentabilidad, subasta
        assert otro.costes == base.costes, subasta


def test_los_meses_son_parametros_t3():
    p = cargar_defaults().con_overrides({
        "procedimiento.regimenes.aeat.meses_inmovilizacion.valor": 3.0,
        "procedimiento.meses_inmovilizacion_si_no_consta.valor": 4.0})
    assert _analizar(p, procedimiento="aeat").costes.plazo_desglose["inmovilizacion"] == 3.0
    assert _analizar(p, procedimiento="concursal").costes.plazo_desglose["inmovilizacion"] == 4.0
    # Sin fecha de inicio manda el mayor de los dos regímenes judiciales, no el «si no consta».
    assert _analizar(p).costes.plazo_desglose["inmovilizacion"] == 2.5


def test_sin_meses_m06_no_suma_nada():
    """Llamada directa sin el argumento nuevo: el plazo es el de antes de la fase."""
    r = _analizar()
    c = m06_costes.ejecutar(entrada_caso_19(), cargar_defaults(), {}, r.reforma, r.valoracion,
                            r.ici, r.riesgos.banda)
    assert c.plazo_desglose["inmovilizacion"] == 0.0
    assert c.plazo_meses_p50 == r.costes.plazo_meses_p50 - 2.5


# ─────────────────────── avisos del plazo ───────────────────────

def test_sin_plazo_legal_el_aviso_dice_que_no_tiene_base_legal():
    for subasta in ({"procedimiento": "no_aplica"}, {"procedimiento": "extrajudicial"}):
        avisos = _analizar(**subasta).procedimiento.avisos
        assert any("2,5 meses" in a and "estimación prudente, sin base legal" in a for a in avisos), subasta


def test_sin_fecha_de_inicio_el_aviso_explica_el_plazo_mas_largo():
    r = _analizar()
    assert ("Por no constar la fecha de inicio, el plazo de la operación suma 2,5 meses de cierre y "
            "pago, los del régimen judicial más largo (con la LO 1/2025 serían 1,8).") in r.procedimiento.avisos
    assert ("| Inmovilización estimada del depósito | 2,5 meses (régimen judicial más largo: no consta "
            "la fecha de inicio) |") in r.informe_markdown


def test_con_fecha_de_inicio_no_hay_aviso_de_plazo():
    for subasta in (POSTERIOR, ANTERIOR):
        r = _analizar(**subasta)
        assert not any("plazo de la operación suma" in a for a in r.procedimiento.avisos), subasta
        assert "meses (plazo legal máximo) |" in r.informe_markdown


# ─────────────────────────── depósito (ADR-0024) ───────────────────────────

@pytest.mark.parametrize("subasta,linea", [
    ({}, "Depósito requerido: 30.400 € (20 % del valor de subasta); supuesto desfavorable: no consta "
         "cuándo se inició el procedimiento judicial (si fue antes del 3-4-2025, es menor)"),
    (POSTERIOR, "Depósito requerido: 30.400 € (20 % del valor de subasta)"),
    (ANTERIOR, "Depósito requerido: 7.600 € (5 % del valor de subasta)"),
    ({"procedimiento": "tgss"}, "Depósito requerido: 38.000 € (25 % del valor de subasta)"),
    ({"procedimiento": "extrajudicial"},
     "Depósito requerido: no consta en la norma para este procedimiento: confírmelo en el edicto"),
    ({"procedimiento": "no_aplica"}, "Depósito requerido: según las condiciones del vendedor (venta no reglada)"),
])
def test_el_deposito_del_plan_sale_del_regimen(subasta, linea):
    assert _deposito(_analizar(**subasta)) == linea


def test_el_minimo_legal_se_declara():
    r = _analizar(valor_subasta=3000.0, **POSTERIOR)
    assert _deposito(r) == "Depósito requerido: 1.000 € (20 % del valor de subasta, con el mínimo legal)"


def test_el_porcentaje_del_alta_no_cambia_el_deposito_y_se_avisa():
    a, b = _analizar(deposito_pct=0.05, **POSTERIOR), _analizar(deposito_pct=0.10, **POSTERIOR)
    assert _deposito(a) == _deposito(b)
    assert any("no coincide con el que fija la norma" in x for x in b.procedimiento.avisos)


def test_el_informe_y_el_checklist_usan_el_deposito_legal():
    r = _analizar()
    assert "depósito 30.400 € (20 % del valor de subasta); supuesto desfavorable" in r.informe_markdown
    item = next(c for c in r.checklist if c.texto == "Depósito disponible y transferido en plazo")
    assert item.detalle == "30.400 €"
    item = next(c for c in _analizar(procedimiento="extrajudicial").checklist
                if c.texto == "Depósito disponible y transferido en plazo")
    assert item.detalle == "No consta en la norma"


def test_en_venta_no_reglada_el_checklist_remite_al_vendedor():
    item = next(c for c in _analizar(procedimiento="no_aplica").checklist
                if c.texto == "Depósito disponible y transferido en plazo")
    assert item.detalle == "Según las condiciones del vendedor"


def test_el_informe_escribe_el_plazo_con_su_decimal():
    """Revisión de la fase: `:.0f` redondeaba 15,5 a 16 (a par) y 14,5 a 14."""
    md = _analizar().informe_markdown
    assert "Plazo total 15,5 m (P50) / 21,7 m (P80)." in md
    assert "| 15,5 m |" in md and "| 16 m |" not in md
    md = _analizar(procedimiento="tgss").informe_markdown          # 13 + 0,3
    assert "Plazo total 13,3 m (P50) / 18,6 m (P80)." in md


def test_la_regla_sem_ejec_01_dice_el_deposito_segun_el_regimen():
    regla = next(r for r in cargar_catalogo()[0] if r["codigo"] == "SEM-EJEC-01")
    assert regla["version"] == "2026.10.07"           # 2026.10 en la 5J-2b; la 5J-3 añade la cesión
    texto = regla["efecto"]["condicion"]
    assert "depósito según el régimen del procedimiento (20 % con la LO 1/2025; 5 % si se inició " \
           "antes del 3-4-2025)" in texto
    assert "5%" not in texto


# ─────────────────────── táctica de puja (ADR-0025) ───────────────────────

def _tacticas(r) -> list[str]:
    return r.puja.plan[:r.puja.plan.index(_deposito(r))]


def test_judicial_lo_1_2025_pujas_secretas_sin_prorroga():
    t = _tacticas(_analizar(**POSTERIOR))
    assert t[0].startswith("Decidir la cifra antes de abrir la puja, entre objetivo ")
    assert t[1].startswith("Pujas secretas y cierre improrrogable (LO 1/2025)")
    assert "antes del 3-4-2025" not in t[1]
    assert t[2].startswith("No apurar el cierre")
    assert not any("sniping" in x or "tramo mínimo" in x for x in t)


def test_sin_fecha_de_inicio_la_tactica_vale_para_los_dos_regimenes():
    t = _tacticas(_analizar())
    assert t[1].endswith("si el procedimiento se inició antes del 3-4-2025, las pujas se ven y el "
                         "cierre se prorroga, y esta táctica sigue siendo válida")


@pytest.mark.parametrize("subasta", [ANTERIOR, {"procedimiento": "aeat"}])
def test_pujas_visibles_con_prorroga_mantienen_la_tactica_anterior(subasta):
    t = _tacticas(_analizar(**subasta))
    assert t[0].startswith("Cargar límites en la interfaz antes de abrir la puja: objetivo ")
    assert t[1] == "Pujar siempre el tramo mínimo; sin pujas psicológicas redondas"
    assert t[2].startswith("Entrar tarde con límites precargados")


def test_notarial_pujas_visibles_sin_prorroga_fijada():
    t = _tacticas(_analizar(procedimiento="notarial"))
    assert t[2].startswith("Las pujas se ven, pero la norma no fija si el cierre se prorroga")


def test_tgss_presencial():
    t = _tacticas(_analizar(procedimiento="tgss"))
    assert t[0].startswith("Llevar decididas la cifra del sobre cerrado y el límite de la puja a viva voz")
    assert "a viva voz" in t[1] and "2 % del tipo" in t[1]


@pytest.mark.parametrize("subasta", [{"procedimiento": "extrajudicial"}, {"procedimiento": "concursal"},
                                     {"procedimiento": "no_aplica"}])
def test_sin_forma_de_puja_se_remite_al_edicto(subasta):
    t = _tacticas(_analizar(**subasta))
    assert t[0].startswith("Cargar límites antes de pujar: objetivo ")
    assert t[1].startswith("No consta cómo se puja en este procedimiento")


def test_con_escalera_degenerada_no_hay_tactica_aunque_haya_forma_de_puja():
    r = ejecutar_analisis(_entrada(**POSTERIOR),
                          params=cargar_defaults().con_overrides({"capital.coste_capital_anual": 0.31}))
    assert r.decision.precios.degenerada
    assert r.puja.plan[0].startswith("No cargar límites ni pujar")
    assert not any(x.startswith(("Decidir la cifra", "Pujas secretas")) for x in r.puja.plan)


def test_m13_sin_procedimiento_mantiene_el_plan_anterior():
    """Llamada directa sin el argumento nuevo: táctica de pujas visibles y el 5 % del alta."""
    r = _analizar()
    p = m13_puja.ejecutar(entrada_caso_19(), cargar_defaults(), {}, r.decision.precios, r.valoracion.vm)
    assert p.plan[0].startswith("Cargar límites en la interfaz antes de abrir la puja")
    assert "Depósito requerido: 7.600 € (5 % del valor de subasta)" in p.plan


# ─────────────── forma de puja en la base legal (contrastada con el BOE) ───────────────

@pytest.mark.parametrize("subasta,texto,estado", [
    (POSTERIOR, "pujas secretas; cierre improrrogable", "confirmado"),
    (ANTERIOR, "pujas visibles; el cierre se prorroga tras la última puja", "confirmado"),
    ({"procedimiento": "aeat"}, "pujas visibles; el cierre se prorroga tras la última puja", "confirmado"),
    ({"procedimiento": "tgss"}, "presencial: sobre cerrado y pujas a viva voz", "confirmado"),
    ({"procedimiento": "notarial"}, "pujas visibles; la norma no fija la prórroga del cierre", "confirmado"),
    ({"procedimiento": "extrajudicial"}, None, "sin_confirmar"),
    ({"procedimiento": "concursal"}, None, "sin_confirmar"),
])
def test_la_forma_de_puja_figura_en_los_datos_legales(subasta, texto, estado):
    r = _analizar(**subasta)
    dato = next(d for d in r.procedimiento.datos_legales if d.dato == "Forma de puja")
    assert (dato.texto, dato.estado, dato.valor) == (texto, estado, None)
    etiqueta = "confirmado" if estado == "confirmado" else "sin confirmar"
    prefijo = f"- Forma de puja ({texto})" if texto else "- Forma de puja:"
    linea = next(x for x in r.informe_markdown.splitlines() if x.startswith("- Forma de puja"))
    assert linea.startswith(prefijo) and linea.endswith(f"({etiqueta})")


def test_el_aviso_de_datos_sin_confirmar_no_cita_una_forma_que_no_consta():
    r = _analizar(procedimiento="concursal")
    assert not any("forma de puja" in a for a in r.procedimiento.avisos)


# ─────────────────────────── compatibilidad ───────────────────────────

def test_un_resultado_anterior_a_la_fase_se_lee_y_se_redacta_igual():
    actual = procedimiento.calcular(entrada_caso_19(), cargar_defaults()).model_dump()
    for campo in ("meses_inmovilizacion_aplicados", "meses_inmovilizacion_asumidos", "forma_puja"):
        actual.pop(campo)
    for dato in actual["datos_legales"]:
        dato.pop("texto")
    antiguo = ProcedimientoResultado.model_validate(actual)
    assert antiguo.meses_inmovilizacion_aplicados is None and antiguo.forma_puja is None
    assert ("| Inmovilización estimada del depósito | 1,8 meses (plazo legal máximo) |"
            in procedimiento.seccion_informe(antiguo))


def test_es_determinista():
    a, b = _analizar(), _analizar()
    assert a.model_dump() == b.model_dump()

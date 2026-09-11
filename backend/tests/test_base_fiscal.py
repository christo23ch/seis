"""La base imponible del ITP es max(valor de referencia, declarado, puja) — no la puja.

Hallazgo del 2026-09-10, recorriendo una subasta real de la AEAT: SEIS aplicaba el
tipo sobre el precio de remate. En una subasta —donde el atractivo es rematar por
debajo del valor— eso **infraestima el impuesto justo en las operaciones más
atractivas**. Corregido en `app/engine/fiscal.py`; estos tests cubren la corrección.

LO QUE ESTOS TESTS **NO** CUBREN, y conviene saberlo antes de confiarse (ADR-0014):

- No comprueban que el valor de referencia aportado sea el correcto del inmueble ni
  del ejercicio. Es dato de entrada; el motor no lo verifica ni lo busca (eso es la
  Fase 17-C).
- No cubren el AJD: la base mínima se aplica solo al tipo de TPO. Si alguien borrase
  esa restricción para aplicarla también al AJD, estos tests seguirían en verde.
- No cubren las CCAA con reducciones o tipos especiales sobre el valor de referencia.
"""
from __future__ import annotations

import pytest

from app.engine import fiscal
from app.engine.contracts import CostesInput, CostesResultado
from app.engine.modules import m11_rentabilidad, m12_decision
from app.engine.modules.m11_rentabilidad import inversion
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base

TIPO = 0.06


def _costes(c_v: float = 0.10, base_minima: float = 0.0, tipo_base: float = 0.0,
            c_f: float = 0.0) -> CostesResultado:
    return CostesResultado(
        c_v=c_v, c_v_desglose={}, c_f_p50=c_f, c_f_p80=c_f, desglose_p50={}, desglose_p80={},
        contingencia_pct=0.0, tenencia_mensual=0.0, plazo_meses_p50=0.0, plazo_meses_p80=0.0,
        regimen_fiscal="itp", tipo_impositivo=tipo_base, base_fiscal_minima=base_minima,
        tipo_base_minima=tipo_base)


# ───────────────────────── prelación de la base ─────────────────────────
def test_manda_el_mayor_de_los_dos_datos_disponibles():
    assert fiscal.base_minima(80000, 60000) == (80000.0, fiscal.POR_REFERENCIA)
    assert fiscal.base_minima(60000, 80000) == (80000.0, fiscal.POR_DECLARADO)


def test_sin_ningun_dato_la_base_es_la_puja_y_se_declara_como_tal():
    """No se estima un valor de referencia: se dice que la base es la puja."""
    assert fiscal.base_minima(None, None) == (0.0, fiscal.POR_PRECIO)


# ───────── el impuesto se calcula sobre el mayor, no sobre la puja ─────────
def test_pujar_por_debajo_de_la_base_no_abarata_el_impuesto():
    """El corazón del fallo: 100.000 de base, remate de 40.000, tipo 6 %.

    Antes: 40.000·6 % = 2.400 €. Correcto: 100.000·6 % = 6.000 €. 3.600 € de
    diferencia en una operación de 40.000 — no es un decimal.
    """
    c = _costes(c_v=TIPO, base_minima=100000, tipo_base=TIPO)
    assert fiscal.sobrecoste(40000, c) == pytest.approx(3600.0)
    assert inversion(40000, c, 0.0) == pytest.approx(40000 + 6000.0)


def test_por_encima_de_la_base_el_impuesto_vuelve_a_ser_el_del_precio():
    c = _costes(c_v=TIPO, base_minima=100000, tipo_base=TIPO)
    assert fiscal.sobrecoste(120000, c) == 0.0
    assert inversion(120000, c, 0.0) == pytest.approx(120000 * 1.06)


def test_en_la_frontera_exacta_los_dos_tramos_coinciden():
    c = _costes(c_v=TIPO, base_minima=100000, tipo_base=TIPO)
    assert fiscal.sobrecoste(100000, c) == 0.0


# ── propiedad de seguridad: sin base, todo se comporta como antes ──
def test_sin_base_minima_el_sobrecoste_es_cero_en_todo_el_dominio():
    """Es lo que hace revisable el cambio: un análisis sin valor de referencia
    devuelve exactamente el mismo número que antes de la corrección."""
    c = _costes(c_v=TIPO)
    for p in (0.0, 1.0, 5000.0, 250000.0):
        assert fiscal.sobrecoste(p, c) == 0.0
        assert inversion(p, c, 1000.0) == pytest.approx(p * (1 + TIPO) + 1000.0)


def test_sin_base_minima_la_escalera_usa_la_formula_cerrada_de_siempre():
    c = _costes(c_v=TIPO)
    assert m12_decision._precio_venta(0.25, 125000, 25000, c) == pytest.approx(
        (125000 / 1.25 - 25000) / 1.06)


# ───────── la inversa de I(P) sigue siendo la inversa, con dos tramos ─────────
@pytest.mark.parametrize("vs, base", [
    (125000, 300000),      # solución en el tramo bajo (P < base)
    (900000, 100000),      # solución en el tramo alto (P > base)
    (125000, 0),           # sin base
])
def test_el_precio_de_la_escalera_reproduce_su_propio_margen(vs, base):
    """Invariante que caza un tramo mal elegido: si P sale de la fórmula para
    margen m, recalcular I(P) y aplicarle m tiene que devolver VS."""
    c = _costes(c_v=TIPO, base_minima=base, tipo_base=TIPO if base else 0.0, c_f=25000)
    p = m12_decision._precio_venta(0.25, vs, 25000.0, c)
    assert inversion(p, c, 25000.0) * 1.25 == pytest.approx(vs)


def test_los_dos_tramos_se_recorren_de_verdad():
    """Sin esto, el test anterior podría estar probando el mismo tramo tres veces."""
    c = _costes(c_v=TIPO, base_minima=300000, tipo_base=TIPO, c_f=25000)
    assert m12_decision._precio_venta(0.25, 125000, 25000.0, c) < 300000
    assert m12_decision._precio_venta(0.25, 900000, 25000.0, c) > 300000


# ─────────────────────── extremo a extremo por el motor ───────────────────────
def _resultado(**costes_extra):
    return ejecutar_analisis(entrada_base(
        costes=CostesInput(itp_tipo_override=TIPO, **costes_extra)))


def test_un_valor_de_referencia_alto_encarece_la_operacion_y_baja_lo_que_se_puede_pujar():
    sin_vr = _resultado()
    con_vr = _resultado(valor_referencia_catastral=300000)

    assert sin_vr.decision.precios.p_objetivo > con_vr.decision.precios.p_objetivo
    assert sin_vr.decision.precios.p_max > con_vr.decision.precios.p_max
    assert sin_vr.decision.precios.p_limite > con_vr.decision.precios.p_limite

    # Y el motivo, para que no se lea como un número que bajó porque sí: al mismo
    # precio de remate, la operación con valor de referencia cuesta más impuesto.
    # (El coste TOTAL de los escenarios no cambia apenas: la escalera persigue un
    # margen fijo, así que baja el precio hasta dejar I(P) donde estaba. Es el precio
    # que se puede pujar lo que cae, que es justo la decisión que toma el cliente.)
    p = 80000.0
    impuesto_extra = fiscal.inversion(p, con_vr.costes, 0.0) - fiscal.inversion(p, sin_vr.costes, 0.0)
    assert impuesto_extra == pytest.approx(TIPO * (300000 - p))


def test_el_regimen_de_iva_no_usa_la_base_minima():
    """En IVA la base es el precio convenido. La restricción es deliberada y va
    declarada en app/engine/fiscal.py; este test la fija."""
    res = ejecutar_analisis(entrada_base(costes=CostesInput(
        regimen_fiscal="iva", valor_referencia_catastral=300000)))
    assert res.costes.tipo_base_minima == 0.0
    assert fiscal.sobrecoste(1.0, res.costes) == 0.0


def test_el_informe_dice_que_el_impuesto_es_un_minimo_cuando_no_hay_valor_de_referencia():
    """La carencia no puede quedarse dentro del motor: el cliente lee el informe."""
    res = _resultado()
    assert res.costes.base_fiscal_origen == fiscal.POR_PRECIO
    assert "MÍNIMO" in res.informe_markdown
    assert "no consta valor de referencia" in res.informe_markdown
    fiscal_item = next(c for c in res.checklist if c.texto.startswith("Tributación"))
    assert fiscal_item.estado == "pendiente"


def test_con_valor_de_referencia_el_informe_declara_la_base_y_el_item_deja_de_estar_pendiente():
    res = _resultado(valor_referencia_catastral=300000)
    assert res.costes.base_fiscal_origen == fiscal.POR_REFERENCIA
    assert "Base imponible del impuesto: 300.000" in res.informe_markdown.replace(" ", ".")
    fiscal_item = next(c for c in res.checklist if c.texto.startswith("Tributación"))
    assert fiscal_item.estado == "ok"


def _costes_con_desglose(base_minima: float = 0.0) -> CostesResultado:
    """Como _costes, pero con el desglose que `evaluar` necesita para el calendario."""
    d = {"reforma": 30000.0, "ocupacion_desalojo": 3000.0, "atrasos_comunidad_ibi": 1500.0,
         "adquisicion_fija": 2000.0, "tenencia": 4000.0, "comercializacion": 5000.0,
         "contingencia": 2500.0, "cargas_subsistentes": 0.0, "plusvalia_municipal": 0.0}
    c = _costes(c_v=TIPO, base_minima=base_minima, tipo_base=TIPO if base_minima else 0.0,
                c_f=sum(d.values()))
    return c.model_copy(update={"desglose_p50": d, "desglose_p80": d, "plazo_meses_p50": 18.0})


def test_el_impuesto_extra_sale_del_bolsillo_en_el_mes_0_y_la_tir_lo_nota():
    """El sobrecoste no es solo un número del total: se paga con la adquisición.

    Si se colase prorrateado —o se olvidase— en el calendario de flujos, el total
    cuadraría y la TIR saldría mejor de lo que realmente es. Las dos operaciones se
    evalúan **al mismo precio** para que la única diferencia sea el impuesto.
    """
    p, params = 80000.0, cargar_defaults()
    inp = entrada_base()
    sin_vr, con_vr = _costes_con_desglose(), _costes_con_desglose(300000)
    escenarios = [m11_rentabilidad.ParametrosEscenario(
        "base", 1.0, vs=200000.0, c_f=sin_vr.c_f_p50, plazo_meses=18.0,
        contingencia_incluida=sin_vr.desglose_p50["contingencia"])]

    r_sin = m11_rentabilidad.evaluar(p, escenarios, sin_vr, inp, params)
    r_con = m11_rentabilidad.evaluar(p, escenarios, con_vr, inp, params)

    assert r_con.inversion_total == pytest.approx(r_sin.inversion_total + TIPO * (300000 - p))
    assert r_con.tir_anual < r_sin.tir_anual

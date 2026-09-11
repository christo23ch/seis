"""Unidades del algoritmo de precios (§9), δ_v (§9.4) y finanzas (M11)."""
import pytest

from app.engine.contracts import CostesResultado, ICIResultado, RentistaInput
from app.engine.modules.m11_rentabilidad import _roi_anualizado, _tir_anual
from app.engine.modules.m12_decision import (_precio_venta, calcular_delta_v,
                                             margen_seguridad)
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base


def _costes(c_v: float, base_minima: float = 0.0, tipo_base: float = 0.0) -> CostesResultado:
    """C_F y desgloses son irrelevantes aquí: estas fórmulas solo leen c_v y la base."""
    return CostesResultado(
        c_v=c_v, c_v_desglose={}, c_f_p50=0.0, c_f_p80=0.0, desglose_p50={}, desglose_p80={},
        contingencia_pct=0.0, tenencia_mensual=0.0, plazo_meses_p50=0.0, plazo_meses_p80=0.0,
        regimen_fiscal="itp", tipo_impositivo=tipo_base, base_fiscal_minima=base_minima,
        tipo_base_minima=tipo_base)


def _ici(delta_pp=0.0):
    return ICIResultado(ici=80, desglose={}, carencias=[], penalizaciones=[],
                        efecto_delta_v_pp=delta_pp, efecto_contingencia_pp=0.0,
                        techo_semaforo=None)


def test_formula_precio_venta():
    # P(m=25%, VS=125.000, C_F=25.000, c_v=0) = 125.000/1,25 − 25.000 = 75.000
    assert _precio_venta(0.25, 125000, 25000, _costes(0.0)) == pytest.approx(75000)


def test_delta_v_suma_de_primas():
    p = cargar_defaults()
    # base 2 + mercado(alto) 4 + dispersión(CV 20%) 2,5 + ICI 5 = 13,5%
    assert calcular_delta_v(p, "alto", 0.20, _ici(5.0)) == pytest.approx(0.135)


def test_delta_v_cap_20pct():
    p = cargar_defaults()
    # 2 + 6 (muy_alto) + 4 (CV>25%) + 12 (ICI<25) = 24 ⇒ cap 20%
    assert calcular_delta_v(p, "muy_alto", 0.40, _ici(12.0)) == pytest.approx(0.20)


def test_margen_seguridad():
    # I = 100.000·1,06 + 20.000 = 126.000; VS 180.000 ⇒ MS = 30%
    assert margen_seguridad(100000, _costes(0.06), 20000, 180000) == pytest.approx(0.30)


def test_roi_anualizado_identidad_12m():
    assert _roi_anualizado(0.25, 12) == pytest.approx(0.25)


def test_tir_flujo_simple():
    # −100 hoy, +110 en 12 meses ⇒ TIR anual = 10%
    flujos = [-100.0] + [0.0] * 11 + [110.0]
    assert _tir_anual(flujos) == pytest.approx(0.10, abs=0.002)


def test_prima_riesgo_endurece_precios():
    """A mayor RA, m* sube y stress crece ⇒ todos los precios bajan (§9.4)."""
    res_medio = ejecutar_analisis(entrada_base())
    # forzamos riesgo alto añadiendo mercado en corrección profunda y DOM larguísimo
    from app.engine.contracts import ZonaInput, ZonaMacroInput, ZonaMicroInput
    zona_mala = ZonaInput(macro=ZonaMacroInput(tendencia_5a_pct=-5.0, stock_meses=15,
                                               dom_venta_dias=220, dom_alquiler_dias=80,
                                               crecimiento_pobl_5a_pct=-1.0, renta_hogar=20000,
                                               y_zona_pct=6.5),
                          micro=ZonaMicroInput())
    res_alto = ejecutar_analisis(entrada_base(zona=zona_mala))
    assert res_alto.riesgos.ra > res_medio.riesgos.ra
    assert res_alto.decision.precios.p_objetivo < res_medio.decision.precios.p_objetivo
    assert res_alto.decision.precios.p_max < res_medio.decision.precios.p_max


def test_escalera_rentista_monotona():
    res = ejecutar_analisis(entrada_base(
        perfil="rentista",
        rentista=RentistaInput(renta_mensual_estimada=900, vacancia_pct=5,
                               ibi_anual=400, comunidad_mensual=60, seguro_anual=300)))
    p = res.decision.precios
    assert 0 < p.p_ideal < p.p_objetivo < p.p_max
    assert res.rentabilidad.y_neta is not None and res.rentabilidad.y_neta > 0
    assert "y_req_pct" in p.detalle


def test_invariante_orden_escalera_base(base_input):
    p = ejecutar_analisis(base_input).decision.precios
    assert p.p_ideal < p.p_objetivo < p.p_max < p.p_limite

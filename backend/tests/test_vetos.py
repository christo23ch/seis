"""Vetos no compensatorios (§8.4): ninguna virtud compensa un defecto letal."""
from app.engine.contracts import CargaInput, DocumentosInput, FinanciacionInput, OcupacionInput, SubastaInput
from app.engine.pipeline import ejecutar_analisis
from tests.conftest import entrada_base


def _codigos_veto(res):
    return {v.codigo for v in res.decision.vetos}


def test_veto_ocu01_renta_antigua_con_venta():
    res = ejecutar_analisis(entrada_base(ocupacion=OcupacionInput(estado="renta_antigua")))
    assert res.decision.semaforo == "rojo"
    assert "VETO-OCU-01" in _codigos_veto(res)
    # riesgo crítico no mitigable en estrategia de venta ⇒ dominancia ≥ 85
    assert res.riesgos.ra >= 85


def test_veto_fin01_hipoteca_sin_preaprobar():
    res = ejecutar_analisis(entrada_base(
        financiacion=FinanciacionInput(tipo="hipoteca", preaprobada=False, ltv=0.7)))
    assert res.decision.semaforo == "rojo"
    assert "VETO-FIN-01" in _codigos_veto(res)
    v = next(x for x in res.decision.vetos if x.codigo == "VETO-FIN-01")
    assert v.subsanable_con                                  # explica cómo salir del rojo


def test_veto_carga01_cargas_supera_35pct():
    res = ejecutar_analisis(entrada_base(
        cargas=[CargaInput(tipo="hipoteca", importe=70000, es_anterior=True,
                           se_purga=False, verificada=True)]))
    assert res.decision.semaforo == "rojo"
    assert "VETO-CARGA-01" in _codigos_veto(res)


def test_veto_carga02_importe_indeterminado():
    res = ejecutar_analisis(entrada_base(
        cargas=[CargaInput(tipo="embargo", importe=None, es_anterior=True,
                           se_purga=False, verificada=False)]))
    assert "VETO-CARGA-02" in _codigos_veto(res)
    assert res.decision.semaforo == "rojo"


def test_veto_comp01_rojo_competitivo():
    # VT desproporcionado ⇒ P_adj esperado muy por encima de P_max ⇒ RVC < umbral del perfil
    res = ejecutar_analisis(entrada_base(
        subasta=SubastaInput(fuente="judicial_boe", valor_subasta=400000,
                             deposito_pct=0.05, horas_hasta_cierre=200)))
    assert res.puja.rvc < 0.80
    assert "VETO-COMP-01" in _codigos_veto(res)
    assert res.decision.semaforo == "rojo"


def test_veto_inf01_sin_informacion_y_cierre_inminente():
    res = ejecutar_analisis(entrada_base(
        documentos=DocumentosInput(),                        # todo a False
        comparables=[],                                       # ICI se hunde
        subasta=SubastaInput(fuente="judicial_boe", valor_subasta=152000,
                             deposito_pct=0.05, horas_hasta_cierre=24)))
    assert res.ici.ici < 25
    assert "VETO-INF-01" in _codigos_veto(res)
    assert res.decision.semaforo == "rojo"


def test_ocupacion_desconocida_asume_precario_y_techo():
    res = ejecutar_analisis(entrada_base(ocupacion=OcupacionInput(estado="desconocida")))
    assert res.decision.semaforo == "amarillo"               # techo por SEM-OCU-03
    codigos = {r.codigo for r in res.reglas_disparadas}
    assert "SEM-OCU-03" in codigos
    # el coste de desalojo del precario está provisionado (P5)
    assert res.costes.desglose_p50["ocupacion_desalojo"] == 6500

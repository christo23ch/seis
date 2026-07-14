"""Caso dorado (§19 de la especificación): vivienda 82 m², subasta judicial,
VT 152.000 €, estado malo, precario, flip integral, cash.

El motor debe reproducir las magnitudes del documento dentro de tolerancias
de redondeo: es la prueba de regresión fundacional de la suite (P1, §8.3).
"""
import pytest

from app.engine.contracts import (ActivoInput, AnalisisInput, CargaInput,
                                  ComparableInput, CostesInput, DocumentosInput,
                                  FinanciacionInput, OcupacionInput, ReformaInput,
                                  SubastaInput, ZonaInput, ZonaMacroInput,
                                  ZonaMicroInput)
from app.engine.pipeline import ejecutar_analisis


@pytest.fixture(scope="module")
def caso_19() -> AnalisisInput:
    comparables = [ComparableInput(precio_m2=v, estado="reformado", origen="testigo")
                   for v in (2100, 2200, 2250, 2293, 2350, 2420, 2490)]
    return AnalisisInput(
        perfil="flip_integral",
        activo=ActivoInput(tipologia="vivienda", superficie_m2=82,
                           estado_conservacion="malo", anio_construccion=1975,
                           municipio="Ciudad Ejemplo", provincia="Ejemplo", ccaa="ejemplo"),
        subasta=SubastaInput(fuente="judicial_boe", valor_subasta=152000,
                             deposito_pct=0.05, horas_hasta_cierre=200),
        cargas=[],
        ocupacion=OcupacionInput(estado="precario"),
        documentos=DocumentosInput(
            nota_simple=True, nota_simple_dias=10, cert_cargas=True,
            posesion_verificada=False, avaluo=True, fotos_interior_o_visita=False,
            fotos_exterior=True, cert_comunidad=False, recibo_ibi=True,
            ite_cee=False, catastro_conciliado=True),
        comparables=comparables,
        zona=ZonaInput(
            macro=ZonaMacroInput(tendencia_5a_pct=3.0, stock_meses=6, dom_venta_dias=75,
                                 dom_alquiler_dias=25, crecimiento_pobl_5a_pct=0.5,
                                 renta_hogar=32000, y_zona_pct=5.5),
            micro=ZonaMicroInput(transporte=70, seguridad=60, sanidad=65, educacion=60,
                                 comercio=70, zonas_verdes=55, pipeline_urbanistico=55,
                                 potencial_transformacion=60, entorno_construido=65)),
        reforma=ReformaInput(visita_interior=False, k_provincia=1.0),
        costes=CostesInput(itp_tipo_override=0.06),
        financiacion=FinanciacionInput(tipo="cash"),
    )


@pytest.fixture(scope="module")
def resultado(caso_19):
    return ejecutar_analisis(caso_19)


def test_ici_en_banda(resultado):
    # Doc: ICI 62 (banda 60–79 ⇒ +2pp de prudencia, sin techo)
    assert 58 <= resultado.ici.ici <= 68
    assert resultado.ici.techo_semaforo is None
    assert resultado.ici.efecto_delta_v_pp == pytest.approx(2.0)


def test_valoracion(resultado):
    # Doc: VS = 82 × 2.293 ≈ 188.000 €, CV bajo, VM en estado 'malo'
    assert resultado.valoracion.vs == pytest.approx(188026, rel=0.005)
    assert resultado.valoracion.dispersion_cv < 0.10
    assert resultado.valoracion.vm == pytest.approx(188026 * 0.72, rel=0.01)
    assert "tasacion_anomala" not in resultado.valoracion.hechos


def test_icu(resultado):
    # Doc: ICU ≈ 68 (tolerancia por normalizaciones paramétricas)
    assert 60 <= resultado.icu.icu <= 75


def test_riesgos_y_ra(resultado):
    # Doc §19: ocupación 12 (alta) ⇒ dominancia una_alta ⇒ RA = 40 banda medio
    scores = {r.dimension: r.score for r in resultado.riesgos.dimensiones}
    assert scores["ocupacion"] == 12
    assert scores["juridico"] == 6
    assert scores["financiero"] == 2
    assert scores["tecnico"] == 9
    assert scores["liquidez"] == 4
    assert resultado.riesgos.ra == 40
    assert resultado.riesgos.banda == "medio"
    assert resultado.riesgos.dominancia_aplicada == "una_alta"


def test_delta_v_y_vs_prudente(resultado):
    # Doc: δ_v = 2+2+0+2 = 6% ⇒ VS_p ≈ 176.700 €
    assert resultado.delta_v == pytest.approx(0.06, abs=0.001)
    assert resultado.vs_prudente == pytest.approx(176744, rel=0.005)


def test_costes(resultado):
    # Doc: C_F(P50) ≈ 77.460 · C_F(P80) ≈ 86.800 · c_v = 6,4%
    assert resultado.costes.c_v == pytest.approx(0.064, abs=0.0005)
    assert resultado.costes.c_f_p50 == pytest.approx(77460, rel=0.02)
    assert resultado.costes.c_f_p80 == pytest.approx(86800, rel=0.02)
    assert resultado.costes.plazo_meses_p50 == pytest.approx(13, abs=0.5)
    assert resultado.costes.contingencia_pct == pytest.approx(0.10, abs=0.001)
    assert resultado.costes.regimen_fiscal == "itp"


def test_escalera_precios(resultado):
    # Doc §19: ideal 51.100 · objetivo 60.100 · máx 69.100 · límite ~80–84 k
    p = resultado.decision.precios
    assert p.p_ideal == pytest.approx(51100, abs=800)
    assert p.p_objetivo == pytest.approx(60100, abs=800)
    assert p.p_max == pytest.approx(69100, abs=900)
    assert 78000 <= p.p_limite <= 84500
    assert p.p_ideal < p.p_objetivo < p.p_max < p.p_limite
    assert not p.degenerada


def test_rentabilidad(resultado):
    # Doc: ROI 25% base a P_objetivo · ROI anualizado ≈ 23% · pesimista positivo
    r = resultado.rentabilidad
    assert r.roi == pytest.approx(0.25, abs=0.005)
    assert r.roi_anualizado == pytest.approx(0.229, abs=0.015)
    assert 0.15 <= r.tir_anual <= 0.35
    pes = next(e for e in r.escenarios if e.nombre == "pesimista")
    assert pes.beneficio > 0
    assert r.valor_esperado == pytest.approx(34000, rel=0.15)


def test_margen_seguridad(resultado):
    # Doc: MS ≈ 25% de caída de VS soportable a P_objetivo
    assert resultado.decision.margen_seguridad_valor == pytest.approx(0.248, abs=0.02)


def test_puja_y_rvc(resultado):
    # Doc: ratio 42% ⇒ P_adj ≈ 63.800 · RVC ≈ 1,08 alcanzable
    assert resultado.puja.p_adj_esperado == pytest.approx(63840, rel=0.005)
    assert resultado.puja.rvc == pytest.approx(1.08, abs=0.03)
    assert resultado.puja.banda_rvc == "alcanzable"


def test_ico_y_semaforo(resultado):
    # Doc: ICO en banda amarilla (60–74); techo Amarillo por ocupación alta (SEM-OCU-02)
    d = resultado.decision
    assert 60 <= d.ico <= 74
    assert d.semaforo == "amarillo"
    assert "amarillo" in d.techos_aplicados
    assert any("posesoria" in c or "posesión" in c.lower() for c in d.condiciones)
    assert not d.vetos


def test_checklist_bloqueantes(resultado):
    bloq_pend = [c for c in resultado.checklist
                 if c.bloqueante and c.estado == "pendiente"]
    textos = " ".join(c.texto for c in bloq_pend)
    assert "posesoria" in textos or "Situación posesoria" in textos
    assert any("Nota simple" in c.texto for c in bloq_pend)   # 10 días > 5 días


def test_informe_sin_cifras_nuevas(resultado):
    # El informe debe contener las cifras clave del snapshot (regla M14)
    inf = resultado.informe_markdown
    assert "AMARILLO" in inf
    for etiqueta in ("Precio ideal", "Precio objetivo", "Precio máximo", "Precio límite",
                     "Margen de seguridad", "TIR", "Checklist"):
        assert etiqueta in inf
    assert f"{resultado.decision.ico} / 100" in inf


def test_trazabilidad(resultado):
    codigos = {r.codigo for r in resultado.reglas_disparadas}
    assert "SEM-OCU-02" in codigos
    assert "SEM-DOC-01" in codigos
    assert "SEM-EJEC-01" in codigos

"""Fase 5G.4-A — coste de capital como coste de oportunidad: rango, aviso y explicación.

Decisiones del responsable (ADR-0016):
- `capital.coste_capital_anual` es el coste de oportunidad del capital propio.
- Rango admitido 0–0,15, ambos incluidos; fuera de él el valor se rechaza (422).
- Aviso no bloqueante a partir de 0,06.

Con la misma regla, las cotas técnicas que el catálogo ya tenía (ICO, ICI, RA,
margen de seguridad) pasan a ser vinculantes, por simulación y por edición
global. Nada de esto cambia un solo cálculo: la última sección fija los
valores de M11/M12 del caso §19 capturados ANTES de esta fase.
"""
from __future__ import annotations

import json

import pytest

from app import models
from app.core.db import SessionLocal
from app.engine.modules import m14_informe
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from app.parametros import catalogo
from tests.conftest import entrada_base
from tests.test_golden_caso19 import caso_19  # noqa: F401 — fixture reutilizada

CLAVE = "capital.coste_capital_anual"
TEXTO_AVISO = ("Por encima del 6 % la escalera de precios suele degenerar "
               "(umbral medido en el caso de referencia §19: 6,13 %)")
LINEA_CASO19 = ("El coste de capital (1,5 % anual, coste de oportunidad del capital propio) "
                "solo se descuenta del precio límite (§9.1); ROI y TIR no lo incluyen. "
                "Importe aplicado: 3.659 €.")


# ─────────────────────────── helpers ───────────────────────────

@pytest.fixture(scope="module")
def aid(api, headers) -> str:
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _simular(api, headers, aid, overrides):
    return api.post(f"/api/v1/analisis/{aid}/simulaciones",
                    json={"overrides": overrides}, headers=headers)


def _publicar(api, headers, clave, valor):
    return api.put("/api/v1/parametros", headers=headers,
                   json={"clave": clave, "valor": valor, "fuente_legal": "test 5G.4"})


def _contar() -> tuple[int, int, int]:
    db = SessionLocal()
    try:
        return (db.query(models.Simulacion).count(), db.query(models.Parametro).count(),
                db.query(models.Auditoria).count())
    finally:
        db.close()


def _borrar_parametro(clave: str) -> None:
    db = SessionLocal()
    try:
        db.query(models.Parametro).filter_by(clave=clave).delete()
        db.commit()
    finally:
        db.close()


# ─────────────────────────── catálogo ───────────────────────────

def test_catalogo_describe_el_coste_de_oportunidad_con_rango_y_aviso():
    p = catalogo.obtener_parametro(CLAVE)
    assert p.rango == (0.0, 0.15)
    assert p.unidad == "fracción anual (0–1)"
    assert "coste de oportunidad del capital propio" in p.descripcion.lower()
    assert "ROI" in p.advertencia and "TIR" in p.advertencia
    assert "precio límite" in p.impacto
    assert p.umbral_aviso == 0.06
    assert p.texto_aviso == TEXTO_AVISO
    # El catálogo no tiene una escala de nivel de riesgo: no se inventa.
    assert p.nivel_riesgo_modificacion == catalogo.PENDIENTE_DE_DEFINIR


def test_solo_el_coste_de_capital_tiene_umbral_de_aviso():
    con_aviso = [p.clave for p in catalogo.obtener_catalogo() if p.umbral_aviso is not None]
    assert con_aviso == [CLAVE]
    assert all(p.umbral_aviso is None and p.texto_aviso is None
               for p in catalogo.obtener_plantillas())


def test_el_valor_por_defecto_esta_dentro_del_rango():
    assert cargar_defaults().get(CLAVE) == 0.015


# ─────────────────────── rango por simulación ───────────────────────

def test_simulacion_acepta_los_extremos_del_rango(api, headers, aid):
    assert _simular(api, headers, aid, {CLAVE: 0.15}).status_code == 201
    assert _simular(api, headers, aid, {CLAVE: 0.0}).status_code == 201


@pytest.mark.parametrize("valor", [0.151, -0.01])
def test_simulacion_fuera_de_rango_da_422_sin_escribir_nada(api, headers, aid, valor):
    antes = _contar()
    r = _simular(api, headers, aid, {CLAVE: valor})
    assert r.status_code == 422, r.text
    detalle = r.json()["detail"]
    assert CLAVE in detalle
    assert "fuera del rango admitido: de 0 a 0,15, ambos incluidos" in detalle
    assert _contar() == antes


def test_otro_parametro_con_cota_dentro_de_rango_se_acepta(api, headers, aid):
    assert _simular(api, headers, aid, {"semaforo.verde.ico_min": 80}).status_code == 201


def test_otro_parametro_con_cota_fuera_de_rango_da_422(api, headers, aid):
    antes = _contar()
    r = _simular(api, headers, aid, {"semaforo.verde.ico_min": 150})
    assert r.status_code == 422
    assert "fuera del rango admitido: de 0 a 100, ambos incluidos" in r.json()["detail"]
    assert _contar() == antes


def test_parametro_sin_rango_concreto_no_se_valida(api, headers, aid):
    # `rvc_min` no tiene cota técnica (pendiente_de_definir): sigue sin validarse.
    assert _simular(api, headers, aid, {"semaforo.verde.rvc_min": 50.0}).status_code == 201


# ─────────────────────── rango por edición global ───────────────────────

def test_edicion_global_acepta_el_extremo_del_rango(api, headers):
    try:
        assert _publicar(api, headers, CLAVE, 0.15).status_code == 200
    finally:
        _borrar_parametro(CLAVE)


@pytest.mark.parametrize("valor", [0.151, -0.01])
def test_edicion_global_fuera_de_rango_da_422_con_el_mismo_mensaje(api, headers, aid, valor):
    antes = _contar()
    r = _publicar(api, headers, CLAVE, valor)
    assert r.status_code == 422, r.text
    assert _contar() == antes
    # Misma regla, misma función, mismo texto que por simulación.
    assert r.json()["detail"] == _simular(api, headers, aid, {CLAVE: valor}).json()["detail"]


def test_edicion_global_de_otro_parametro_con_cota(api, headers):
    try:
        assert _publicar(api, headers, "semaforo.verde.ico_min", 80).status_code == 200
    finally:
        _borrar_parametro("semaforo.verde.ico_min")
    antes = _contar()
    assert _publicar(api, headers, "semaforo.verde.ico_min", 150).status_code == 422
    assert _contar() == antes


def test_edicion_global_de_una_seccion_no_salta_el_rango(api, headers):
    """Publicar la sección entera no es un atajo para meter una hoja fuera de rango."""
    seccion = {**cargar_defaults().seccion("semaforo.verde"), "ico_min": 150}
    antes = _contar()
    r = _publicar(api, headers, "semaforo.verde", seccion)
    assert r.status_code == 422
    assert "semaforo.verde.ico_min" in r.json()["detail"]
    assert _contar() == antes


def test_edicion_global_rechaza_un_no_numero_en_un_parametro_con_rango(api, headers):
    antes = _contar()
    assert _publicar(api, headers, CLAVE, "mucho").status_code == 422
    assert _contar() == antes


# ─────────────────────── parametros-simulables ───────────────────────

def test_parametros_simulables_devuelve_umbral_de_aviso(api, headers, aid):
    r = api.get(f"/api/v1/analisis/{aid}/parametros-simulables", headers=headers)
    assert r.status_code == 200
    por_clave = {p["clave"]: p for p in r.json()["editables"]}
    assert por_clave[CLAVE]["umbral_aviso"] == 0.06
    assert por_clave[CLAVE]["texto_aviso"] == TEXTO_AVISO
    assert por_clave[CLAVE]["rango"] == [0.0, 0.15]
    otros = [p for c, p in por_clave.items() if c != CLAVE]
    assert otros and all(p["umbral_aviso"] is None and p["texto_aviso"] is None for p in otros)


# ─────────────────────── explicación en el informe ───────────────────────

@pytest.fixture(scope="module")
def dorado(caso_19):  # noqa: F811
    return ejecutar_analisis(caso_19)


def test_informe_explica_el_coste_de_capital_con_su_importe(dorado):
    assert dorado.decision.precios.detalle["coste_capital"] == 3659.05
    assert LINEA_CASO19 in dorado.informe_markdown


def test_el_resultado_lleva_la_tasa_aplicada_junto_al_importe(dorado):
    # La interfaz lee la tasa y el importe del mismo resultado.
    assert dorado.decision.precios.detalle["coste_capital_anual"] == 0.015


def test_informe_explica_la_tasa_de_una_simulacion(caso_19):  # noqa: F811
    r = ejecutar_analisis(caso_19, params=cargar_defaults().con_overrides({CLAVE: 0.0125}))
    assert "El coste de capital (1,25 % anual, coste de oportunidad" in r.informe_markdown


def _informe_sin(dorado, entrada, *, tasa: bool, importe: bool) -> str:
    parciales = {"valoracion": dorado.valoracion, "icu": dorado.icu, "reforma": dorado.reforma,
                 "costes": dorado.costes, "riesgos": dorado.riesgos,
                 "rentabilidad": dorado.rentabilidad, "puja": dorado.puja, "ici": dorado.ici,
                 "delta_v": dorado.delta_v, "vs_p": dorado.vs_prudente,
                 "reglas": dorado.reglas_disparadas}
    if tasa:
        parciales["coste_capital_anual"] = 0.015
    dec = dorado.decision.model_copy(deep=True)
    if not importe:
        dec.precios.detalle.pop("coste_capital")
    return m14_informe.construir_informe(entrada, parciales, dec, dorado.checklist)


@pytest.mark.parametrize("tasa,importe", [(False, True), (True, False)])
def test_sin_tasa_o_sin_importe_no_se_imprime_la_linea(dorado, caso_19, tasa, importe):  # noqa: F811
    texto = _informe_sin(dorado, caso_19, tasa=tasa, importe=importe)
    assert "El coste de capital (" not in texto
    assert "## 7 · Análisis financiero" in texto


# ─────────────── el motor no cambia ni un número (caso §19) ───────────────

# Capturados con el código ANTERIOR a 5G.4 (commit 9c41bbe).
ESCALERA_ANTES = (51317.0, 60011.0, 68731.0, 80022.0, False)
DETALLE_ANTES = {"delta_v_aplicado": 0.0, "m_objetivo_ajustado": 0.25, "m_minimo_ajustado": 0.17,
                 "vs_pesimista": 160837.44, "p_por_margen_min": 69097.33,
                 "p_por_pesimista": 68730.9, "coste_capital": 3659.05}
RENTABILIDAD_ANTES = {"precio_evaluado": 60011.0, "inversion_total": 141395.76,
                      "beneficio": 35348.68, "roi": 0.25, "roi_anualizado": 0.2287,
                      "tir_anual": 0.3387, "valor_esperado": 32361.25}
ESCENARIOS_ANTES = [
    ("pesimista", 160837.44, 151559.46, 9277.98, 0.0612, 0.04, 18.2),
    ("base", 176744.44, 141395.76, 35348.68, 0.25, 0.2287, 13.0),
    ("optimista", 186995.62, 133995.7, 52999.92, 0.3955, 0.4361, 11.0),
]
DECISION_ANTES = ("amarillo", 64, 40, 0.248)


def test_m11_m12_no_cambian_ningun_valor_numerico(dorado):
    e = dorado.decision.precios
    assert (e.p_ideal, e.p_objetivo, e.p_max, e.p_limite, e.degenerada) == ESCALERA_ANTES
    # Claves nuevas de `detalle`, solo de trazabilidad: la tasa aplicada (5G.4) y la base
    # del coste de capital, el capital propio (5H.1-B). Las demás, idénticas.
    nuevas = {"coste_capital_anual", "capital_propio"}
    assert {k: v for k, v in e.detalle.items() if k not in nuevas} == DETALLE_ANTES
    rt = dorado.rentabilidad
    assert {k: getattr(rt, k) for k in RENTABILIDAD_ANTES} == RENTABILIDAD_ANTES
    assert [(x.nombre, x.vs, x.coste_total, x.beneficio, x.roi, x.roi_anualizado, x.plazo_meses)
            for x in rt.escenarios] == ESCENARIOS_ANTES
    d = dorado.decision
    assert (d.semaforo, d.ico, d.ra, d.margen_seguridad_valor) == DECISION_ANTES

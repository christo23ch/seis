"""Fase 5D — servicio de simulaciones sobre un `Analisis` ya existente.

Puro backend: sin HTTP, sin UI. `api` se pide solo para garantizar que
`Base.metadata.create_all` ya corrió para este módulo (mismo patrón que
`tests/test_valoracion_detalle.py`/`tests/test_comparables_usados.py`).
Cada test abre su propia `SessionLocal()` y crea sus propios `Analisis` vía
`analisis_service.crear_analisis`, como en el resto de la suite — no se toca
ningún dato de las Fases 1-4 ni de la Fase 5C.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app import models
from app.core.db import SessionLocal
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import ejecutar_analisis
from app.services import analisis_service, conocimiento_service, simulacion_service
from tests.conftest import entrada_base


def _crear_analisis(db, **overrides) -> str:
    analisis_id, _ = analisis_service.crear_analisis(db, entrada_base(**overrides))
    return analisis_id


# ─────────────────────── 1. Reconstrucción lossless ───────────────────────

def test_reconstruccion_lossless_desde_analisis_entrada(api):
    db = SessionLocal()
    try:
        inp = entrada_base()
        analisis_id, _ = analisis_service.crear_analisis(db, inp)
        analisis = db.get(models.Analisis, analisis_id)

        reconstruido = simulacion_service._reconstruir_input(analisis)

        assert inp.model_dump() == reconstruido.model_dump()
    finally:
        db.close()


# ─────────────────────── 2. Simulación básica ───────────────────────

def test_simulacion_basica_sin_overrides(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        sim = simulacion_service.crear_simulacion(db, analisis_id)

        assert db.get(models.Simulacion, sim.id) is not None
        assert sim.estado == "pendiente"
        assert sim.analisis_id == analisis_id
        assert sim.overrides == {}
        assert isinstance(sim.parametros_aplicados, dict) and sim.parametros_aplicados
        assert isinstance(sim.resultado, dict) and sim.resultado
    finally:
        db.close()


# ─────────────────────── 3. Snapshot completo ───────────────────────

def test_snapshot_es_el_arbol_completo_no_solo_claves_editables(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)

        # Secciones que NO son T3 de M12/M13 y por tanto nunca están en el
        # catálogo — deben estar en el snapshot igualmente, porque el
        # snapshot es el árbol .raw() completo, no una proyección del catálogo.
        for seccion in ("fiscal", "aranceles", "comercializacion", "tenencia",
                        "reforma", "ocupacion", "atrasos", "icu", "escenarios"):
            assert seccion in sim.parametros_aplicados, f"falta sección '{seccion}' en el snapshot"

        # Perfiles fusionados: la sección completa, no solo las claves editables.
        assert "perfiles" in sim.parametros_aplicados
        assert set(sim.parametros_aplicados["perfiles"].keys()) == {
            "flip_ligero", "flip_integral", "cambio_uso",
            "division_horizontal", "oportunista", "rentista"}
        assert "coc_min" in sim.parametros_aplicados["perfiles"]["rentista"]

        # Debe coincidir exactamente con params_base.raw() (sin overrides aquí).
        params_base, _, _ = conocimiento_service.cargar_conocimiento(db)
        assert sim.parametros_aplicados == params_base.raw()
    finally:
        db.close()


# ─────────────────────── 4. Override simple ───────────────────────

def test_override_simple_semaforo_verde_ico_min(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        overrides = {"semaforo.verde.ico_min": 78}

        sim = simulacion_service.crear_simulacion(db, analisis_id, overrides)

        assert sim.overrides == overrides
        assert sim.parametros_aplicados["semaforo"]["verde"]["ico_min"] == 78

        # El resultado procede realmente de esos parámetros: se reconstruye
        # el mismo input/params/reglas por fuera y se compara con lo persistido.
        analisis = db.get(models.Analisis, analisis_id)
        inp = simulacion_service._reconstruir_input(analisis)
        params_base, reglas, version_reglas = conocimiento_service.cargar_conocimiento(db)
        params_esperado = params_base.con_overrides(overrides)
        resultado_esperado = ejecutar_analisis(inp, params=params_esperado, reglas=reglas,
                                               version_reglas=version_reglas)
        assert sim.resultado == simulacion_service._json(resultado_esperado)
    finally:
        db.close()


# ─────────────────────── 5. Override de perfil (plantilla) ───────────────────────

def test_override_de_plantilla_perfil_no_afecta_parametros_base(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)   # perfil por defecto: flip_integral
        overrides = {"perfiles.flip_integral.rvc_veto": 0.95}   # nueva clave de 5C.1

        sim = simulacion_service.crear_simulacion(db, analisis_id, overrides)

        assert sim.overrides == overrides
        assert sim.parametros_aplicados["perfiles"]["flip_integral"]["rvc_veto"] == 0.95

        # No contamina Parametros base global ni defaults.yaml.
        assert cargar_defaults().get("perfiles.flip_integral.rvc_veto") == 0.80
    finally:
        db.close()


# ─────────────────────── 6. rvc_veto ───────────────────────

def test_override_rvc_veto_aceptado_y_distinto_de_la_regla(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        overrides = {"perfiles.flip_integral.rvc_veto": 0.60}

        sim = simulacion_service.crear_simulacion(db, analisis_id, overrides)

        assert "perfiles.flip_integral.rvc_veto" in sim.overrides
        assert sim.parametros_aplicados["perfiles"]["flip_integral"]["rvc_veto"] == 0.60
        # No se confunde con la regla T2: ni la clave de override ni el
        # snapshot contienen el identificador de la regla.
        assert "VETO-COMP-01" not in sim.overrides
        assert "VETO-COMP-01" not in str(sim.parametros_aplicados.get("perfiles"))
    finally:
        db.close()


# ─────────────────────── 7. Hardcode rechazado ───────────────────────

def test_override_de_hardcode_rechazado(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        antes = db.query(models.Simulacion).count()

        try:
            simulacion_service.crear_simulacion(
                db, analisis_id, {"hardcode.m13.ratio_clamp_min": 0.05})
            assert False, "debía rechazar el override de un hardcode"
        except simulacion_service.OverrideInvalidoError as exc:
            assert exc.clave == "hardcode.m13.ratio_clamp_min"

        assert db.query(models.Simulacion).count() == antes
    finally:
        db.close()


# ─────────────────────── 8. Derivado rechazado ───────────────────────

def test_override_de_calculo_derivado_rechazado(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        try:
            simulacion_service.crear_simulacion(db, analisis_id, {"ra_base": 50})
            assert False, "debía rechazar el override de un cálculo derivado (TIPO 3)"
        except simulacion_service.OverrideInvalidoError:
            pass
    finally:
        db.close()


# ─────────────────────── 9. Clave inexistente rechazada ───────────────────────

def test_override_de_clave_inexistente_rechazado(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        try:
            simulacion_service.crear_simulacion(
                db, analisis_id, {"parametro.que.no.existe": 1})
            assert False, "debía rechazar una clave inexistente"
        except simulacion_service.OverrideInvalidoError:
            pass

        # Y también un patrón de plantilla sin resolver.
        try:
            simulacion_service.crear_simulacion(
                db, analisis_id, {"perfiles.{perfil}.rvc_veto": 0.9})
            assert False, "debía rechazar un patrón de plantilla sin resolver"
        except simulacion_service.OverrideInvalidoError:
            pass
    finally:
        db.close()


# ─────────────────────── 10. Simulaciones independientes ───────────────────────

def test_simulaciones_independientes_sin_contaminacion(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        sim_a = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.05})
        sim_b = simulacion_service.crear_simulacion(
            db, analisis_id, {"financiacion.dscr_minimo": 1.5})

        assert sim_a.overrides == {"capital.coste_capital_anual": 0.05}
        assert sim_b.overrides == {"financiacion.dscr_minimo": 1.5}
        assert "financiacion.dscr_minimo" not in sim_a.overrides
        assert "capital.coste_capital_anual" not in sim_b.overrides

        assert sim_a.parametros_aplicados["capital"]["coste_capital_anual"] == 0.05
        assert sim_b.parametros_aplicados["capital"]["coste_capital_anual"] == 0.015  # default
        assert sim_b.parametros_aplicados["financiacion"]["dscr_minimo"] == 1.5
        assert sim_a.parametros_aplicados["financiacion"]["dscr_minimo"] == 1.2  # default

        assert sim_a.resultado is not sim_b.resultado
    finally:
        db.close()


# ─────────────────────── 11. Múltiples simulaciones ───────────────────────

def test_multiples_simulaciones_mismo_analisis_sin_nuevos_analisis(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis_antes = db.query(models.Analisis).count()

        for i in range(3):
            simulacion_service.crear_simulacion(
                db, analisis_id, {"capital.coste_capital_anual": 0.01 + i * 0.001})

        assert db.query(models.Simulacion).filter_by(analisis_id=analisis_id).count() == 3
        assert db.query(models.Analisis).count() == analisis_antes
    finally:
        db.close()


# ─────────────────────── 12. Análisis original intacto ───────────────────────

def test_analisis_original_intacto_tras_simular(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)
        entrada_antes = dict(analisis.entrada)
        resultado_antes = dict(analisis.resultado)

        simulacion_service.crear_simulacion(
            db, analisis_id, {"semaforo.verde.ico_min": 90,
                              "perfiles.flip_integral.m_objetivo": 0.5})

        db.refresh(analisis)   # fuerza releer de BD, no confiar en el objeto en memoria
        assert analisis.entrada == entrada_antes
        assert analisis.resultado == resultado_antes
    finally:
        db.close()


# ─────────────────────── 13. pendiente → validada ───────────────────────

def test_transicion_pendiente_a_validada(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)
        assert sim.fecha_validacion is None

        validada = simulacion_service.validar_simulacion(db, analisis_id, sim.id)

        assert validada.estado == "validada"
        assert validada.fecha_validacion is not None
    finally:
        db.close()


# ─────────────────────── 14. pendiente → descartada ───────────────────────

def test_transicion_pendiente_a_descartada_conserva_datos(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.02})
        overrides_antes = dict(sim.overrides)
        snapshot_antes = dict(sim.parametros_aplicados)
        resultado_antes = dict(sim.resultado)

        descartada = simulacion_service.descartar_simulacion(db, analisis_id, sim.id)

        assert descartada.estado == "descartada"
        assert descartada.overrides == overrides_antes
        assert descartada.parametros_aplicados == snapshot_antes
        assert descartada.resultado == resultado_antes
    finally:
        db.close()


# ─────────────────────── 15. Transiciones inválidas ───────────────────────

def test_transiciones_invalidas_rechazadas(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        sim_validada = simulacion_service.crear_simulacion(db, analisis_id)
        simulacion_service.validar_simulacion(db, analisis_id, sim_validada.id)

        sim_descartada = simulacion_service.crear_simulacion(db, analisis_id)
        simulacion_service.descartar_simulacion(db, analisis_id, sim_descartada.id)

        for accion in (simulacion_service.validar_simulacion, simulacion_service.descartar_simulacion):
            try:
                accion(db, analisis_id, sim_validada.id)
                assert False, "validada no debe aceptar ninguna transición"
            except simulacion_service.TransicionInvalidaError:
                pass
            try:
                accion(db, analisis_id, sim_descartada.id)
                assert False, "descartada no debe aceptar ninguna transición"
            except simulacion_service.TransicionInvalidaError:
                pass
    finally:
        db.close()


# ─────────────────────── 16. Validar no modifica Analisis ───────────────────────

def test_validar_simulacion_no_modifica_analisis(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)
        entrada_antes = dict(analisis.entrada)
        resultado_antes = dict(analisis.resultado)

        sim = simulacion_service.crear_simulacion(
            db, analisis_id, {"semaforo.verde.ico_min": 90})
        simulacion_service.validar_simulacion(db, analisis_id, sim.id)

        db.refresh(analisis)
        assert analisis.entrada == entrada_antes
        assert analisis.resultado == resultado_antes
    finally:
        db.close()


# ─────────────────────── 17. Pertenencia cruzada ───────────────────────

def test_pertenencia_cruzada_rechazada(api):
    db = SessionLocal()
    try:
        analisis_a = _crear_analisis(db)
        analisis_b = _crear_analisis(db)
        sim_de_a = simulacion_service.crear_simulacion(db, analisis_a)

        try:
            simulacion_service.validar_simulacion(db, analisis_b, sim_de_a.id)
            assert False, "no debía permitir validar una simulación de otro análisis"
        except simulacion_service.PertenenciaCruzadaError as exc:
            assert exc.simulacion_id == sim_de_a.id
            assert exc.analisis_id == analisis_b

        try:
            simulacion_service.descartar_simulacion(db, analisis_b, sim_de_a.id)
            assert False, "no debía permitir descartar una simulación de otro análisis"
        except simulacion_service.PertenenciaCruzadaError:
            pass

        # La simulación sigue intacta y sigue perteneciendo a A.
        sim_de_a_recargada = db.get(models.Simulacion, sim_de_a.id)
        assert sim_de_a_recargada.estado == "pendiente"
        assert sim_de_a_recargada.analisis_id == analisis_a
    finally:
        db.close()


# ─────────────────────── 18. Resultado = pipeline completo ───────────────────────

def test_resultado_contiene_el_analisisresult_completo(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)

        campos_esperados = {
            "decision", "ici", "valoracion", "icu", "reforma", "costes",
            "riesgos", "rentabilidad", "puja", "checklist", "reglas_disparadas",
            "informe_markdown", "delta_v", "vs_prudente",
        }
        assert campos_esperados <= set(sim.resultado.keys())
        assert isinstance(sim.resultado["informe_markdown"], str) and sim.resultado["informe_markdown"]
        assert "semaforo" in sim.resultado["decision"]
    finally:
        db.close()


# ─────────────────────── 19. Informe provisional ───────────────────────

def test_informe_de_simulacion_pendiente_es_provisional(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)

        assert sim.estado == "pendiente"
        assert sim.resultado.get("informe_markdown")
        # Su sola presencia no cambia el estado ni lo convierte en oficial.
        assert sim.estado != "validada"
        assert sim.fecha_validacion is None
    finally:
        db.close()


# ─────────────────────── 20. Aislamiento de conocimiento ───────────────────────

def test_aislamiento_entre_simulaciones_consecutivas(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.099})
        sim_b = simulacion_service.crear_simulacion(
            db, analisis_id, {"financiacion.dscr_minimo": 2.0})

        # B parte de la configuración base, no del objeto ya modificado por A.
        assert sim_b.parametros_aplicados["capital"]["coste_capital_anual"] == 0.015
    finally:
        db.close()


# ─────────────────────── 21. No modifica defaults ───────────────────────

def test_simulaciones_no_modifican_defaults_yaml(api):
    db = SessionLocal()
    try:
        antes = cargar_defaults().raw()
        analisis_id = _crear_analisis(db)
        simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.5})
        simulacion_service.crear_simulacion(
            db, analisis_id, {"semaforo.verde.ico_min": 1})
        despues = cargar_defaults().raw()
        assert antes == despues
    finally:
        db.close()


# ─────────────────────── 22. Rendimiento básico ───────────────────────

def test_no_hay_carga_de_conocimiento_redundante_y_es_razonablemente_rapida(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        with patch("app.services.simulacion_service.conocimiento_service.cargar_conocimiento",
                  wraps=conocimiento_service.cargar_conocimiento) as espia:
            inicio = time.perf_counter()
            simulacion_service.crear_simulacion(
                db, analisis_id, {"capital.coste_capital_anual": 0.02})
            duracion = time.perf_counter() - inicio

        assert espia.call_count == 1, "crear_simulacion no debe cargar conocimiento más de una vez"
        assert duracion < 2.0, f"una simulación no debería tardar {duracion:.3f}s"
    finally:
        db.close()


# ─────────────────────── 23. Forma de los valores de override (Fase 5F.7.1) ───────────────────────
#
# La clave ya se validaba (5D); el VALOR no, y uno de forma incorrecta llegaba al
# motor y reventaba con `TypeError` (HTTP 500, medido en la auditoría 5F.7). Solo
# se comprueba la FORMA contra el valor de referencia del mismo árbol: ningún
# rango, suma, orden ni regla de negocio.

_FORMA_INVALIDA = [
    ("semaforo.verde.ico_min", "abc"),                    # texto donde va número
    ("semaforo.verde.ico_min", None),                     # nulo donde va número
    ("semaforo.verde.ico_min", [1, 2]),                   # lista donde va número
    ("semaforo.verde.ico_min", {"x": 1}),                 # objeto donde va número
    ("semaforo.verde.ico_min", True),                     # bool NO es número aquí
    ("capital.coste_capital_anual", float("nan")),        # número no finito
    ("capital.coste_capital_anual", float("inf")),        # número no finito
    ("riesgos.bandas_ra", 5),                             # número donde va lista
    ("riesgos.bandas_ra", [{"max": "x", "banda": "bajo"}]),     # elemento mal formado
    ("adjudicacion.ratios.aeat", {"otra": 0.5}),          # claves distintas
    ("adjudicacion.ratios.aeat", {"default": 0.5, "otra": 1}),  # clave de más
    ("adjudicacion.ratios.judicial_boe",                  # estructura anidada rota
     {"vivienda": 0.4, "default": 0.5}),
]


@pytest.mark.parametrize("clave,valor", _FORMA_INVALIDA)
def test_override_con_forma_invalida_se_rechaza_sin_crear_fila(api, clave, valor):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        with patch("app.services.simulacion_service.ejecutar_analisis") as motor:
            with pytest.raises(simulacion_service.OverrideInvalidoError) as exc:
                simulacion_service.crear_simulacion(db, analisis_id, {clave: valor})
        assert exc.value.clave == clave
        assert motor.call_count == 0, "un valor mal formado no debe llegar al motor"
        assert db.query(models.Simulacion).filter_by(analisis_id=analisis_id).count() == 0
    finally:
        db.close()


def test_forma_invalida_anidada_indica_la_ruta_interna(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        with pytest.raises(simulacion_service.OverrideInvalidoError) as exc:
            simulacion_service.crear_simulacion(
                db, analisis_id, {"riesgos.bandas_ra": [{"max": "x", "banda": "bajo"}]})
        assert "[0].max" in exc.value.motivo
    finally:
        db.close()


@pytest.mark.parametrize("clave,valor", [
    ("capital.coste_capital_anual", 1),                   # int donde la referencia es float
    ("semaforo.verde.ico_min", 90.5),                     # float donde la referencia es int
    ("adjudicacion.ratios.aeat", {"default": 0.6}),       # estructura con su forma exacta
    ("riesgos.bandas_ra", [{"max": 30, "banda": "bajo"}, {"max": 100, "banda": "alto"}]),
])
def test_override_con_forma_valida_se_acepta(api, clave, valor):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id, {clave: valor})
        assert sim.estado == "pendiente"
        assert sim.overrides == {clave: valor}
    finally:
        db.close()

"""Fase 5E — `Analisis.simulacion_validada_id`: configuración actualmente
seleccionada (original vs. una `Simulacion` concreta).

Servicio: sin HTTP, sesión directa (mismo patrón que `test_simulacion.py`).
Endpoint: con `api`/`headers`, para probar la adaptación de los 4 endpoints
de lectura que el audit de Fase 5E identificó (`detalle`, `informe`,
`informe.pdf`, `checklist`). Los análisis de los tests HTTP se crean por la
API real (como `test_api.py`), no por el servicio directo, porque
`obtener_analisis` es *fail-closed* por organización (§4 de `analisis_service`):
un análisis creado sin `organizacion_id` nunca sería visible para el admin
autenticado, con o sin cambios de esta fase.
"""
from __future__ import annotations

import json

from app import models
from app.core.db import SessionLocal
from app.services import analisis_service, simulacion_service
from tests.conftest import entrada_base


def _crear_analisis(db, **overrides) -> str:
    analisis_id, _ = analisis_service.crear_analisis(db, entrada_base(**overrides))
    return analisis_id


def _crear_analisis_via_api(api, headers) -> str:
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ─────────────────────── Servicio: puntero y selección ───────────────────────

def test_simulacion_validada_id_null_por_defecto(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)
        assert analisis.simulacion_validada_id is None
    finally:
        db.close()


def test_validar_simulacion_fija_puntero_en_la_misma_operacion(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.02})

        validada = simulacion_service.validar_simulacion(db, analisis_id, sim.id)

        assert validada.estado == "validada"
        analisis = db.get(models.Analisis, analisis_id)
        assert analisis.simulacion_validada_id == sim.id
    finally:
        db.close()


def test_validar_segunda_simulacion_mueve_el_puntero_sin_cambiar_historial(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim_a = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.02})
        sim_b = simulacion_service.crear_simulacion(
            db, analisis_id, {"financiacion.dscr_minimo": 1.5})

        simulacion_service.validar_simulacion(db, analisis_id, sim_a.id)
        simulacion_service.validar_simulacion(db, analisis_id, sim_b.id)

        analisis = db.get(models.Analisis, analisis_id)
        assert analisis.simulacion_validada_id == sim_b.id

        sim_a_recargada = db.get(models.Simulacion, sim_a.id)
        assert sim_a_recargada.estado == "validada"   # sigue validada, aunque ya no sea la actual
    finally:
        db.close()


def test_volver_a_configuracion_original_no_toca_simulaciones(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)
        simulacion_service.validar_simulacion(db, analisis_id, sim.id)

        analisis = simulacion_service.volver_a_configuracion_original(db, analisis_id)

        assert analisis.simulacion_validada_id is None
        sim_recargada = db.get(models.Simulacion, sim.id)
        assert sim_recargada.estado == "validada"
        assert sim_recargada.fecha_validacion is not None
    finally:
        db.close()


def test_volver_a_configuracion_original_es_idempotente(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        primera = simulacion_service.volver_a_configuracion_original(db, analisis_id)
        segunda = simulacion_service.volver_a_configuracion_original(db, analisis_id)
        assert primera.simulacion_validada_id is None
        assert segunda.simulacion_validada_id is None
    finally:
        db.close()


def test_analisis_no_encontrado_en_validar_y_volver(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)

        try:
            simulacion_service.validar_simulacion(db, "no-existe", sim.id)
            assert False, "debía fallar con análisis inexistente"
        except simulacion_service.AnalisisNoEncontradoError:
            pass

        try:
            simulacion_service.volver_a_configuracion_original(db, "no-existe")
            assert False, "debía fallar con análisis inexistente"
        except simulacion_service.AnalisisNoEncontradoError:
            pass
    finally:
        db.close()


# ─────────────────────── Regresión: pertenencia y transiciones ───────────────────────

def test_pertenencia_cruzada_en_validar_sigue_bloqueada_tras_5e(api):
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

        # Ninguno de los dos análisis quedó apuntando a la simulación ajena.
        assert db.get(models.Analisis, analisis_a).simulacion_validada_id is None
        assert db.get(models.Analisis, analisis_b).simulacion_validada_id is None
    finally:
        db.close()


def test_transiciones_invalidas_siguen_rechazadas_tras_5e(api):
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

        # El puntero sigue en la única que llegó a validarse de verdad.
        assert db.get(models.Analisis, analisis_id).simulacion_validada_id == sim_validada.id
    finally:
        db.close()


# ─────────────────────── obtener_configuracion_actual ───────────────────────

def test_configuracion_actual_sin_seleccion_es_la_original(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)

        config = simulacion_service.obtener_configuracion_actual(db, analisis_id)

        assert config.simulacion_id is None
        assert config.entrada == analisis.entrada
        assert config.resultado == analisis.resultado
    finally:
        db.close()


def test_configuracion_actual_con_seleccion_usa_resultado_de_la_simulacion(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)
        entrada_original = dict(analisis.entrada)

        sim = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.5})
        simulacion_service.validar_simulacion(db, analisis_id, sim.id)

        config = simulacion_service.obtener_configuracion_actual(db, analisis_id)

        assert config.simulacion_id == sim.id
        assert config.resultado == sim.resultado
        assert config.resultado != analisis.resultado    # el override tuvo efecto real
        # El inmueble NUNCA cambia de fuente: sigue siendo el del análisis original.
        assert config.entrada == entrada_original
    finally:
        db.close()


def test_configuracion_actual_puntero_roto_degrada_a_original(api):
    """Defensivo: si `simulacion_validada_id` apuntara a una fila que ya no
    existe (SQLite no aplica `ondelete=SET NULL` porque el proyecto no activa
    `PRAGMA foreign_keys`; en PostgreSQL esto no debería llegar a ocurrir),
    la lectura no debe romperse — se degrada a la configuración original."""
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)
        analisis.simulacion_validada_id = "id-que-no-existe"
        db.commit()

        config = simulacion_service.obtener_configuracion_actual(db, analisis_id)

        assert config.simulacion_id is None
        assert config.resultado == analisis.resultado
    finally:
        db.close()


# ─────────────────────── Endpoints HTTP adaptados ───────────────────────

def test_endpoint_detalle_sin_seleccion_devuelve_original(api, headers):
    analisis_id = _crear_analisis_via_api(api, headers)

    r = api.get(f"/api/v1/analisis/{analisis_id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["simulacion_validada_id"] is None


def test_endpoints_reflejan_la_simulacion_seleccionada(api, headers):
    analisis_id = _crear_analisis_via_api(api, headers)
    db = SessionLocal()
    try:
        analisis = db.get(models.Analisis, analisis_id)
        entrada_original = dict(analisis.entrada)

        sim = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.5})
        simulacion_service.validar_simulacion(db, analisis_id, sim.id)
        resultado_sim = dict(sim.resultado)
    finally:
        db.close()

    detalle = api.get(f"/api/v1/analisis/{analisis_id}", headers=headers).json()
    assert detalle["simulacion_validada_id"] == sim.id
    assert detalle["entrada"] == entrada_original          # el inmueble no cambia
    assert detalle["resultado"] == resultado_sim            # el resultado sí

    informe = api.get(f"/api/v1/analisis/{analisis_id}/informe", headers=headers)
    assert informe.status_code == 200
    assert informe.text == resultado_sim["informe_markdown"]

    checklist = api.get(f"/api/v1/analisis/{analisis_id}/checklist", headers=headers)
    assert checklist.status_code == 200
    assert checklist.json() == resultado_sim["checklist"]

    pdf = api.get(f"/api/v1/analisis/{analisis_id}/informe.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"


def test_endpoints_vuelven_al_original_tras_deseleccionar(api, headers):
    analisis_id = _crear_analisis_via_api(api, headers)
    db = SessionLocal()
    try:
        analisis = db.get(models.Analisis, analisis_id)
        resultado_original = dict(analisis.resultado)

        sim = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.5})
        simulacion_service.validar_simulacion(db, analisis_id, sim.id)
        simulacion_service.volver_a_configuracion_original(db, analisis_id)
    finally:
        db.close()

    detalle = api.get(f"/api/v1/analisis/{analisis_id}", headers=headers).json()
    assert detalle["simulacion_validada_id"] is None
    assert detalle["resultado"] == resultado_original


# ─────────────── Fase 5E.1 — seleccionar_simulacion_validada ───────────────

def _dos_simulaciones_validadas(db, analisis_id):
    sim_a = simulacion_service.crear_simulacion(
        db, analisis_id, {"capital.coste_capital_anual": 0.02})
    sim_b = simulacion_service.crear_simulacion(
        db, analisis_id, {"financiacion.dscr_minimo": 1.5})
    simulacion_service.validar_simulacion(db, analisis_id, sim_a.id)
    simulacion_service.validar_simulacion(db, analisis_id, sim_b.id)
    return sim_a, sim_b


def test_seleccionar_dos_validadas_reselecciona_la_primera(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim_a, sim_b = _dos_simulaciones_validadas(db, analisis_id)
        assert db.get(models.Analisis, analisis_id).simulacion_validada_id == sim_b.id

        analisis = simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim_a.id)

        assert analisis.simulacion_validada_id == sim_a.id
        assert db.get(models.Simulacion, sim_a.id).estado == "validada"
        assert db.get(models.Simulacion, sim_b.id).estado == "validada"
    finally:
        db.close()


def test_seleccionar_no_modifica_ningun_estado(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim_a, sim_b = _dos_simulaciones_validadas(db, analisis_id)   # puntero queda en B

        simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim_a.id)

        analisis = db.get(models.Analisis, analisis_id)
        assert analisis.simulacion_validada_id == sim_a.id
        assert db.get(models.Simulacion, sim_a.id).estado == "validada"
        assert db.get(models.Simulacion, sim_b.id).estado == "validada"
    finally:
        db.close()


def test_seleccionar_simulacion_pendiente_falla(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)

        try:
            simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim.id)
            assert False, "no debía permitir seleccionar una simulación pendiente"
        except simulacion_service.TransicionInvalidaError as exc:
            assert exc.estado_actual == "pendiente"

        assert db.get(models.Analisis, analisis_id).simulacion_validada_id is None
    finally:
        db.close()


def test_seleccionar_simulacion_descartada_falla(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = simulacion_service.crear_simulacion(db, analisis_id)
        simulacion_service.descartar_simulacion(db, analisis_id, sim.id)

        try:
            simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim.id)
            assert False, "no debía permitir seleccionar una simulación descartada"
        except simulacion_service.TransicionInvalidaError as exc:
            assert exc.estado_actual == "descartada"

        assert db.get(models.Analisis, analisis_id).simulacion_validada_id is None
    finally:
        db.close()


def test_seleccionar_simulacion_de_otro_analisis_falla_por_pertenencia(api):
    db = SessionLocal()
    try:
        analisis_a = _crear_analisis(db)
        analisis_b = _crear_analisis(db)
        sim_de_a = simulacion_service.crear_simulacion(db, analisis_a)
        simulacion_service.validar_simulacion(db, analisis_a, sim_de_a.id)

        try:
            simulacion_service.seleccionar_simulacion_validada(db, analisis_b, sim_de_a.id)
            assert False, "no debía permitir seleccionar una simulación de otro análisis"
        except simulacion_service.PertenenciaCruzadaError as exc:
            assert exc.simulacion_id == sim_de_a.id
            assert exc.analisis_id == analisis_b

        assert db.get(models.Analisis, analisis_b).simulacion_validada_id is None
    finally:
        db.close()


def test_seleccionar_id_inexistente_falla(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        try:
            simulacion_service.seleccionar_simulacion_validada(db, analisis_id, "no-existe")
            assert False, "debía fallar con simulación inexistente"
        except simulacion_service.SimulacionNoEncontradaError as exc:
            assert exc.simulacion_id == "no-existe"
    finally:
        db.close()


def test_reseleccionar_no_modifica_snapshot_ni_fecha_validacion(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim_a, sim_b = _dos_simulaciones_validadas(db, analisis_id)
        sim_a_antes = db.get(models.Simulacion, sim_a.id)
        estado_antes = sim_a_antes.estado
        fecha_antes = sim_a_antes.fecha_validacion
        overrides_antes = dict(sim_a_antes.overrides)
        parametros_antes = dict(sim_a_antes.parametros_aplicados)
        resultado_antes = dict(sim_a_antes.resultado)

        simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim_a.id)

        sim_a_despues = db.get(models.Simulacion, sim_a.id)
        assert sim_a_despues.estado == estado_antes
        assert sim_a_despues.fecha_validacion == fecha_antes
        assert sim_a_despues.overrides == overrides_antes
        assert sim_a_despues.parametros_aplicados == parametros_antes
        assert sim_a_despues.resultado == resultado_antes
    finally:
        db.close()


def test_flujo_completo_seleccion_historico_no_cambia(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim_a, sim_b = _dos_simulaciones_validadas(db, analisis_id)   # puntero -> B

        def estados():
            return (db.get(models.Simulacion, sim_a.id).estado,
                    db.get(models.Simulacion, sim_b.id).estado)

        assert estados() == ("validada", "validada")

        simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim_a.id)
        assert db.get(models.Analisis, analisis_id).simulacion_validada_id == sim_a.id
        assert estados() == ("validada", "validada")

        simulacion_service.volver_a_configuracion_original(db, analisis_id)
        assert db.get(models.Analisis, analisis_id).simulacion_validada_id is None
        assert estados() == ("validada", "validada")

        simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim_b.id)
        assert db.get(models.Analisis, analisis_id).simulacion_validada_id == sim_b.id
        assert estados() == ("validada", "validada")
    finally:
        db.close()

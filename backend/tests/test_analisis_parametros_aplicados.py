"""Fase 5F.1 — `Analisis.parametros_aplicados`: árbol T3 efectivo congelado
en el momento de crear el análisis (mismo snapshot que `Simulacion.parametros_aplicados`
desde la Fase 5D, ahora también para la configuración original).

Sin HTTP: sesión directa, mismo patrón que `test_simulacion.py`. `api` se pide
solo para garantizar que `Base.metadata.create_all` ya corrió para este módulo.
"""
from __future__ import annotations

from unittest.mock import patch

from app import models
from app.core.db import SessionLocal
from app.services import analisis_service, conocimiento_service
from tests.conftest import entrada_base


# ─────────────────────────── 1. Snapshot presente ───────────────────────────

def test_analisis_nuevo_guarda_snapshot_no_vacio(api):
    db = SessionLocal()
    try:
        analisis_id, _ = analisis_service.crear_analisis(db, entrada_base())
        analisis = db.get(models.Analisis, analisis_id)

        assert analisis.parametros_aplicados is not None
        assert isinstance(analisis.parametros_aplicados, dict)
        assert analisis.parametros_aplicados
    finally:
        db.close()


# ─────────────────────────── 2. Snapshot == params.raw() ───────────────────────────

def test_snapshot_coincide_exactamente_con_params_efectivo(api):
    db = SessionLocal()
    try:
        inp = entrada_base()
        analisis_id, _ = analisis_service.crear_analisis(db, inp)
        analisis = db.get(models.Analisis, analisis_id)

        # Mismo estado de BD, sin nada escrito entre medias: resolver conocimiento
        # de nuevo debe dar exactamente el mismo árbol que el que usó el motor.
        params_esperado, _, _ = conocimiento_service.cargar_conocimiento(db)

        assert analisis.parametros_aplicados == params_esperado.raw()
        # No basta con "contiene algunas claves": comprobación de secciones
        # completas y representativas, deep-equal ya cubierto arriba.
        assert analisis.parametros_aplicados["perfiles"] == params_esperado.raw()["perfiles"]
        assert analisis.parametros_aplicados["riesgos"] == params_esperado.raw()["riesgos"]
    finally:
        db.close()


# ─────────────────────────── 3. Incluye PerfilInversion fusionado ───────────────────────────

def test_snapshot_incluye_perfilinversion_fusionado(api):
    db = SessionLocal()
    try:
        # La fixture `api` no siembra PerfilInversion (eso lo hace scripts/sembrar.py,
        # fuera del alcance de los tests de la suite) — se inserta aquí explícitamente.
        db.add(models.PerfilInversion(
            codigo="flip_ligero", nombre="Reforma ligera + venta (test)",
            parametros={"tipo": "venta", "m_objetivo": 0.77, "m_minimo": 0.33,
                       "rvc_veto": 0.80, "piso_pesimista_frac_i": 0.0}))
        db.commit()

        analisis_id, _ = analisis_service.crear_analisis(db, entrada_base(perfil="flip_ligero"))
        analisis = db.get(models.Analisis, analisis_id)

        assert analisis.parametros_aplicados["perfiles"]["flip_ligero"]["m_objetivo"] == 0.77
        assert analisis.parametros_aplicados["perfiles"]["flip_ligero"]["m_minimo"] == 0.33
        # Distinto del valor de defaults.yaml (0.16): prueba que la fusión ocurrió de verdad.
        assert analisis.parametros_aplicados["perfiles"]["flip_ligero"]["m_objetivo"] != 0.16
    finally:
        db.close()


# ─────────────────────────── 4. Snapshot no cambia con gobernanza posterior ───────────────────────────

def test_snapshot_permanece_aunque_cambie_conocimiento_despues(api):
    db = SessionLocal()
    try:
        analisis_id, _ = analisis_service.crear_analisis(db, entrada_base())
        valor_en_creacion = db.get(models.Analisis, analisis_id).parametros_aplicados[
            "capital"]["coste_capital_anual"]
        assert valor_en_creacion == 0.015   # valor de defaults.yaml, sin overrides todavía

        conocimiento_service.set_parametro(
            db, "capital.coste_capital_anual", 0.5, fuente_legal=None, quien="test")

        analisis = db.get(models.Analisis, analisis_id)
        assert analisis.parametros_aplicados["capital"]["coste_capital_anual"] == 0.015
        assert analisis.parametros_aplicados["capital"]["coste_capital_anual"] != 0.5
    finally:
        # Revertir: set_parametro es un cambio real y permanente de gobernanza
        # T3 (misma clave+fecha => reemplaza, `conocimiento_service.py:48`) que
        # de lo contrario contaminaría el resto de tests de este módulo,
        # todos sobre la misma BD del fixture `api` (scope="module").
        conocimiento_service.set_parametro(
            db, "capital.coste_capital_anual", 0.015, fuente_legal=None, quien="test")
        db.close()


# ─────────────────────────── 5. Histórico sin snapshot permanece NULL ───────────────────────────

def test_analisis_historico_sin_snapshot_permanece_null(api):
    db = SessionLocal()
    try:
        # Simula un registro anterior a esta fase: se inserta directamente vía
        # el modelo, sin pasar por crear_analisis(), sin fijar parametros_aplicados.
        inp = entrada_base()
        historico = models.Analisis(
            perfil_codigo=inp.perfil, version_reglas="2026.07", version_parametros="2026.07",
            entrada={"perfil": inp.perfil}, hechos={}, resultado={"decision": {"semaforo": "verde"}},
        )
        db.add(historico)
        db.commit()

        releido = db.get(models.Analisis, historico.id)
        assert releido.parametros_aplicados is None
    finally:
        db.close()


# ─────────────────────────── 6. simular() conserva su contrato ───────────────────────────

def test_simular_conserva_contrato_publico(api):
    db = SessionLocal()
    try:
        inp = entrada_base()
        resultado_1 = analisis_service.simular(db, inp)
        resultado_2 = analisis_service.simular(db, inp)

        # Sigue devolviendo un AnalisisResult, con el mismo comportamiento
        # determinista de siempre (mismo caso base ya usado en test_api.py).
        assert resultado_1.decision.semaforo == "amarillo"
        assert resultado_1.model_dump() == resultado_2.model_dump()
    finally:
        db.close()


# ─────────────────────────── 7. Una sola resolución de conocimiento ───────────────────────────

def test_crear_analisis_resuelve_conocimiento_una_sola_vez(api):
    db = SessionLocal()
    try:
        with patch("app.services.analisis_service.conocimiento_service.cargar_conocimiento",
                  wraps=conocimiento_service.cargar_conocimiento) as espia:
            analisis_service.crear_analisis(db, entrada_base())

        assert espia.call_count == 1
    finally:
        db.close()


# ─────────────────────────── 8. Aislamiento del snapshot persistido ───────────────────────────

def test_snapshot_es_independiente_del_objeto_python(api):
    db = SessionLocal()
    try:
        analisis_id, _ = analisis_service.crear_analisis(db, entrada_base())
        snapshot_en_memoria = db.get(models.Analisis, analisis_id).parametros_aplicados
        snapshot_en_memoria["capital"]["coste_capital_anual"] = -999999   # mutación local
    finally:
        db.close()

    # Sesión completamente distinta: si el snapshot persistido estuviera
    # "vivo" en vez de ser un valor independiente, la mutación anterior se
    # vería aquí.
    db2 = SessionLocal()
    try:
        releido = db2.get(models.Analisis, analisis_id)
        assert releido.parametros_aplicados["capital"]["coste_capital_anual"] == 0.015
        assert releido.parametros_aplicados["capital"]["coste_capital_anual"] != -999999
    finally:
        db2.close()

"""Fase 3 — Trazabilidad de comparables: snapshot inmutable por análisis.

Antes de esta fase, los comparables usados por M03 solo sobrevivían dentro del
JSON de `Analisis.entrada` — no consultables, no relacionales. Estos tests
demuestran que `crear_analisis` persiste ahora un `ComparableUsado` por cada
elemento de `AnalisisInput.comparables`, en el mismo orden, sin filtrar ni
deduplicar (M03 usa el 100 % de lo recibido — ver `m03_valoracion.py` y la
verificación arquitectónica previa), y que ningún comportamiento de Fase 1
(puente captación→análisis) ni Fase 2 (corte sin ancla) cambia.

`api` se pide como fixture incluso en tests que no hacen peticiones HTTP:
garantiza que `Base.metadata.create_all` ya se ejecutó para este módulo —
mismo patrón que `tests/test_ingesta.py`.
"""
from __future__ import annotations

from app import models
from app.core.db import SessionLocal
from app.engine.contracts import (ActivoInput, AnalisisInput, ComparableInput,
                                  CostesInput, DocumentosInput, FinanciacionInput,
                                  OcupacionInput, ReformaInput, SubastaInput,
                                  ZonaInput, ZonaMacroInput, ZonaMicroInput)
from app.engine.pipeline import ejecutar_analisis
from app.services import analisis_service
from tests.conftest import entrada_base


def _filas(db, analisis_id: str) -> list[models.ComparableUsado]:
    return (db.query(models.ComparableUsado)
            .filter(models.ComparableUsado.analisis_id == analisis_id)
            .order_by(models.ComparableUsado.orden)
            .all())


# ───────────────────────── TEST 1 — N comparables ─────────────────────────

def test_n_comparables_produce_n_filas_en_orden_y_valores_correctos(api):
    db = SessionLocal()
    try:
        inp = entrada_base()  # 7 comparables (conftest.entrada_base)
        analisis_id, _ = analisis_service.crear_analisis(db, inp)
        filas = _filas(db, analisis_id)

        assert len(filas) == 7
        assert all(f.analisis_id == analisis_id for f in filas)
        for i, (f, c) in enumerate(zip(filas, inp.comparables)):
            assert f.orden == i
            assert float(f.precio_m2) == c.precio_m2
            assert f.estado == c.estado
            assert f.origen == c.origen
            assert float(f.meses_antiguedad) == c.meses_antiguedad
            assert f.superficie_m2 is None  # entrada_base no lo fija (opcional, contracts.py)
    finally:
        db.close()


# ───────────────────────── TEST 2 — sin comparables ─────────────────────────

def test_sin_comparables_cero_filas_sin_error_y_fase_2_intacta(api):
    db = SessionLocal()
    try:
        inp = entrada_base(comparables=[])
        analisis_id, resultado = analisis_service.crear_analisis(db, inp)

        assert _filas(db, analisis_id) == []
        # Fase 2 (corte sin ancla) sigue exactamente igual: no se ha tocado.
        assert resultado.valoracion.metodo == "sin_comparables"
        assert resultado.decision.semaforo == "rojo"
        assert "ancla de mercado" in " ".join(resultado.decision.razones).lower()
    finally:
        db.close()


# ───────────────────────── TEST 3 — duplicados ─────────────────────────

def test_duplicados_se_conservan_como_filas_independientes(api):
    c = ComparableInput(precio_m2=2200, estado="reformado", origen="testigo")
    db = SessionLocal()
    try:
        inp = entrada_base(comparables=[c, c])
        analisis_id, _ = analisis_service.crear_analisis(db, inp)
        filas = _filas(db, analisis_id)

        assert len(filas) == 2
        assert [f.orden for f in filas] == [0, 1]
        assert filas[0].precio_m2 == filas[1].precio_m2
        assert filas[0].estado == filas[1].estado == "reformado"
        assert filas[0].id != filas[1].id  # dos filas reales, no una compartida
    finally:
        db.close()


# ─────────────────────── TEST 4 — análisis repetidos ───────────────────────

def test_dos_analisis_con_los_mismos_comparables_no_comparten_snapshots(api):
    db = SessionLocal()
    try:
        inp = entrada_base()  # mismo objeto reutilizado a propósito: crear_analisis no lo muta
        id_a, _ = analisis_service.crear_analisis(db, inp)
        id_b, _ = analisis_service.crear_analisis(db, inp)

        assert id_a != id_b
        filas_a, filas_b = _filas(db, id_a), _filas(db, id_b)
        assert len(filas_a) == len(filas_b) == 7
        assert {f.id for f in filas_a}.isdisjoint({f.id for f in filas_b})
        assert all(f.analisis_id == id_a for f in filas_a)
        assert all(f.analisis_id == id_b for f in filas_b)
    finally:
        db.close()


# ───────────────────────── TEST 5 — puente Fase 1 ─────────────────────────

def test_puente_subasta_id_tambien_persiste_comparables_sin_romper_fase_1(api, headers):
    r = api.post("/api/v1/subastas", json={
        "fuente_codigo": "judicial_boe", "identificador_externo": "FASE3-PUENTE",
        "valor_subasta": 150000.0, "deposito_pct": 0.05,
    }, headers=headers)
    assert r.status_code == 201, r.text
    subasta_id = r.json()["id"]

    db = SessionLocal()
    try:
        subastas_antes = db.query(models.Subasta).count()
        inp = entrada_base()
        analisis_id, _ = analisis_service.crear_analisis(db, inp, subasta_id=subasta_id)

        assert analisis_id is not None
        filas = _filas(db, analisis_id)
        assert len(filas) == 7
        # Fase 1 intacta: sigue sin duplicar la Subasta reutilizada.
        assert db.query(models.Subasta).count() == subastas_antes
        activo = db.get(models.Analisis, analisis_id).activo_id
        assert db.get(models.Activo, activo).subasta_id == subasta_id
    finally:
        db.close()


# ───────────────────────── TEST 6 — caso dorado ─────────────────────────

def _caso_19() -> AnalisisInput:
    """Réplica exacta de la entrada de `tests/test_golden_caso19.py` (NO se toca
    ese fichero: es un test de persistencia aparte, sobre la misma entrada)."""
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


def test_caso_dorado_persiste_7_snapshots_y_el_resultado_no_cambia(api):
    """Pasa la misma entrada del caso dorado por `crear_analisis` (persistencia
    real) y compara contra `ejecutar_analisis` puro (lo que usa
    `test_golden_caso19.py`, sin tocarlo) para demostrar que la persistencia de
    comparables no altera ni un dígito del resultado del motor."""
    inp = _caso_19()
    referencia = ejecutar_analisis(inp)  # motor puro, sin BD — como el caso dorado

    db = SessionLocal()
    try:
        analisis_id, resultado = analisis_service.crear_analisis(db, inp)
        filas = _filas(db, analisis_id)

        assert len(filas) == 7
        assert [f.orden for f in filas] == list(range(7))
        assert all(f.analisis_id == analisis_id for f in filas)
        for f, c in zip(filas, inp.comparables):
            assert float(f.precio_m2) == c.precio_m2
            assert f.estado == c.estado
            assert f.origen == c.origen

        # Resultado numérico idéntico al del motor puro (regresión, Doc §19).
        assert resultado.decision.semaforo == referencia.decision.semaforo == "amarillo"
        assert resultado.decision.ico == referencia.decision.ico
        assert resultado.decision.ici == referencia.decision.ici
        assert resultado.decision.ra == referencia.decision.ra
        assert resultado.decision.precios.p_ideal == referencia.decision.precios.p_ideal
        assert resultado.decision.precios.p_objetivo == referencia.decision.precios.p_objetivo
        assert resultado.decision.precios.p_max == referencia.decision.precios.p_max
        assert resultado.decision.precios.p_limite == referencia.decision.precios.p_limite
        assert resultado.valoracion.vs == referencia.valoracion.vs
        assert resultado.valoracion.vm == referencia.valoracion.vm
        assert resultado.rentabilidad.roi == referencia.rentabilidad.roi
    finally:
        db.close()

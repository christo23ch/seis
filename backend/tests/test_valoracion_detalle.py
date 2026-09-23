"""Fase 4 — Trazabilidad de la valoración: intermedios de M03 persistidos.

Antes de esta fase, `m03_valoracion.ejecutar` calculaba por cada comparable un
precio ajustado, un normalizado y un peso — y los descartaba al retornar; solo
sobrevivían los agregados finales (VM, VS, método), opacos dentro del JSON de
`Analisis.resultado`. Estos tests demuestran que ahora esos intermedios se
persisten (`ComparableValorado`, 1:1 con cada `ComparableUsado` de Fase 3, y
`ValoracionAjustes`, 1:1 con `Analisis`), y que a partir de ellos se puede
reconstruir VM/VS/VT **sin volver a ejecutar M03** — el test de reconstrucción
bloquea `m03_valoracion.ejecutar` estructuralmente para probarlo.

`api` se pide como fixture incluso donde no hay peticiones HTTP: garantiza que
`Base.metadata.create_all` ya corrió para este módulo (mismo patrón que
`tests/test_ingesta.py` y `tests/test_comparables_usados.py`).
"""
from __future__ import annotations

from unittest.mock import patch

from app import models
from app.core.db import SessionLocal
from app.engine.contracts import (ActivoInput, AnalisisInput, ComparableInput,
                                  CostesInput, DocumentosInput, FinanciacionInput,
                                  OcupacionInput, ReformaInput, RentistaInput,
                                  SubastaInput, ZonaInput, ZonaMacroInput,
                                  ZonaMicroInput)
from app.engine.pipeline import ejecutar_analisis
from app.services import analisis_service
from tests.conftest import entrada_base


def _comparables_valorados(db, analisis_id: str) -> list[models.ComparableValorado]:
    return (db.query(models.ComparableValorado)
            .filter(models.ComparableValorado.analisis_id == analisis_id)
            .order_by(models.ComparableValorado.id).all())


def _comparables_usados(db, analisis_id: str) -> list[models.ComparableUsado]:
    return (db.query(models.ComparableUsado)
            .filter(models.ComparableUsado.analisis_id == analisis_id)
            .order_by(models.ComparableUsado.orden).all())


# ─────────────────────────── CASO 1 — caso normal ───────────────────────────

def test_caso_normal_filas_correspondencia_1a1_valores_orden_y_agregados(api):
    db = SessionLocal()
    try:
        inp = entrada_base()  # 7 comparables
        analisis_id, resultado = analisis_service.crear_analisis(db, inp)

        usados = _comparables_usados(db, analisis_id)
        valorados = _comparables_valorados(db, analisis_id)
        assert len(usados) == len(valorados) == 7

        # Correspondencia 1:1 real por comparable_usado_id, no solo por conteo.
        ids_usados = {u.id for u in usados}
        ids_en_valorados = {v.comparable_usado_id for v in valorados}
        assert ids_usados == ids_en_valorados

        detalle_motor = resultado.valoracion.detalle_comparables
        assert len(detalle_motor) == 7
        por_usado_id = {v.comparable_usado_id: v for v in valorados}
        for u, det in zip(usados, detalle_motor):  # mismo orden que inp.comparables
            v = por_usado_id[u.id]
            assert float(v.precio_ajustado_m2) == det.precio_ajustado_m2
            assert float(v.normalizado_m2) == det.normalizado_m2
            assert float(v.peso) == det.peso

        ajustes = db.get(models.ValoracionAjustes, analisis_id)
        assert ajustes is not None
        assert float(ajustes.k_estado_activo) == resultado.valoracion.k_estado_activo
        assert float(ajustes.ratio_sanidad) == resultado.valoracion.ratio_sanidad
        assert ajustes.vs_antes_de_capitalizacion is None  # no es perfil rentista
        assert ajustes.vs_capitalizacion is None

        # Agregados: VM/VS ya persistidos hoy (Analisis.resultado JSON); VT doble.
        analisis = db.get(models.Analisis, analisis_id)
        assert analisis.resultado["valoracion"]["vm"] == resultado.valoracion.vm
        assert analisis.resultado["valoracion"]["vs"] == resultado.valoracion.vs
        assert analisis.entrada["subasta"]["valor_subasta"] == inp.subasta.valor_subasta
    finally:
        db.close()


# ────────────────────── CASO 2 — vs_por_capitalizacion ──────────────────────

def test_vs_por_capitalizacion_desplazado_queda_accesible_y_coincide_con_m03(api):
    """Renta baja frente al valor de comparables ⇒ vs_cap < vs ⇒ override.
    Hoy solo quedaba la bandera de texto; ahora el VS desplazado y el que lo
    sustituyó quedan persistidos y verificables."""
    db = SessionLocal()
    try:
        inp = entrada_base(
            perfil="rentista",
            rentista=RentistaInput(renta_mensual_estimada=300, vacancia_pct=5,
                                   ibi_anual=400, comunidad_mensual=60, seguro_anual=300))
        referencia = ejecutar_analisis(inp)  # motor puro, para confirmar que el override SÍ se dispara
        assert "vs_por_capitalizacion" in referencia.valoracion.hechos
        assert referencia.valoracion.vs_antes_de_capitalizacion is not None
        assert referencia.valoracion.vs_capitalizacion is not None
        assert referencia.valoracion.vs_capitalizacion < referencia.valoracion.vs_antes_de_capitalizacion

        analisis_id, resultado = analisis_service.crear_analisis(db, inp)
        assert resultado.valoracion.vs == referencia.valoracion.vs  # el VS final es el capitalizado

        ajustes = db.get(models.ValoracionAjustes, analisis_id)
        assert ajustes is not None
        assert float(ajustes.vs_antes_de_capitalizacion) == referencia.valoracion.vs_antes_de_capitalizacion
        assert float(ajustes.vs_capitalizacion) == referencia.valoracion.vs_capitalizacion
        assert float(ajustes.vs_capitalizacion) == resultado.valoracion.vs
        assert float(ajustes.vs_antes_de_capitalizacion) > float(ajustes.vs_capitalizacion)
    finally:
        db.close()


# ─────────────────────────── CASO 3 — sin comparables ───────────────────────

def test_sin_comparables_no_crea_detalles_y_fase_2_intacta(api):
    db = SessionLocal()
    try:
        inp = entrada_base(comparables=[])
        analisis_id, resultado = analisis_service.crear_analisis(db, inp)

        assert _comparables_valorados(db, analisis_id) == []
        assert db.get(models.ValoracionAjustes, analisis_id) is None  # no "detalles inexistentes"

        # Fase 2 (corte sin ancla) sin cambios.
        assert resultado.valoracion.metodo == "sin_comparables"
        assert resultado.decision.semaforo == "rojo"
        assert "ancla de mercado" in " ".join(resultado.decision.razones).lower()
        assert resultado.valoracion.k_estado_activo is None
        assert resultado.valoracion.detalle_comparables == []
    finally:
        db.close()


# ─────────────────────────── CASO 4 — duplicados ───────────────────────────

def test_duplicados_producen_detalles_independientes_sin_deduplicar(api):
    c = ComparableInput(precio_m2=2200, estado="reformado", origen="testigo")
    db = SessionLocal()
    try:
        inp = entrada_base(comparables=[c, c])
        analisis_id, resultado = analisis_service.crear_analisis(db, inp)

        valorados = _comparables_valorados(db, analisis_id)
        assert len(valorados) == 2
        assert valorados[0].id != valorados[1].id
        assert valorados[0].comparable_usado_id != valorados[1].comparable_usado_id
        # Mismo comparable de entrada ⇒ mismo normalizado/peso en ambas filas.
        assert valorados[0].normalizado_m2 == valorados[1].normalizado_m2
        assert valorados[0].peso == valorados[1].peso
        assert len(resultado.valoracion.detalle_comparables) == 2
    finally:
        db.close()


# ───────────────────────── CASO 5 — análisis repetidos ──────────────────────

def test_dos_analisis_con_los_mismos_comparables_no_comparten_detalles(api):
    db = SessionLocal()
    try:
        inp = entrada_base()
        id_a, _ = analisis_service.crear_analisis(db, inp)
        id_b, _ = analisis_service.crear_analisis(db, inp)
        assert id_a != id_b

        valorados_a, valorados_b = _comparables_valorados(db, id_a), _comparables_valorados(db, id_b)
        assert len(valorados_a) == len(valorados_b) == 7
        assert {v.id for v in valorados_a}.isdisjoint({v.id for v in valorados_b})
        assert {v.comparable_usado_id for v in valorados_a}.isdisjoint(
            {v.comparable_usado_id for v in valorados_b})

        ajustes_a = db.get(models.ValoracionAjustes, id_a)
        ajustes_b = db.get(models.ValoracionAjustes, id_b)
        assert ajustes_a is not None and ajustes_b is not None
        assert ajustes_a.analisis_id != ajustes_b.analisis_id
    finally:
        db.close()


# ───────────────────────── CASO 6 — caso dorado (§19) ───────────────────────

def _caso_19() -> AnalisisInput:
    """Réplica exacta de la entrada de `tests/test_golden_caso19.py` (NO se
    toca ese fichero: es un test de persistencia aparte, sobre la misma
    entrada — mismo patrón ya usado en `test_comparables_usados.py`)."""
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


def test_caso_dorado_persiste_detalle_y_el_resultado_numerico_no_cambia(api):
    inp = _caso_19()
    referencia = ejecutar_analisis(inp)  # motor puro, sin BD — como el caso dorado

    db = SessionLocal()
    try:
        analisis_id, resultado = analisis_service.crear_analisis(db, inp)

        valorados = _comparables_valorados(db, analisis_id)
        assert len(valorados) == 7
        ajustes = db.get(models.ValoracionAjustes, analisis_id)
        assert ajustes is not None
        assert float(ajustes.k_estado_activo) == referencia.valoracion.k_estado_activo
        assert float(ajustes.ratio_sanidad) == referencia.valoracion.ratio_sanidad

        # El resultado numérico del motor no cambia por haber pasado por
        # persistencia — exactamente igual a la garantía ya probada en Fase 3.
        assert resultado.decision.semaforo == referencia.decision.semaforo == "amarillo"
        assert resultado.decision.ico == referencia.decision.ico
        assert resultado.valoracion.vm == referencia.valoracion.vm
        assert resultado.valoracion.vs == referencia.valoracion.vs
        assert resultado.decision.precios.p_objetivo == referencia.decision.precios.p_objetivo
    finally:
        db.close()


# ──────────────── RECONSTRUCCIÓN — sin volver a ejecutar M03 ────────────────

def test_reconstruccion_de_vm_vs_vt_sin_ejecutar_m03(api):
    """Dado un `analisis_id`, reconstruye VM/VS/VT aplicando la fórmula
    documentada sobre datos ya persistidos. `m03_valoracion.ejecutar` queda
    bloqueado con un mock durante la reconstrucción: si algo intentara
    recalcular llamando a M03, el test falla de inmediato."""
    db = SessionLocal()
    try:
        inp = entrada_base()
        analisis_id, resultado_original = analisis_service.crear_analisis(db, inp)
    finally:
        db.close()

    db = SessionLocal()
    try:
        with patch("app.engine.modules.m03_valoracion.ejecutar",
                   side_effect=AssertionError(
                       "la reconstrucción no debe volver a ejecutar M03")):
            analisis = db.get(models.Analisis, analisis_id)
            m2 = analisis.entrada["activo"]["superficie_m2"]
            vt_reconstruido = analisis.entrada["subasta"]["valor_subasta"]

            valorados = _comparables_valorados(db, analisis_id)
            ajustes = db.get(models.ValoracionAjustes, analisis_id)

            # Aplica la MISMA fórmula que `_mediana_ponderada` (función pura,
            # sin params ni I/O) sobre los normalizados/pesos ya persistidos —
            # no es "ejecutar M03", es aplicar su fórmula documentada a datos
            # guardados, tal como aprobó la propuesta G.
            from app.engine.modules.m03_valoracion import _mediana_ponderada
            normalizados = [float(v.normalizado_m2) for v in valorados]
            pesos = [float(v.peso) for v in valorados]
            vs_m2_reconstruido = _mediana_ponderada(normalizados, pesos)

            vs_reconstruido = round(vs_m2_reconstruido * m2, 2)
            vm_reconstruido = round(vs_m2_reconstruido * float(ajustes.k_estado_activo) * m2, 2)

        assert vt_reconstruido == inp.subasta.valor_subasta
        assert vs_reconstruido == resultado_original.valoracion.vs
        assert vm_reconstruido == resultado_original.valoracion.vm
    finally:
        db.close()

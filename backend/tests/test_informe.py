"""Fase 5F.3 — informe oficial: snapshot histórico e inmutable.

Sin HTTP: sesión directa, mismo patrón que `test_simulacion.py` y
`test_configuracion_validada.py`. `api` se pide solo para garantizar que
`Base.metadata.create_all` ya corrió para este módulo.
"""
from __future__ import annotations

from unittest.mock import patch

from app import models
from app.core.db import SessionLocal
from app.services import (analisis_service, conocimiento_service,
                          informe_service, simulacion_service)
from tests.conftest import entrada_base


def _crear_analisis(db, **overrides) -> str:
    analisis_id, _ = analisis_service.crear_analisis(db, entrada_base(**overrides))
    return analisis_id


def _simulacion_seleccionada(db, analisis_id, overrides) -> models.Simulacion:
    """Crea una simulación, la valida (lo que además la selecciona, Fase 5E)."""
    sim = simulacion_service.crear_simulacion(db, analisis_id, overrides)
    simulacion_service.validar_simulacion(db, analisis_id, sim.id)
    return sim


# ─────────────────── A. Informe desde la configuración original ───────────────────

def test_informe_desde_configuracion_original(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)

        informe = informe_service.generar_informe_oficial(db, analisis_id)

        assert informe.simulacion_id is None
        assert informe.overrides == {}
        assert informe.entrada_snapshot == analisis.entrada
        assert informe.parametros_aplicados == analisis.parametros_aplicados
        assert informe.resultado == analisis.resultado
        assert informe.analisis_id == analisis_id
        assert informe.generado_en is not None
    finally:
        db.close()


# ─────────────────── B. Informe desde una simulación validada ───────────────────

def test_informe_desde_simulacion_validada_copia_su_snapshot(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)
        sim = _simulacion_seleccionada(db, analisis_id, {"capital.coste_capital_anual": 0.5})
        simulacion_service.seleccionar_simulacion_validada(db, analisis_id, sim.id)

        informe = informe_service.generar_informe_oficial(db, analisis_id)

        assert informe.simulacion_id == sim.id
        assert informe.overrides == sim.overrides
        assert informe.parametros_aplicados == sim.parametros_aplicados
        assert informe.resultado == sim.resultado
        # La entrada del inmueble SIEMPRE es la del análisis: no se simula.
        assert informe.entrada_snapshot == analisis.entrada
        # Y el snapshot de la simulación es realmente distinto del original.
        assert informe.resultado != analisis.resultado
        assert informe.parametros_aplicados != analisis.parametros_aplicados
    finally:
        db.close()


# ─────────────────── C. No modifica el Analisis ───────────────────

def test_generar_informe_no_modifica_el_analisis(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = _simulacion_seleccionada(db, analisis_id, {"financiacion.dscr_minimo": 1.9})

        analisis = db.get(models.Analisis, analisis_id)
        antes = {
            "entrada": dict(analisis.entrada),
            "resultado": dict(analisis.resultado),
            "parametros_aplicados": dict(analisis.parametros_aplicados),
            "simulacion_validada_id": analisis.simulacion_validada_id,
            "version_reglas": analisis.version_reglas,
            "version_parametros": analisis.version_parametros,
        }
        assert antes["simulacion_validada_id"] == sim.id

        informe_service.generar_informe_oficial(db, analisis_id)

        db.expire_all()
        despues = db.get(models.Analisis, analisis_id)
        assert despues.entrada == antes["entrada"]
        assert despues.resultado == antes["resultado"]
        assert despues.parametros_aplicados == antes["parametros_aplicados"]
        assert despues.simulacion_validada_id == antes["simulacion_validada_id"]
        assert despues.version_reglas == antes["version_reglas"]
        assert despues.version_parametros == antes["version_parametros"]
    finally:
        db.close()


# ─────────────────── D. No modifica la Simulacion ───────────────────

def test_generar_informe_no_modifica_la_simulacion(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = _simulacion_seleccionada(db, analisis_id, {"capital.coste_capital_anual": 0.33})
        antes = {
            "estado": sim.estado,
            "fecha_validacion": sim.fecha_validacion,
            "overrides": dict(sim.overrides),
            "parametros_aplicados": dict(sim.parametros_aplicados),
            "resultado": dict(sim.resultado),
        }

        informe_service.generar_informe_oficial(db, analisis_id)

        db.expire_all()
        despues = db.get(models.Simulacion, sim.id)
        assert despues.estado == antes["estado"] == "validada"
        assert despues.fecha_validacion == antes["fecha_validacion"]
        assert despues.overrides == antes["overrides"]
        assert despues.parametros_aplicados == antes["parametros_aplicados"]
        assert despues.resultado == antes["resultado"]
    finally:
        db.close()


# ─────────────────── E. Inmutabilidad práctica ───────────────────

def test_informe_inmutable_ante_cambios_posteriores(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim1 = _simulacion_seleccionada(db, analisis_id, {"capital.coste_capital_anual": 0.11})

        informe = informe_service.generar_informe_oficial(db, analisis_id)
        congelado = {
            "entrada_snapshot": dict(informe.entrada_snapshot),
            "parametros_aplicados": dict(informe.parametros_aplicados),
            "overrides": dict(informe.overrides),
            "resultado": dict(informe.resultado),
            "simulacion_id": informe.simulacion_id,
        }
        informe_id = informe.id

        # 1. Cambia la gobernanza T3 global.
        conocimiento_service.set_parametro(
            db, "capital.coste_capital_anual", 0.95, fuente_legal=None, quien="test")
        # 2. Cambia un perfil de inversión.
        db.add(models.PerfilInversion(
            codigo="flip_integral", nombre="Perfil alterado",
            parametros={"tipo": "venta", "m_objetivo": 0.9, "m_minimo": 0.5,
                       "rvc_veto": 0.80, "piso_pesimista_frac_i": 0.0}))
        db.commit()
        # 3. Nace otra simulación y pasa a ser la configuración seleccionada.
        sim2 = _simulacion_seleccionada(db, analisis_id, {"financiacion.dscr_minimo": 1.7})
        assert db.get(models.Analisis, analisis_id).simulacion_validada_id == sim2.id

        db.expire_all()
        releido = db.get(models.Informe, informe_id)
        assert releido.entrada_snapshot == congelado["entrada_snapshot"]
        assert releido.parametros_aplicados == congelado["parametros_aplicados"]
        assert releido.overrides == congelado["overrides"]
        assert releido.resultado == congelado["resultado"]
        assert releido.simulacion_id == congelado["simulacion_id"] == sim1.id
        # El parámetro que cambió globalmente sigue con su valor histórico.
        assert releido.parametros_aplicados["capital"]["coste_capital_anual"] == 0.11
    finally:
        # Revertir la gobernanza: `set_parametro` es un cambio real y permanente
        # sobre la BD del módulo (misma clave+fecha reemplaza), y contaminaría
        # los tests posteriores de este fichero.
        conocimiento_service.set_parametro(
            db, "capital.coste_capital_anual", 0.015, fuente_legal=None, quien="test")
        db.query(models.PerfilInversion).filter_by(codigo="flip_integral").delete()
        db.commit()
        db.close()


# ─────────────────── F. Múltiples informes coexistiendo ───────────────────

def test_multiples_informes_coexisten_e_independientes(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        i1 = informe_service.generar_informe_oficial(db, analisis_id)   # original
        i1_congelado = dict(i1.resultado)
        assert i1.simulacion_id is None

        s1 = _simulacion_seleccionada(db, analisis_id, {"capital.coste_capital_anual": 0.21})
        i2 = informe_service.generar_informe_oficial(db, analisis_id)

        s2 = _simulacion_seleccionada(db, analisis_id, {"financiacion.dscr_minimo": 1.55})
        i3 = informe_service.generar_informe_oficial(db, analisis_id)

        informes = (db.query(models.Informe)
                    .filter(models.Informe.analisis_id == analisis_id).all())
        assert len(informes) == 3
        assert {i.id for i in informes} == {i1.id, i2.id, i3.id}
        assert i2.simulacion_id == s1.id
        assert i3.simulacion_id == s2.id

        # Emitir I2 e I3 no tocó a I1.
        db.expire_all()
        assert db.get(models.Informe, i1.id).resultado == i1_congelado
        assert db.get(models.Informe, i1.id).simulacion_id is None
    finally:
        db.close()


# ─────────────────── G. Reemisión sobre la misma configuración ───────────────────

def test_reemision_sobre_la_misma_configuracion_permitida(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        primero = informe_service.generar_informe_oficial(db, analisis_id)
        segundo = informe_service.generar_informe_oficial(db, analisis_id)

        assert primero.id != segundo.id
        assert primero.simulacion_id == segundo.simulacion_id is None
        assert primero.resultado == segundo.resultado
        assert db.query(models.Informe).filter_by(analisis_id=analisis_id).count() == 2
    finally:
        db.close()


# ─────────────────── H. Pertenencia cruzada ───────────────────

def test_pertenencia_cruzada_rechazada(api):
    """El puntero de configuración solo puede corromperse por escritura directa
    (los servicios de 5E/5E.1 ya comprueban pertenencia), pero
    `obtener_configuracion_actual` resuelve el puntero por id SIN comprobarla.
    Sin este guardián, el informe copiaría el resultado de otro análisis."""
    db = SessionLocal()
    try:
        analisis_a = _crear_analisis(db)
        analisis_b = _crear_analisis(db)
        sim_de_b = _simulacion_seleccionada(db, analisis_b, {"capital.coste_capital_anual": 0.4})

        # Corrupción deliberada del puntero de A hacia una simulación de B.
        analisis = db.get(models.Analisis, analisis_a)
        analisis.simulacion_validada_id = sim_de_b.id
        db.commit()

        informes_antes = db.query(models.Informe).count()
        auditorias_antes = db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count()
        try:
            informe_service.generar_informe_oficial(db, analisis_a)
            assert False, "no debía emitir un informe con una simulación ajena"
        except simulacion_service.PertenenciaCruzadaError as exc:
            assert exc.simulacion_id == sim_de_b.id
            assert exc.analisis_id == analisis_a

        # El rechazo ocurre ANTES de cualquier persistencia: ni informe, ni
        # auditoría. Comprobar solo la tabla `informe` dejaría sin cubrir que
        # pudiera quedar un evento de auditoría de un informe que no existe.
        assert db.query(models.Informe).count() == informes_antes
        assert db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count() == auditorias_antes
    finally:
        db.close()


# ─────────────────── I. Puntero a simulación inexistente ───────────────────

def test_puntero_invalido_rechaza_la_emision(api):
    """Fase 5F.4 — cambio deliberado de signo respecto a 5F.3.

    `obtener_configuracion_actual` sigue degradando a la configuración
    original ante un puntero roto, y eso es correcto para LEER: los cuatro
    endpoints de configuración actual mantienen esa semántica intacta.

    Pero EMITIR un informe sobre esa degradación produciría un documento que
    afirma «generado desde la configuración original» cuando sí había una
    simulación seleccionada: una afirmación histórica falsa. La emisión se
    rechaza y no persiste nada.
    """
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        analisis = db.get(models.Analisis, analisis_id)
        analisis.simulacion_validada_id = "id-que-no-existe"
        db.commit()

        informes_antes = db.query(models.Informe).count()
        auditorias_antes = db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count()

        try:
            informe_service.generar_informe_oficial(db, analisis_id)
            assert False, "no debía emitir sobre una configuración inconsistente"
        except informe_service.ConfiguracionInconsistenteError as exc:
            assert exc.analisis_id == analisis_id
            assert exc.simulacion_id == "id-que-no-existe"

        assert db.query(models.Informe).count() == informes_antes
        assert db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count() == auditorias_antes

        # La LECTURA de configuración actual conserva su comportamiento.
        config = simulacion_service.obtener_configuracion_actual(db, analisis_id)
        assert config.simulacion_id is None
        assert config.resultado == analisis.resultado
    finally:
        db.close()


def test_analisis_inexistente_rechazado(api):
    db = SessionLocal()
    try:
        try:
            informe_service.generar_informe_oficial(db, "no-existe")
            assert False, "debía fallar con análisis inexistente"
        except simulacion_service.AnalisisNoEncontradoError as exc:
            assert exc.analisis_id == "no-existe"
    finally:
        db.close()


# ─────────────────── J. Análisis anterior a la migración 0014 ───────────────────

def test_informe_de_analisis_sin_snapshot_de_parametros(api):
    """Un análisis anterior a 0014 no tiene `parametros_aplicados` y no es
    reconstruible (auditoría 5F.0). El informe se emite declarando la carencia
    con `NULL`, jamás rellenándola con los parámetros vigentes hoy."""
    db = SessionLocal()
    try:
        resultado_historico = {"decision": {"semaforo": "amarillo"},
                              "informe_markdown": "# Informe histórico"}
        historico = models.Analisis(
            perfil_codigo="flip_integral", version_reglas="2026.07",
            version_parametros="2026.07", entrada={"perfil": "flip_integral"},
            hechos={}, resultado=resultado_historico)
        db.add(historico)
        db.commit()
        assert historico.parametros_aplicados is None

        informe = informe_service.generar_informe_oficial(db, historico.id)

        assert informe.parametros_aplicados is None
        assert informe.resultado == resultado_historico
        assert informe.entrada_snapshot == {"perfil": "flip_integral"}
        assert informe.overrides == {}
        # Bajo ninguna circunstancia se han cargado los parámetros actuales.
        params_hoy, _, _ = conocimiento_service.cargar_conocimiento(db)
        assert informe.parametros_aplicados != params_hoy.raw()
    finally:
        db.close()


# ─────────────────── K/L. Auditoría ───────────────────

def test_auditoria_una_entrada_por_informe_con_simulacion(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        sim = _simulacion_seleccionada(db, analisis_id, {"capital.coste_capital_anual": 0.25})
        antes = db.query(models.Auditoria).filter_by(entidad="informe").count()

        informe = informe_service.generar_informe_oficial(
            db, analisis_id, usuario_id="usuario-uuid-1", quien="alguien@ejemplo.test")

        filas = (db.query(models.Auditoria)
                 .filter_by(entidad="informe", entidad_id=informe.id).all())
        assert len(filas) == 1
        assert db.query(models.Auditoria).filter_by(entidad="informe").count() == antes + 1

        fila = filas[0]
        assert fila.accion == "generar_oficial"
        assert fila.quien == "alguien@ejemplo.test"
        assert fila.delta == {"analisis_id": analisis_id, "simulacion_id": sim.id}
        # El correo va en `quien`, nunca en `delta` (el servicio de auditoría
        # veta datos personales ahí; que no haya lanzado ya lo demuestra).
        assert "@" not in str(fila.delta)
        # Y el informe guarda el id técnico, no el correo.
        assert informe.generado_por == "usuario-uuid-1"
    finally:
        db.close()


def test_auditoria_refleja_procedencia_original(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        informe = informe_service.generar_informe_oficial(db, analisis_id)

        fila = (db.query(models.Auditoria)
                .filter_by(entidad="informe", entidad_id=informe.id).one())
        assert fila.delta == {"analisis_id": analisis_id, "simulacion_id": None}
    finally:
        db.close()


# ─────────────────── 16. El informe es snapshot, no regenerador ───────────────────

def test_el_informe_congela_el_markdown_y_no_reejecuta_m14(api):
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        markdown_original = db.get(models.Analisis, analisis_id).resultado["informe_markdown"]
        assert markdown_original.startswith("# Informe de análisis SEIS")

        with patch("app.engine.modules.m14_informe.construir_informe") as m14_informe_mock, \
             patch("app.engine.modules.m14_informe.construir_checklist") as m14_checklist_mock, \
             patch("app.engine.pipeline.ejecutar_analisis") as pipeline_mock:
            informe = informe_service.generar_informe_oficial(db, analisis_id)

        assert m14_informe_mock.call_count == 0, "el informe no debe regenerar el Markdown"
        assert m14_checklist_mock.call_count == 0, "el informe no debe regenerar el checklist"
        assert pipeline_mock.call_count == 0, "el informe no debe reejecutar M01-M14"

        assert informe.resultado["informe_markdown"] == markdown_original
        assert informe.resultado["checklist"] == db.get(
            models.Analisis, analisis_id).resultado["checklist"]
    finally:
        db.close()


# ─────────────── Fase 5F.3.1 — atomicidad Informe + Auditoría (B-1) ───────────────

def test_fallo_de_auditoria_no_deja_informe_huerfano(api):
    """Reproduce el defecto B-1 que detectó la auditoría independiente.

    Antes de la corrección: `auditar` lanzaba, la excepción se propagaba, pero
    el INSERT ya volcado por el `flush` seguía vivo en la transacción abierta;
    si el llamador confirmaba esa sesión por cualquier otro motivo, el informe
    quedaba persistido SIN su evento de auditoría. Este test falla con la
    implementación antigua y pasa con el `rollback` explícito.
    """
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)
        informes_antes = db.query(models.Informe).count()
        auditorias_antes = db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count()

        with patch("app.services.informe_service.auditoria_service.auditar",
                  side_effect=RuntimeError("fallo de auditoría simulado")):
            try:
                informe_service.generar_informe_oficial(db, analisis_id)
                assert False, "la excepción debía propagarse, no convertirse en éxito"
            except RuntimeError as exc:
                assert "fallo de auditoría simulado" in str(exc)

        # El paso decisivo: el llamador confirma la sesión por otro motivo.
        db.commit()
    finally:
        db.close()

    # Sesión nueva: se comprueba lo que quedó REALMENTE en la base de datos.
    db2 = SessionLocal()
    try:
        assert db2.query(models.Informe).count() == informes_antes
        assert db2.query(models.Auditoria).filter_by(
            accion="generar_oficial").count() == auditorias_antes
    finally:
        db2.close()


def test_sesion_reutilizable_tras_el_fallo(api):
    """Tras el rollback la sesión queda limpia: una generación posterior sobre
    la misma sesión funciona con normalidad y sí deja su auditoría."""
    db = SessionLocal()
    try:
        analisis_id = _crear_analisis(db)

        with patch("app.services.informe_service.auditoria_service.auditar",
                  side_effect=RuntimeError("fallo de auditoría simulado")):
            try:
                informe_service.generar_informe_oficial(db, analisis_id)
            except RuntimeError:
                pass

        informe = informe_service.generar_informe_oficial(db, analisis_id)

        assert db.get(models.Informe, informe.id) is not None
        assert db.query(models.Auditoria).filter_by(
            entidad="informe", entidad_id=informe.id).count() == 1
    finally:
        db.close()


# ─────────────── Aislamiento por organización: comportamiento ACTUAL ───────────────

def test_servicio_interno_no_aisla_por_organizacion(api):
    """FIJA EL COMPORTAMIENTO ACTUAL, NO UNA GARANTÍA.

    `generar_informe_oficial` recibe solo `analisis_id` y no comprueba
    `organizacion_id`, igual que `crear_simulacion` y `validar_simulacion`
    (Fases 5D/5E). La Fase 5F.4 resolvió el aislamiento en la CAPA HTTP, no
    en el servicio: las cuatro rutas de `/informes` resuelven primero el
    análisis con `obtener_analisis(..., organizacion_id=...)`, que es
    fail-closed, y devuelven 404 ante un análisis ajeno. Ver
    `tests/test_informe_api.py`.

    La observación arquitectónica sigue viva y se conserva aquí a propósito:
    la capa de servicio no protege por sí misma, así que un futuro llamador
    interno (una tarea Celery, otro servicio) podría saltarse el aislamiento.
    Endurecerla exigiría hacerlo de forma uniforme en `simulacion_service` e
    `informe_service` a la vez, nunca solo en uno.
    """
    db = SessionLocal()
    try:
        org_a = models.Organizacion(nombre="Org A (informe)")
        org_b = models.Organizacion(nombre="Org B (informe)")
        db.add_all([org_a, org_b])
        db.commit()

        analisis_id, _ = analisis_service.crear_analisis(
            db, entrada_base(), organizacion_id=org_a.id)

        # La capa que SÍ aísla hoy rechaza el acceso desde la otra organización.
        assert analisis_service.obtener_analisis(
            db, analisis_id, organizacion_id=org_b.id) is None

        # El servicio interno, en cambio, no lo comprueba: pendiente de 5F.4.
        informe = informe_service.generar_informe_oficial(db, analisis_id)
        assert informe.analisis_id == analisis_id
    finally:
        db.close()

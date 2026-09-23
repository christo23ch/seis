"""Fase 5F.4 — API de informes oficiales.

Cubre la superficie HTTP: aislamiento por organización, IDOR entre análisis,
generación explícita, lectura histórica, PDF desde el Markdown congelado y
rechazo de configuración inconsistente.

La separación respecto a `test_informe.py` es deliberada y sigue la que ya
existe entre `test_simulacion.py` (servicio) y `test_api.py` (HTTP): aquí se
prueba lo que aporta la ruta, no lo que el servicio ya garantiza.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app import models
from app.core.db import SessionLocal
from app.services import informe_service, simulacion_service
from tests.conftest import ADMIN, entrada_base, token_headers


@pytest.fixture(scope="module")
def dos_orgs(api):
    """Org A y Org B, cada una con su analista (mismo montaje que
    `test_multitenant.py`), más un análisis propio por organización."""
    from app.services import usuario_service

    db = SessionLocal()
    try:
        org_a = usuario_service.crear_organizacion(db, "Org Informes A")
        usuario_service.crear_usuario(db, "informes-a@example.com", "claveA123", "Ana A",
                                      rol="analista", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
        org_b = usuario_service.crear_organizacion(db, "Org Informes B")
        usuario_service.crear_usuario(db, "informes-b@example.com", "claveB123", "Ana B",
                                      rol="analista", organizacion_id=org_b.id,
                                      rol_org="miembro", es_superadmin=False)
        usuario_service.crear_usuario(db, "lector-a@example.com", "claveL123", "Lector A",
                                      rol="lector", organizacion_id=org_a.id,
                                      rol_org="miembro", es_superadmin=False)
    finally:
        db.close()

    a_h = token_headers(api, "informes-a@example.com", "claveA123")
    b_h = token_headers(api, "informes-b@example.com", "claveB123")
    lector_h = token_headers(api, "lector-a@example.com", "claveL123")

    payload = json.loads(entrada_base().model_dump_json())
    id_a = api.post("/api/v1/analisis", json=payload, headers=a_h).json()["id"]
    id_b = api.post("/api/v1/analisis", json=payload, headers=b_h).json()["id"]
    return {"a_h": a_h, "b_h": b_h, "lector_h": lector_h, "id_a": id_a, "id_b": id_b}


def _generar(api, headers, analisis_id):
    r = api.post(f"/api/v1/analisis/{analisis_id}/informes", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ─────────────────────────── A. Aislamiento por organización ───────────────────────────

def test_usuario_puede_listar_informes_de_su_organizacion(api, dos_orgs):
    _generar(api, dos_orgs["a_h"], dos_orgs["id_a"])
    r = api.get(f"/api/v1/analisis/{dos_orgs['id_a']}/informes", headers=dos_orgs["a_h"])
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_cross_org_todas_las_rutas_devuelven_404(api, dos_orgs):
    """Nunca 403: eso confirmaría que el análisis existe."""
    informe = _generar(api, dos_orgs["a_h"], dos_orgs["id_a"])
    id_a, b_h = dos_orgs["id_a"], dos_orgs["b_h"]

    assert api.post(f"/api/v1/analisis/{id_a}/informes", headers=b_h).status_code == 404
    assert api.get(f"/api/v1/analisis/{id_a}/informes", headers=b_h).status_code == 404
    assert api.get(f"/api/v1/analisis/{id_a}/informes/{informe['id']}",
                   headers=b_h).status_code == 404
    assert api.get(f"/api/v1/analisis/{id_a}/informes/{informe['id']}/pdf",
                   headers=b_h).status_code == 404


def test_cross_org_no_genera_informe_en_el_analisis_ajeno(api, dos_orgs):
    db = SessionLocal()
    try:
        antes = db.query(models.Informe).filter_by(analisis_id=dos_orgs["id_a"]).count()
    finally:
        db.close()

    api.post(f"/api/v1/analisis/{dos_orgs['id_a']}/informes", headers=dos_orgs["b_h"])

    db = SessionLocal()
    try:
        assert db.query(models.Informe).filter_by(
            analisis_id=dos_orgs["id_a"]).count() == antes
    finally:
        db.close()


# ─────────────────────────── B. IDOR entre análisis ───────────────────────────

def test_informe_de_otro_analisis_no_es_recuperable(api, dos_orgs, headers):
    """El identificador de informe es global: sin guardián de pertenencia,
    `/analisis/A/informes/{informe-de-B}` devolvería el documento de B."""
    payload = json.loads(entrada_base().model_dump_json())
    id_1 = api.post("/api/v1/analisis", json=payload, headers=headers).json()["id"]
    id_2 = api.post("/api/v1/analisis", json=payload, headers=headers).json()["id"]
    informe_2 = _generar(api, headers, id_2)

    # Ambos análisis son de la MISMA organización: lo que bloquea aquí es el
    # guardián de pertenencia, no el aislamiento organizativo.
    r = api.get(f"/api/v1/analisis/{id_1}/informes/{informe_2['id']}", headers=headers)
    assert r.status_code == 404
    r_pdf = api.get(f"/api/v1/analisis/{id_1}/informes/{informe_2['id']}/pdf",
                    headers=headers)
    assert r_pdf.status_code == 404

    listado = api.get(f"/api/v1/analisis/{id_1}/informes", headers=headers).json()
    assert informe_2["id"] not in {i["id"] for i in listado}


def test_informe_inexistente_da_404(api, dos_orgs):
    r = api.get(f"/api/v1/analisis/{dos_orgs['id_a']}/informes/no-existe",
                headers=dos_orgs["a_h"])
    assert r.status_code == 404


# ─────────────────────────── C. Generación ───────────────────────────

def test_post_crea_un_informe_y_una_auditoria(api, dos_orgs):
    db = SessionLocal()
    try:
        informes_antes = db.query(models.Informe).count()
        auditorias_antes = db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count()
    finally:
        db.close()

    cuerpo = _generar(api, dos_orgs["a_h"], dos_orgs["id_a"])

    db = SessionLocal()
    try:
        assert db.query(models.Informe).count() == informes_antes + 1
        assert db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count() == auditorias_antes + 1

        informe = db.get(models.Informe, cuerpo["id"])
        usuario = db.query(models.Usuario).filter_by(email="informes-a@example.com").one()
        assert informe.generado_por == usuario.id          # id técnico, no correo

        fila = db.query(models.Auditoria).filter_by(
            entidad="informe", entidad_id=informe.id).one()
        assert fila.accion == "generar_oficial"
        assert fila.quien == "informes-a@example.com"       # actor legible
        assert "@" not in str(fila.delta)
    finally:
        db.close()


def test_post_no_modifica_el_analisis(api, dos_orgs):
    db = SessionLocal()
    try:
        antes = db.get(models.Analisis, dos_orgs["id_a"])
        resultado_antes = dict(antes.resultado)
        puntero_antes = antes.simulacion_validada_id
    finally:
        db.close()

    _generar(api, dos_orgs["a_h"], dos_orgs["id_a"])

    db = SessionLocal()
    try:
        despues = db.get(models.Analisis, dos_orgs["id_a"])
        assert despues.resultado == resultado_antes
        assert despues.simulacion_validada_id == puntero_antes
    finally:
        db.close()


# ─────────────────────────── D/E. Histórico y procedencia ───────────────────────────

def test_informes_conservan_su_procedencia_al_cambiar_de_configuracion(api, headers):
    payload = json.loads(entrada_base().model_dump_json())
    analisis_id = api.post("/api/v1/analisis", json=payload, headers=headers).json()["id"]

    i_original = _generar(api, headers, analisis_id)
    assert i_original["simulacion_id"] is None

    db = SessionLocal()
    try:
        s_a = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.31})
        simulacion_service.validar_simulacion(db, analisis_id, s_a.id)
    finally:
        db.close()
    i_a = _generar(api, headers, analisis_id)
    assert i_a["simulacion_id"] == s_a.id

    db = SessionLocal()
    try:
        # `capital.coste_capital_anual` y no `financiacion.dscr_minimo`: este
        # último solo actúa en la rama rentista, así que con un perfil de venta
        # no cambiaría el resultado y el test no probaría nada.
        s_b = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.62})
        simulacion_service.validar_simulacion(db, analisis_id, s_b.id)
    finally:
        db.close()
    i_b = _generar(api, headers, analisis_id)
    assert i_b["simulacion_id"] == s_b.id

    # Los tres coexisten y el primero no cambió al emitirse los siguientes.
    releido = api.get(f"/api/v1/analisis/{analisis_id}/informes/{i_original['id']}",
                      headers=headers).json()
    assert releido["simulacion_id"] is None
    assert releido["resultado"] == i_original["resultado"]
    assert releido["resultado"] != i_b["resultado"]

    listado = api.get(f"/api/v1/analisis/{analisis_id}/informes", headers=headers).json()
    assert {i["id"] for i in listado} >= {i_original["id"], i_a["id"], i_b["id"]}
    # Más reciente primero.
    fechas = [i["generado_en"] for i in listado]
    assert fechas == sorted(fechas, reverse=True)


# ─────────────────────────── F. Análisis anterior a 0014 ───────────────────────────

def test_informe_de_analisis_pre_0014_expone_parametros_nulos(api, dos_orgs):
    db = SessionLocal()
    try:
        org = db.query(models.Usuario).filter_by(
            email="informes-a@example.com").one().organizacion_id
        historico = models.Analisis(
            organizacion_id=org, perfil_codigo="flip_integral",
            version_reglas="2026.07", version_parametros="2026.07",
            entrada={"perfil": "flip_integral"}, hechos={},
            resultado={"decision": {"semaforo": "rojo"}, "informe_markdown": "# Viejo"})
        db.add(historico)
        db.commit()
        historico_id = historico.id
        assert historico.parametros_aplicados is None
    finally:
        db.close()

    cuerpo = _generar(api, dos_orgs["a_h"], historico_id)
    assert cuerpo["parametros_aplicados"] is None
    assert cuerpo["resultado"]["decision"]["semaforo"] == "rojo"

    detalle = api.get(f"/api/v1/analisis/{historico_id}/informes/{cuerpo['id']}",
                      headers=dos_orgs["a_h"]).json()
    assert detalle["parametros_aplicados"] is None


# ─────────────────────────── G. Configuración inconsistente ───────────────────────────

def test_configuracion_inconsistente_devuelve_409_sin_persistir(api, headers):
    payload = json.loads(entrada_base().model_dump_json())
    analisis_id = api.post("/api/v1/analisis", json=payload, headers=headers).json()["id"]

    db = SessionLocal()
    try:
        analisis = db.get(models.Analisis, analisis_id)
        analisis.simulacion_validada_id = "simulacion-que-no-existe"
        db.commit()
        informes_antes = db.query(models.Informe).count()
        auditorias_antes = db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count()
    finally:
        db.close()

    r = api.post(f"/api/v1/analisis/{analisis_id}/informes", headers=headers)
    assert r.status_code == 409, r.text

    db = SessionLocal()
    try:
        assert db.query(models.Informe).count() == informes_antes
        assert db.query(models.Auditoria).filter_by(
            accion="generar_oficial").count() == auditorias_antes
    finally:
        db.close()

    # Los endpoints de CONFIGURACIÓN ACTUAL conservan su semántica intacta.
    assert api.get(f"/api/v1/analisis/{analisis_id}", headers=headers).status_code == 200
    assert api.get(f"/api/v1/analisis/{analisis_id}/informe",
                   headers=headers).status_code == 200


# ─────────────────────────── H. PDF ───────────────────────────

def test_pdf_procede_del_markdown_congelado_y_no_ejecuta_m14(api, headers):
    payload = json.loads(entrada_base().model_dump_json())
    analisis_id = api.post("/api/v1/analisis", json=payload, headers=headers).json()["id"]
    informe = _generar(api, headers, analisis_id)
    markdown_congelado = informe["resultado"]["informe_markdown"]

    # La configuración actual pasa a ser otra, con un resultado distinto.
    db = SessionLocal()
    try:
        sim = simulacion_service.crear_simulacion(
            db, analisis_id, {"capital.coste_capital_anual": 0.6})
        simulacion_service.validar_simulacion(db, analisis_id, sim.id)
        assert sim.resultado["informe_markdown"] != markdown_congelado
        auditorias_antes = db.query(models.Auditoria).count()
    finally:
        db.close()

    with patch("app.engine.modules.m14_informe.construir_informe") as m14, \
         patch("app.engine.pipeline.ejecutar_analisis") as motor, \
         patch("app.services.pdf_service.informe_a_pdf",
               wraps=__import__("app.services.pdf_service", fromlist=["x"]).informe_a_pdf) as espia:
        r = api.get(f"/api/v1/analisis/{analisis_id}/informes/{informe['id']}/pdf",
                    headers=headers)

    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert informe["id"][:8] in r.headers["content-disposition"]
    assert m14.call_count == 0 and motor.call_count == 0
    # El PDF se construyó con el Markdown CONGELADO, no con el de la
    # configuración actual, que ahora es otra.
    espia.assert_called_once()
    assert espia.call_args[0][0] == markdown_congelado

    db = SessionLocal()
    try:
        assert db.query(models.Auditoria).count() == auditorias_antes   # GET no audita
    finally:
        db.close()


def test_get_no_genera_auditoria(api, dos_orgs):
    informe = _generar(api, dos_orgs["a_h"], dos_orgs["id_a"])
    db = SessionLocal()
    try:
        antes = db.query(models.Auditoria).count()
    finally:
        db.close()

    api.get(f"/api/v1/analisis/{dos_orgs['id_a']}/informes", headers=dos_orgs["a_h"])
    api.get(f"/api/v1/analisis/{dos_orgs['id_a']}/informes/{informe['id']}",
            headers=dos_orgs["a_h"])

    db = SessionLocal()
    try:
        assert db.query(models.Auditoria).count() == antes
    finally:
        db.close()


# ─────────────────────────── I. Fallo de auditoría vía HTTP ───────────────────────────

def test_fallo_de_auditoria_no_deja_informe_huerfano_via_http(api, dos_orgs):
    db = SessionLocal()
    try:
        informes_antes = db.query(models.Informe).count()
    finally:
        db.close()

    with patch("app.services.informe_service.auditoria_service.auditar",
              side_effect=RuntimeError("fallo de auditoría simulado")):
        try:
            api.post(f"/api/v1/analisis/{dos_orgs['id_a']}/informes",
                     headers=dos_orgs["a_h"])
        except RuntimeError:
            pass   # TestClient propaga la excepción del servidor

    db = SessionLocal()
    try:
        assert db.query(models.Informe).count() == informes_antes
    finally:
        db.close()


# ─────────────────────────── J. Autenticación y roles ───────────────────────────

def test_sin_autenticacion_401(api, dos_orgs):
    id_a = dos_orgs["id_a"]
    assert api.post(f"/api/v1/analisis/{id_a}/informes").status_code == 401
    assert api.get(f"/api/v1/analisis/{id_a}/informes").status_code == 401
    assert api.get(f"/api/v1/analisis/{id_a}/informes/x").status_code == 401
    assert api.get(f"/api/v1/analisis/{id_a}/informes/x/pdf").status_code == 401


def test_rol_lector_no_puede_generar_pero_si_leer(api, dos_orgs):
    id_a, lector_h = dos_orgs["id_a"], dos_orgs["lector_h"]

    assert api.post(f"/api/v1/analisis/{id_a}/informes",
                    headers=lector_h).status_code == 403

    informe = _generar(api, dos_orgs["a_h"], id_a)
    assert api.get(f"/api/v1/analisis/{id_a}/informes",
                   headers=lector_h).status_code == 200
    assert api.get(f"/api/v1/analisis/{id_a}/informes/{informe['id']}",
                   headers=lector_h).status_code == 200
    assert api.get(f"/api/v1/analisis/{id_a}/informes/{informe['id']}/pdf",
                   headers=lector_h).status_code == 200

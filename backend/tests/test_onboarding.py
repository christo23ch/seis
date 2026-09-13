"""La checklist de arranque: qué se deduce, qué se declara, y qué no se puede falsear.

LO QUE ESTOS TESTS **NO** CUBREN (ADR-0014):

- No comprueban que los cuatro pasos del catálogo sean los correctos para un
  usuario nuevo. Eso es una decisión de producto y ninguna prueba la valida.
- No cubren recordatorios: no existen todavía.
- No cubren concurrencia real. Se comprueba que marcar dos veces es idempotente,
  pero con dos peticiones simultáneas lo que salva la fila es la restricción de
  unicidad de la base, y eso solo se ejercita de verdad contra PostgreSQL.
- Van por la API y no por el servicio a propósito: así se prueba el contrato que
  consume el frontend, que es donde la Fase 14 descubrió que cada lado probaba
  contra su propia idea del contrato.
"""
from __future__ import annotations

from app.services import onboarding_service


def _paso(estado: dict, clave: str) -> dict:
    return next(p for p in estado["pasos"] if p["clave"] == clave)


def _estado(api, cab) -> dict:
    r = api.get("/api/v1/cuenta/onboarding", headers=cab)
    assert r.status_code == 200, r.text
    return r.json()


# ───────────────────────── el catálogo y su forma ─────────────────────────
def test_el_catalogo_distingue_pasos_deducidos_de_declarados():
    """Si todos fueran declarados, la checklist sería una lista de deseos."""
    assert any(p.deducido for p in onboarding_service.PASOS)
    assert any(not p.deducido for p in onboarding_service.PASOS)
    assert set(onboarding_service.CLAVES_MANUALES) < set(onboarding_service.CLAVES)


def test_la_checklist_trae_los_pasos_con_su_origen(api, headers):
    estado = _estado(api, headers)
    assert estado["total"] == len(onboarding_service.PASOS)
    assert {p["clave"] for p in estado["pasos"]} == set(onboarding_service.CLAVES)
    assert _paso(estado, "primer_analisis")["origen"] == "datos"
    assert _paso(estado, "como_funciona")["origen"] == "declarado"


# ────────────── lo deducido se lee de los datos, no de una marca ──────────────
def test_un_paso_deducido_no_se_puede_marcar_a_mano(api, headers):
    """Aceptar la marca sería dejar que alguien declare un hecho comprobable."""
    r = api.post("/api/v1/cuenta/onboarding/primer_analisis", headers=headers)
    assert r.status_code == 400
    assert "deduce" in r.json()["detail"]
    assert _paso(_estado(api, headers), "primer_analisis")["completado"] is False


def test_el_primer_analisis_se_deduce_de_los_datos_reales(api, headers, base_input):
    """El corazón del diseño: nadie declara que tiene un análisis. O está, o no."""
    assert _paso(_estado(api, headers), "primer_analisis")["completado"] is False

    r = api.post("/api/v1/analisis", json=base_input.model_dump(mode="json"), headers=headers)
    assert r.status_code in (200, 201), r.text

    assert _paso(_estado(api, headers), "primer_analisis")["completado"] is True


def test_una_clave_inventada_se_rechaza(api, headers):
    r = api.post("/api/v1/cuenta/onboarding/inventada", headers=headers)
    assert r.status_code == 400
    assert "desconocido" in r.json()["detail"]


# ───────────────────────── lo declarado se persiste ─────────────────────────
def test_marcar_un_paso_manual_lo_deja_hecho_y_sigue_hecho(api, headers):
    r = api.post("/api/v1/cuenta/onboarding/como_funciona", headers=headers)
    assert r.status_code == 200, r.text
    assert _paso(r.json(), "como_funciona")["completado"] is True
    assert _paso(r.json(), "como_funciona")["completado_en"] is not None
    # …y sigue hecho en una consulta nueva, que es lo que significa «persistida».
    assert _paso(_estado(api, headers), "como_funciona")["completado"] is True


def test_marcar_dos_veces_no_rompe_ni_duplica(api, headers):
    """Idempotente: la unicidad la impone la base, no el servicio."""
    api.post("/api/v1/cuenta/onboarding/perfil_revisado", headers=headers)
    r = api.post("/api/v1/cuenta/onboarding/perfil_revisado", headers=headers)
    assert r.status_code == 200, r.text
    assert _paso(r.json(), "perfil_revisado")["completado"] is True

    from app import models
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        assert db.query(models.PasoOnboarding).filter_by(clave="perfil_revisado").count() == 1
    finally:
        db.close()


# ───────────────────── aislamiento: la checklist es tuya ─────────────────────
def test_la_checklist_de_otro_usuario_no_se_mezcla(api, dos_organizaciones):
    """Un paso marcado por una persona no aparece hecho en la de otra."""
    a, b = dos_organizaciones["a_h"], dos_organizaciones["b_h"]
    assert api.post("/api/v1/cuenta/onboarding/como_funciona", headers=a).status_code == 200
    assert _paso(_estado(api, a), "como_funciona")["completado"] is True
    assert _paso(_estado(api, b), "como_funciona")["completado"] is False


def test_un_analisis_de_otra_organizacion_no_completa_tu_primer_analisis(
        api, dos_organizaciones, base_input):
    """Mismo aislamiento que el resto del producto: por organización."""
    a, b = dos_organizaciones["a_h"], dos_organizaciones["b_h"]
    r = api.post("/api/v1/analisis", json=base_input.model_dump(mode="json"), headers=a)
    assert r.status_code in (200, 201), r.text
    assert _paso(_estado(api, a), "primer_analisis")["completado"] is True
    assert _paso(_estado(api, b), "primer_analisis")["completado"] is False


# ─────────────────────────── superficie de la ruta ───────────────────────────
def test_la_checklist_exige_sesion(api):
    assert api.get("/api/v1/cuenta/onboarding").status_code == 401


def test_la_ruta_no_admite_un_usuario_ajeno(api):
    """No hay `{usuario_id}` en la ruta: no existe forma de pedir la de otro."""
    rutas = [r for r in api.app.openapi()["paths"] if "onboarding" in r]
    assert rutas and all("usuario_id" not in r for r in rutas)

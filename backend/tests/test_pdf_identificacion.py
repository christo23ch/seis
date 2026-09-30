"""Fase 5G.1 — identificación del informe oficial en el PDF (deuda D5).

Un PDF oficial impreso tiene que decir qué informe es: id, fecha de emisión,
procedencia, versiones de parámetros y reglas y número de overrides. Todo sale
de la fila `Informe`, que es inmutable: dos descargas del mismo informe deben
identificarlo igual hoy y dentro de un año, cambie lo que cambie la
configuración en uso o el conocimiento global. El PDF de la vista previa
(`/informe.pdf`) lleva en cambio la marca «VISTA PREVIA — NO OFICIAL».

El texto se extrae con `pypdf` (dependencia solo de tests). Cada test corre con
las DOS fuentes: Helvetica siempre —es la única que existe en Windows— y DejaVu
cuando está instalada, que es obligatorio en CI (mismo criterio que
`test_pdf_respaldo.py`).
"""
from __future__ import annotations

import io
import json
import os
import time
from datetime import datetime, timezone

import pytest
from pypdf import PdfReader

from app import models
from app.core.db import SessionLocal
from app.services import conocimiento_service, pdf_service, simulacion_service
from tests.conftest import ADMIN, entrada_base


# ─────────────────────────── utilidades ───────────────────────────

@pytest.fixture(params=["helvetica", "dejavu"])
def fuente(request, monkeypatch):
    """Fuerza la fuente del PDF. Helvetica corre siempre; DejaVu se omite
    fuera de CI si no está instalada y FALLA en CI si falta."""
    if request.param == "helvetica":
        monkeypatch.setattr(pdf_service, "_DEJAVU", pdf_service.Path("/ruta/que/no/existe"))
        return False
    if not (pdf_service._DEJAVU / "DejaVuSans.ttf").exists():
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            pytest.fail("DejaVu ausente en CI: la rama con fuente ha dejado de probarse")
        pytest.skip("DejaVu no instalada en esta máquina (sí lo está en CI)")
    return True


def _paginas(pdf: bytes) -> list[str]:
    """Texto de cada página con los espacios normalizados."""
    return [" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(pdf)).pages]


def _esperado(texto: str, unicode_ok: bool) -> str:
    """Lo que debe aparecer impreso: el texto pasado por el mismo saneador que
    el PDF (con Helvetica, «—» se translitera a «-»)."""
    return " ".join(pdf_service._limpiar(texto, unicode_ok).split())


def _fecha_utc(iso: str) -> str:
    fecha = datetime.fromisoformat(iso)
    fecha = fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)
    return fecha.strftime("%Y-%m-%d %H:%M:%S UTC")


def _crear_analisis(api, headers) -> str:
    payload = json.loads(entrada_base().model_dump_json())
    r = api.post("/api/v1/analisis", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _emitir(api, headers, analisis_id) -> dict:
    r = api.post(f"/api/v1/analisis/{analisis_id}/informes", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _pdf_oficial(api, headers, analisis_id, informe_id) -> bytes:
    r = api.get(f"/api/v1/analisis/{analisis_id}/informes/{informe_id}/pdf", headers=headers)
    assert r.status_code == 200, r.text
    return r.content


def _validar_simulacion(analisis_id, overrides) -> str:
    db = SessionLocal()
    try:
        sim = simulacion_service.crear_simulacion(db, analisis_id, overrides)
        simulacion_service.validar_simulacion(db, analisis_id, sim.id)
        return sim.id
    finally:
        db.close()


# ─────────────────────────── A. Contenido de la identificación ───────────────────────────

def test_pdf_oficial_lleva_id_fecha_procedencia_y_versiones(api, headers, fuente):
    analisis_id = _crear_analisis(api, headers)
    informe = _emitir(api, headers, analisis_id)
    decision = informe["resultado"]["decision"]

    texto = " ".join(_paginas(_pdf_oficial(api, headers, analisis_id, informe["id"])))

    assert "INFORME OFICIAL" in texto
    assert informe["id"] in texto
    assert _fecha_utc(informe["generado_en"]) in texto
    assert _esperado("Procedencia: Configuración original", fuente) in texto
    assert _esperado(f"Versión de parámetros: {decision['version_parametros']}", fuente) in texto
    assert _esperado(f"Versión de reglas: {decision['version_reglas']}", fuente) in texto
    assert "Overrides aplicados: 0" in texto
    assert "Sin snapshot" not in texto


def test_la_identificacion_aparece_en_todas_las_paginas_sin_partirse(api, headers, fuente):
    """El pie lleva el id completo en cada página. Si se partiera en dos
    líneas o se saliera del margen, el id no aparecería contiguo."""
    analisis_id = _crear_analisis(api, headers)
    informe = _emitir(api, headers, analisis_id)

    paginas = _paginas(_pdf_oficial(api, headers, analisis_id, informe["id"]))

    assert len(paginas) >= 2, "el caso de prueba debería ocupar varias páginas"
    for n, pagina in enumerate(paginas, start=1):
        assert informe["id"] in pagina, f"falta el id en la página {n}"
        assert _esperado("Informe oficial", fuente) in pagina
        assert _esperado(f"página {n}", fuente) in pagina


def test_el_pie_cabe_en_el_ancho_util(fuente):
    """El caso más largo que puede darse: id completo + simulación + página 999."""
    ident = pdf_service.identificacion_oficial(models.Informe(
        id="0" * 36, analisis_id="a", simulacion_id="f" * 36, overrides={"x": 1},
        parametros_aplicados={}, resultado={"decision": {}},
        generado_en=datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)))
    pdf = pdf_service._InformePDF(ident)

    tamano = pdf._tamano_pie(ident.pie.format(n=999))

    assert tamano >= pdf_service.TAMANO_PIE_MINIMO
    pdf.set_font(pdf.familia, "", tamano)
    assert pdf.get_string_width(pdf_service._limpiar(ident.pie.format(n=999), fuente)) <= pdf.epw


# ─────────────────────────── B. Procedencia ───────────────────────────

def test_procedencia_de_una_simulacion(api, headers, fuente):
    analisis_id = _crear_analisis(api, headers)
    sim_id = _validar_simulacion(analisis_id, {"capital.coste_capital_anual": 0.4})
    informe = _emitir(api, headers, analisis_id)
    assert informe["simulacion_id"] == sim_id

    texto = " ".join(_paginas(_pdf_oficial(api, headers, analisis_id, informe["id"])))

    assert _esperado(f"Procedencia: Simulación {sim_id[:8]}", fuente) in texto
    assert sim_id in texto                        # el id completo, en el bloque inicial
    assert "Overrides aplicados: 1" in texto
    assert _esperado("Configuración original", fuente) not in texto


# ─────────────────────────── C. Estabilidad ───────────────────────────

def test_dos_descargas_identifican_igual_aunque_cambie_todo_entre_medias(api, headers, fuente):
    analisis_id = _crear_analisis(api, headers)
    informe = _emitir(api, headers, analisis_id)
    primera = _pdf_oficial(api, headers, analisis_id, informe["id"])

    # Entre medias cambian la configuración en uso y el conocimiento global.
    _validar_simulacion(analisis_id, {"capital.coste_capital_anual": 0.5})
    db = SessionLocal()
    try:
        conocimiento_service.set_parametro(db, "capital.coste_capital_anual", 0.33, None, "test-5g1")
    finally:
        db.close()
    try:
        segunda = _pdf_oficial(api, headers, analisis_id, informe["id"])
    finally:
        db = SessionLocal()   # el conocimiento global se restaura para el resto del módulo
        try:
            db.query(models.Parametro).filter_by(clave="capital.coste_capital_anual").delete()
            db.commit()
        finally:
            db.close()

    assert _paginas(primera) == _paginas(segunda)
    assert _esperado("Procedencia: Configuración original", fuente) in " ".join(_paginas(segunda))


def test_dos_descargas_son_identicas_byte_a_byte(api, headers, fuente):
    """La fecha de creación del PDF es la de emisión, no la de descarga."""
    analisis_id = _crear_analisis(api, headers)
    informe = _emitir(api, headers, analisis_id)

    primera = _pdf_oficial(api, headers, analisis_id, informe["id"])
    # Sin esta espera, dos descargas en el mismo segundo coincidirían aunque la
    # fecha de los metadatos fuese la de descarga: el test pasaría por suerte.
    time.sleep(1.1)
    segunda = _pdf_oficial(api, headers, analisis_id, informe["id"])

    assert primera == segunda


def test_el_markdown_congelado_no_cambia(api, headers):
    analisis_id = _crear_analisis(api, headers)
    informe = _emitir(api, headers, analisis_id)
    markdown = informe["resultado"]["informe_markdown"]

    _pdf_oficial(api, headers, analisis_id, informe["id"])

    detalle = api.get(f"/api/v1/analisis/{analisis_id}/informes/{informe['id']}",
                      headers=headers).json()
    assert detalle["resultado"]["informe_markdown"] == markdown
    assert "INFORME OFICIAL" not in markdown
    db = SessionLocal()
    try:
        assert db.get(models.Informe, informe["id"]).resultado["informe_markdown"] == markdown
    finally:
        db.close()


# ─────────────────────────── D. Vista previa ───────────────────────────

def test_la_vista_previa_se_marca_como_no_oficial_y_el_oficial_no(api, headers, fuente):
    analisis_id = _crear_analisis(api, headers)
    informe = _emitir(api, headers, analisis_id)
    marca = _esperado(pdf_service.MARCA_VISTA_PREVIA, fuente)

    r = api.get(f"/api/v1/analisis/{analisis_id}/informe.pdf", headers=headers)
    assert r.status_code == 200
    previa = _paginas(r.content)
    oficial = " ".join(_paginas(_pdf_oficial(api, headers, analisis_id, informe["id"])))

    for n, pagina in enumerate(previa, start=1):
        assert marca in pagina, f"falta la marca en la página {n} de la vista previa"
    assert "INFORME OFICIAL" not in " ".join(previa)
    assert marca not in oficial
    assert "NO OFICIAL" not in oficial


# ─────────────────────────── E. Informe anterior a 0014 ───────────────────────────

def test_informe_sin_snapshot_de_parametros_genera_pdf_y_lo_declara(api, headers, fuente):
    db = SessionLocal()
    try:
        org = db.query(models.Usuario).filter_by(email=ADMIN["username"]).one().organizacion_id
        historico = models.Analisis(
            organizacion_id=org, perfil_codigo="flip_integral",
            version_reglas="2026.07", version_parametros="2026.07",
            entrada={"perfil": "flip_integral"}, hechos={},
            resultado={"decision": {"semaforo": "rojo"}, "informe_markdown": "# Viejo\n\nTexto."})
        db.add(historico)
        db.commit()
        historico_id = historico.id
    finally:
        db.close()
    informe = _emitir(api, headers, historico_id)
    assert informe["parametros_aplicados"] is None

    texto = " ".join(_paginas(_pdf_oficial(api, headers, historico_id, informe["id"])))

    assert informe["id"] in texto
    assert _esperado("Sin snapshot de parámetros", fuente) in texto
    # El resultado histórico no trae versiones: se dice, no se buscan fuera.
    assert _esperado("Versión de parámetros: no consta", fuente) in texto
    assert _esperado("Versión de reglas: no consta", fuente) in texto

"""Fase 17-A — Parser del BOE: contrato defensivo.

El HTML de aquí es **sintético**: su estructura es plausible, no verificada
contra subastas.boe.es. Ajustar los selectores contra el portal real es la Fase
17-B. Lo que estos tests fijan no son los selectores, sino lo que no cambiará
cuando lleguen los buenos: que el parser **nunca lanza**, que un ítem ilegible se
cuenta y se describe en vez de tumbar el documento, y que los importes y fechas
se leen en formato español —confundir el separador convierte 152.000 € en 152 €,
que es un error silencioso y caro porque pasa cualquier filtro de valor máximo.
"""
from __future__ import annotations

import pytest

from app.ingesta import boe


# ─────────────────────── Fixtures de HTML sintético ───────────────────────

def _item(identificador: str, valor: str, extra: str = "") -> str:
    return f"""
      <div class="subasta-item">
        <span>Identificador: {identificador}</span>
        <span>Valor subasta: {valor}</span>
        <span>Puja mínima: 90.000,00 €</span>
        <span>Importe del depósito: 7.600,00 €</span>
        <span>Localidad: Ciudad Ejemplo</span>
        <span>Provincia: Ejemplo</span>
        <span>Tipo de bien: Vivienda</span>
        <span>Fecha de conclusión: 31-12-2026</span>
        {extra}
      </div>"""


def _listado(*items: str) -> str:
    return f"<html><body><main>{''.join(items)}</main></body></html>"


# ─────────────────────────── Parser: nunca lanza ───────────────────────────

def test_parsea_un_listado_con_varios_items():
    html = _listado(_item("SUB-001", "152.000,00 €"), _item("SUB-002", "98.500,50 €"))

    subastas, motivos = boe.parsear_listado(html)

    assert [s.identificador_externo for s in subastas] == ["SUB-001", "SUB-002"]
    assert subastas[0].valor_subasta == 152000.0
    assert subastas[1].valor_subasta == 98500.5
    assert motivos == []


@pytest.mark.parametrize("html", [
    "",
    "   ",
    "<html><body>no hay nada aquí</body></html>",
    "<div class='subasta-item'><span>Identificador: X</span></div>",   # sin valor
    "<<<>>> esto no es html <<<",
    "<html><body><div class='subasta-item'>" + "<span>" * 500,          # anidamiento absurdo
])
def test_un_html_ilegible_devuelve_lista_vacia_y_nunca_lanza(html):
    """El contrato del módulo: la ingesta nocturna no puede caerse por el HTML.

    Un portal que cambia una etiqueta, devuelve una página de error o corta la
    respuesta a la mitad debe producir cero subastas y un motivo, no una traza.
    """
    subastas, _motivos = boe.parsear_listado(html)
    assert subastas == []


def test_un_item_roto_no_impide_parsear_los_demas():
    """Es la diferencia entre ingerir 1 de 2 e ingerir 0 de 2."""
    html = _listado(_item("SUB-OK", "152.000,00 €"),
                    "<div class='subasta-item'><span>Identificador: SUB-MALA</span></div>")

    subastas, motivos = boe.parsear_listado(html)

    assert [s.identificador_externo for s in subastas] == ["SUB-OK"]
    assert len(motivos) == 1 and "sin valor" in motivos[0]


@pytest.mark.parametrize("texto,esperado", [
    ("152.000,00 €", 152000.0),
    ("152.000 €", 152000.0),
    ("1.234.567,89 €", 1234567.89),
    ("98,50", 98.5),
    ("sin importe", None),
    (None, None),
])
def test_los_importes_se_leen_en_formato_espanol(texto, esperado):
    """Confundir el separador convierte 152.000 € en 152 €.

    No es un error cosmético: una subasta de 152 € pasa cualquier filtro de
    alerta por valor máximo y dispara notificaciones a todo el mundo.
    """
    assert boe.importe_es(texto) == esperado


@pytest.mark.parametrize("texto,anio,mes,dia", [
    ("31-12-2026", 2026, 12, 31),
    ("01/06/2027", 2027, 6, 1),
])
def test_las_fechas_se_leen_en_formato_espanol(texto, anio, mes, dia):
    f = boe.fecha_es(texto)
    assert (f.year, f.month, f.day) == (anio, mes, dia)


@pytest.mark.parametrize("texto", ["31-02-2026", "no es fecha", "", None])
def test_una_fecha_imposible_es_none_y_no_una_excepcion(texto):
    assert boe.fecha_es(texto) is None


def test_los_selectores_salen_de_los_parametros_t3():
    """La Fase 17-B debe poder ajustar el portal sin desplegar código."""
    class ParamsFalsos:
        def get(self, clave):
            return {"ingesta.boe.marca_item": "otra-marca",
                    "ingesta.boe.etiqueta_valor": "Importe de salida"}.get(clave)

    html = ("<div class='otra-marca'><span>Identificador: X-1</span>"
            "<span>Importe de salida: 50.000,00 €</span></div>")

    subastas, _ = boe.parsear_listado(html, ParamsFalsos())

    assert len(subastas) == 1 and subastas[0].valor_subasta == 50000.0

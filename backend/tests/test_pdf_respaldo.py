"""El informe PDF debe generarse CON y SIN la fuente DejaVu.

`pdf_service._DEJAVU` es una ruta POSIX absoluta, así que en Windows nunca
existe: la rama de respaldo no es un caso exótico, es **la única que corre** en
todo el desarrollo local y en cualquier imagen que no sea `backend/Dockerfile`.

Estos tests fuerzan las dos ramas explícitamente en lugar de depender de si la
máquina tiene la fuente instalada. Sin esa fuerza, instalar `fonts-dejavu-core`
en el runner de CI —que es lo que hace el Bloque F′— pondría el pipeline en
verde **enterrando** el defecto del respaldo en vez de arreglarlo.
"""
from __future__ import annotations

import os
import pathlib

import pytest

from app.services import pdf_service

# Fragmento de informe con toda la tipografía que M14 genera de verdad y que no
# existe en latin-1: viñeta, guion largo, comillas tipográficas, comparadores,
# flecha, puntos suspensivos y un emoji.
MARKDOWN = """# Informe de análisis

## Decisión — resumen

- Semáforo 🟢 verde: ROI ≥ 18 %
- Precio «objetivo» → 142.000 €
- Riesgo bajo… salvo cargas no purgables

| Concepto | Valor |
|---|---|
| P_límite | 155.000 € |

Texto normal con “comillas” y guion —largo—.
"""


@pytest.fixture
def sin_dejavu(monkeypatch):
    """Fuerza la rama de respaldo, exista o no la fuente en esta máquina."""
    monkeypatch.setattr(pdf_service, "_DEJAVU",
                        pdf_service.Path("/ruta/que/no/existe"))


def test_el_informe_se_genera_sin_la_fuente_dejavu(sin_dejavu):
    """Test capital: es la regresión que rompía el informe entero.

    Una viñeta `•` concatenada FUERA del saneador hacía que fpdf2 lanzara
    `FPDFUnicodeEncodingException` con Helvetica, que solo admite latin-1.
    """
    pdf = pdf_service.informe_a_pdf(MARKDOWN)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_el_informe_se_genera_con_la_fuente_dejavu():
    """La otra rama. Único test del fichero que puede omitirse.

    **En CI la omisión es un FALLO, no un `skip`.** El runner instala
    `fonts-dejavu-core` a propósito; si ese paso se rompe o el paquete cambia de
    ruta, la rama con fuente dejaría de probarse y el pipeline seguiría verde
    porque nadie lee la salida de una ejecución que pasa.
    """
    if not (pdf_service._DEJAVU / "DejaVuSans.ttf").exists():
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            pytest.fail("DejaVu ausente en CI: el paso de instalación falló y la "
                        "rama con fuente ha dejado de probarse")
        pytest.skip("DejaVu no instalada en esta máquina (sí lo está en CI)")

    pdf = pdf_service.informe_a_pdf(MARKDOWN)

    assert pdf.startswith(b"%PDF")
    assert b"DejaVuSans" in pdf, "se generó con Helvetica teniendo la fuente"


def test_un_caracter_desconocido_se_reemplaza_y_no_rompe(sin_dejavu):
    """Mata la retirada de la red de último recurso.

    La tabla de equivalencias cubre lo previsible. El `encode(latin-1,"replace")`
    final existe para lo IMPREVISTO —`㎡` es plausible en una tasación—, y sin
    este test todos los demás pasan con la red quitada, porque su corpus solo
    contiene caracteres que la tabla ya traduce. Es decir: la suite daba luz
    verde a borrar la única defensa contra el carácter que nadie anticipó.
    """
    assert pdf_service._limpiar("Superficie 120 ㎡", False) == "Superficie 120 ?"

    pdf = pdf_service.informe_a_pdf("# T\n\nSuperficie 120 ㎡ y № 4\n")

    assert pdf.startswith(b"%PDF")


@pytest.mark.parametrize("original,equivalente",
                         sorted(pdf_service._EQUIVALENCIAS.items()))
def test_toda_la_tabla_de_equivalencias_se_translitera(original, equivalente):
    """Propiedad sobre la tabla ENTERA, no una lista de ejemplos.

    Con casos escritos a mano, 15 de las 23 entradas podían borrarse sin que nada
    fallara —entre ellas `’`, el carácter tipográfico más frecuente en prosa
    española, y `≤`/`≠`, espejos de un `≥` que sí estaba cubierto—. Parametrizar
    sobre la propia tabla mantiene la cobertura cuando la tabla crezca.
    """
    resultado = pdf_service._limpiar(f"x{original}y", False)

    assert resultado == f"x{equivalente}y"
    assert "?" not in resultado, "la equivalencia no evitó el reemplazo de último recurso"


def test_el_respaldo_incrusta_helvetica_y_no_dejavu(sin_dejavu):
    """Afirma QUÉ RAMA se ejecutó, no solo que salió un PDF.

    Un PDF con Helvetica también empieza por `%PDF`, de modo que invertir la
    detección de fuente dejaba los dos tests de rama en verde.
    """
    pdf = pdf_service.informe_a_pdf(MARKDOWN)

    assert b"Helvetica" in pdf
    assert b"DejaVuSans" not in pdf


def test_el_titulo_no_latin1_no_rompe_el_informe(sin_dejavu):
    """El título va a los metadatos, que también se codifican."""
    pdf = pdf_service.informe_a_pdf(MARKDOWN, titulo="Chalé «Sur» — 155.000 € ㎡")

    assert pdf.startswith(b"%PDF")


def test_el_pie_no_latin1_no_rompe_el_informe(sin_dejavu, monkeypatch):
    """Ahora comprobable de verdad, gracias a que el literal vive en `PIE`.

    Antes el test tenía el nombre correcto y no podía fallar: el pie actual
    sobrevive a latin-1 por casualidad, y el test heredaba esa casualidad.
    """
    monkeypatch.setattr(pdf_service, "PIE", "SEIS ▪ página {n} ㎡")

    pdf = pdf_service.informe_a_pdf(MARKDOWN)

    assert pdf.startswith(b"%PDF")


def test_la_vineta_llega_saneada_desde_el_punto_de_lista(sin_dejavu):
    """Ancla la regresión estrella al PUNTO DE LLAMADA, no al saneador.

    El test que lleva el nombre del defecto afirma sobre `_limpiar` aislado, así
    que no cazaría una reconcatenación fuera de él. Esto sí: un markdown con un
    único ítem de lista, independiente del corpus grande.
    """
    pdf = pdf_service.informe_a_pdf("- Un solo punto de lista\n")

    assert pdf.startswith(b"%PDF")


def test_la_vineta_se_translitera_en_vez_de_perderse(sin_dejavu):
    """Transliterar y no reemplazar por «?».

    `encode("latin-1", "replace")` es técnicamente correcto y produce un informe
    ilegible: los guiones largos, las comillas y los comparadores salpican todo
    el texto de M14. La equivalencia conserva el sentido.
    """
    assert pdf_service._limpiar(f"  {pdf_service.VINETA}  Punto", False) == "-  Punto"


@pytest.mark.parametrize("original,esperado", [
    ("ROI ≥ 18 %", "ROI >= 18 %"),
    ("Precio → 142.000 €", "Precio -> 142.000 EUR"),
    ("“comillas”", '"comillas"'),
    ("guion —largo—", "guion -largo-"),
    ("Riesgo bajo…", "Riesgo bajo..."),
])
def test_las_equivalencias_conservan_el_sentido(original, esperado):
    assert pdf_service._limpiar(original, False) == esperado


def test_ningun_caracter_del_informe_DORADO_se_pierde_en_el_respaldo():
    """Corpus DERIVADO del informe real, no escrito a mano.

    El corpus de este fichero es una constante, así que solo protege las cinco
    equivalencias que alguien acordó meter en él: borrar `’`, `≤`, `≠`, `δ` o los
    espacios duros dejaba la suite verde. Y `δ` es precisamente el carácter que
    el informe dorado §19 perdía —está documentado como tal en `pdf_service`— y
    no aparecía en la constante.

    Leyendo el informe de referencia entero, la tabla queda vigilada por el texto
    que el sistema genera de verdad, y crece con él.
    """
    informe = pathlib.Path(__file__).resolve().parents[2] / "docs" / "SEIS_informe_ejemplo_caso19.md"
    if not informe.exists():
        pytest.skip("no está el informe de referencia del §19")

    perdidos = []
    for linea in informe.read_text(encoding="utf-8").splitlines():
        limpio = pdf_service._limpiar(linea, False)
        if "?" in limpio and "?" not in linea:
            perdidos.append((linea, limpio))

    assert not perdidos, (
        f"{len(perdidos)} líneas del informe dorado pierden algún carácter al "
        f"transliterar. Primera: {perdidos[0][0]!r} → {perdidos[0][1]!r}. "
        "Añada su equivalencia en `_EQUIVALENCIAS`.")


def test_ningun_caracter_del_informe_se_pierde_en_el_respaldo():
    """Invariante REAL del respaldo, no una tautología.

    La versión anterior afirmaba `limpio.encode("latin-1")` sin excepción, que es
    una identidad: `_limpiar` **termina** en `encode(..., "replace")`, así que su
    salida siempre es codificable y el test no podía fallar jamás. Lo que sí
    tiene señal es que no aparezcan «?»: cada uno es un carácter del informe que
    se ha perdido. Así se detectó que `δ` —que M14 emite en la Valoración— era el
    único carácter del informe dorado §19 que acababa reemplazado.
    """
    for linea in MARKDOWN.splitlines():
        limpio = pdf_service._limpiar(linea, False)

        assert "?" not in limpio, (
            f"se perdió un carácter al transliterar: {linea!r} → {limpio!r}. "
            "Añada su equivalencia en `_EQUIVALENCIAS`.")


def test_las_viñetas_conservan_su_sangria(sin_dejavu, monkeypatch):
    """La sangría va FUERA del saneador, que termina en `.strip()`.

    Meterla dentro se la comía y todas las listas del informe —plan de puja,
    checklist bloqueante, vetos— perdían su indentación en silencio.

    Se afirma sobre la **cadena que llega a `multi_cell`**, no sobre longitudes en
    bytes del PDF: quitar la sangría conservando la viñeta también cambia el
    tamaño, así que la comparación anterior pasaba con el defecto que decía
    vigilar.
    """
    escritas = []
    original = pdf_service._InformePDF.multi_cell

    def _capturar(self, w, h, txt="", *a, **k):
        escritas.append(txt)
        return original(self, w, h, txt, *a, **k)

    monkeypatch.setattr(pdf_service._InformePDF, "multi_cell", _capturar)

    pdf_service.informe_a_pdf("- Punto de lista\n")

    vinetas = [t for t in escritas if "Punto de lista" in t]
    assert vinetas, "no se escribió la línea de lista"
    assert vinetas[0].startswith("  "), (
        f"la viñeta perdió su sangría: {vinetas[0]!r}")


def test_con_dejavu_no_se_transliteran_los_caracteres(monkeypatch):
    """Con la fuente disponible el texto se conserva íntegro: transliterar
    siempre degradaría el informe sin motivo."""
    assert pdf_service._limpiar("ROI ≥ 18 % → «sí»", True) == "ROI ≥ 18 % → «sí»"


# Retirado `test_el_pie_de_pagina_tambien_pasa_por_el_saneador`: era un duplicado
# del humo de arriba con un nombre que prometía una garantía que no daba —el pie
# actual sobrevive a latin-1 por casualidad, así que el test no podía fallar—. El
# test real del pie es `test_el_pie_no_latin1_no_rompe_el_informe`, que sustituye
# `PIE` por un texto que sí rompería sin saneador.

"""Render del informe Markdown de M14 a PDF (§12) con fpdf2.

Sin dependencias de sistema pesadas: TTF DejaVu si está disponible (UTF-8
completo) y fallback a Helvetica con transliteración latin-1.
"""
from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_DEJAVU = Path("/usr/share/fonts/truetype/dejavu")
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")


# Viñeta del listado. Constante y no literal suelto: era un literal concatenado
# FUERA del saneador, y por ahí entró el carácter que rompía el informe entero.
VINETA = "•"

# Pie de página. Constante y no literal dentro de `footer()` por testabilidad:
# embebido allí no hay forma de sustituirlo, y comprobar que pasa por el saneador
# era imposible — el texto actual sobrevive a latin-1 por casualidad.
PIE = "SEIS · página {n}"

# Equivalencias tipográficas para el respaldo latin-1. Sin ellas,
# `encode("latin-1", "replace")` sustituye cada carácter por «?», que es
# técnicamente correcto y produce un informe ilegible: los guiones largos, las
# comillas tipográficas y los operadores de comparación aparecen por todo el
# texto que genera M14. Traducir es barato y conserva el sentido.
_EQUIVALENCIAS = {
    "•": "-", "‣": "-",                      # viñetas
    "–": "-", "—": "-", "―": "-",       # guiones largos
    "“": '"', "”": '"', "„": '"',       # comillas dobles
    "‘": "'", "’": "'", "‚": "'",       # comillas simples
    "…": "...",                                   # puntos suspensivos
    "→": "->", "←": "<-", "⇒": "=>",    # flechas
    "≥": ">=", "≤": "<=", "≠": "!=",    # comparadores
    "™": "(TM)", "€": "EUR",                 # símbolos
    # `δ` la emite M14 en la sección de Valoración («δ_v aplicado»). Es el ÚNICO
    # carácter del informe dorado §19 que acababa reemplazado por «?».
    "δ": "delta", "σ": "sigma", "Δ": "delta",
    " ": " ", " ": " ", " ": " ",       # espacios duros y finos
}


def _limpiar(texto: str, unicode_ok: bool) -> str:
    """Único punto por el que el texto puede llegar a fpdf.

    Con DejaVu disponible solo se retiran emojis y marcas de Markdown. Sin ella,
    además se translitera a latin-1: primero por equivalencias legibles y solo
    después, como último recurso, con el reemplazo de `encode`.
    """
    texto = _EMOJI.sub("", texto)
    texto = texto.replace("**", "").replace("`", "").replace("_", " ")
    if not unicode_ok:
        for original, equivalente in _EQUIVALENCIAS.items():
            texto = texto.replace(original, equivalente)
        texto = texto.encode("latin-1", "replace").decode("latin-1")
    return texto.strip()


class _InformePDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.unicode_ok = (_DEJAVU / "DejaVuSans.ttf").exists()
        if self.unicode_ok:
            self.add_font("DejaVu", "", str(_DEJAVU / "DejaVuSans.ttf"))
            self.add_font("DejaVu", "B", str(_DEJAVU / "DejaVuSans-Bold.ttf"))
            self.familia = "DejaVu"
        else:
            self.familia = "helvetica"

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(self.familia, "", 8)
        self.set_text_color(120)
        # También por el saneador: es texto que llega a fpdf igual que el resto,
        # y hoy sobrevive a latin-1 por casualidad, no por diseño. El literal vive
        # en `PIE` para que un test pueda sustituirlo: embebido aquí, comprobar
        # que pasa por el saneador era imposible.
        self.cell(0, 8, _limpiar(PIE.format(n=self.page_no()), self.unicode_ok),
                  align="C")
        self.set_text_color(0)


def _volcar_tabla(pdf: _InformePDF, filas: list[list[str]]) -> None:
    pdf.set_font(pdf.familia, "", 8.5)
    with pdf.table(text_align="LEFT", line_height=5.5, padding=1.2) as tabla:
        for i, fila in enumerate(filas):
            row = tabla.row()
            for celda in fila:
                row.cell(_limpiar(celda, pdf.unicode_ok))
    pdf.ln(2)


def informe_a_pdf(markdown: str, titulo: str = "Informe de análisis SEIS") -> bytes:
    pdf = _InformePDF()
    # El título va a los metadatos del PDF, que también se codifican.
    pdf.set_title(_limpiar(titulo, pdf.unicode_ok))
    pdf.add_page()
    tabla_actual: list[list[str]] = []

    for linea in markdown.splitlines():
        raw = linea.rstrip()
        es_tabla = raw.strip().startswith("|")
        if tabla_actual and not es_tabla:
            _volcar_tabla(pdf, tabla_actual)
            tabla_actual = []
        if not raw.strip():
            continue
        if es_tabla:
            celdas = [c for c in raw.strip().strip("|").split("|")]
            if all(set(c.strip()) <= set("-: ") for c in celdas):
                continue                               # separador de cabecera
            tabla_actual.append(celdas)
            continue
        if raw.startswith("# "):
            pdf.set_font(pdf.familia, "B", 15)
            pdf.multi_cell(0, 8, _limpiar(raw[2:], pdf.unicode_ok), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
        elif raw.startswith("## "):
            pdf.set_font(pdf.familia, "B", 12)
            pdf.set_fill_color(238)
            pdf.multi_cell(0, 7, _limpiar(raw[3:], pdf.unicode_ok), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
        elif raw.startswith("---"):
            pdf.ln(1)
        elif raw.lstrip().startswith("- "):
            pdf.set_font(pdf.familia, "", 9)
            # La viñeta va DENTRO de `_limpiar`, no concatenada fuera. Esta línea
            # era la causa raíz: con Helvetica, `•` (U+2022) no existe en latin-1
            # y fpdf2 lanzaba FPDFUnicodeEncodingException, tirando el informe
            # entero en cualquier máquina sin la fuente DejaVu.
            # La viñeta se sanea CON el contenido; la sangría se añade después y
            # por fuera, porque son espacios ASCII y no pueden romper nada. Meter
            # también la sangría dentro costaba la indentación de todas las
            # listas del informe: `_limpiar` termina en `.strip()`.
            texto = "  " + _limpiar(f"{VINETA}  {raw.lstrip()[2:]}", pdf.unicode_ok)
            pdf.multi_cell(0, 5, texto, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            negrita = "B" if raw.startswith("**") else ""
            pdf.set_font(pdf.familia, negrita, 9.5)
            pdf.multi_cell(0, 5.2, _limpiar(raw, pdf.unicode_ok), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if tabla_actual:
        _volcar_tabla(pdf, tabla_actual)
    return bytes(pdf.output())

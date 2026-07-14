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


def _limpiar(texto: str, unicode_ok: bool) -> str:
    texto = _EMOJI.sub("", texto)
    texto = texto.replace("**", "").replace("`", "").replace("_", " ")
    if not unicode_ok:
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
        self.cell(0, 8, f"SEIS · página {self.page_no()}", align="C")
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
    pdf.set_title(titulo)
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
            pdf.multi_cell(0, 5, "  •  " + _limpiar(raw.lstrip()[2:], pdf.unicode_ok), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            negrita = "B" if raw.startswith("**") else ""
            pdf.set_font(pdf.familia, negrita, 9.5)
            pdf.multi_cell(0, 5.2, _limpiar(raw, pdf.unicode_ok), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if tabla_actual:
        _volcar_tabla(pdf, tabla_actual)
    return bytes(pdf.output())

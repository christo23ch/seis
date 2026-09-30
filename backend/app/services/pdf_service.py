"""Render del informe Markdown de M14 a PDF (§12) con fpdf2.

Sin dependencias de sistema pesadas: TTF DejaVu si está disponible (UTF-8
completo) y fallback a Helvetica con transliteración latin-1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_DEJAVU = Path("/usr/share/fonts/truetype/dejavu")
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")

# Énfasis de Markdown (`_texto_`), pero NO el guion bajo interior de un
# identificador. Un `.replace("_", " ")` a secas degradaba los nombres canónicos
# del producto: `P_límite` salía como «P límite», `C_F` como «C F» y `c_v` como
# «c v», en 15 líneas del informe dorado §19. `P_límite` es término contractual
# —el bloqueo duro que el software nunca deja superar (CLAUDE.md §4)—, así que
# verlo partido en el entregable que recibe el cliente no es cosmético.
# Solo se retira el guion bajo que NO está entre dos caracteres de palabra.
# `[^\W_]` es «carácter de palabra que no sea el propio guion bajo»: sin esa
# exclusión, `__negrita__` dejaba restos, porque `_` cuenta como \w y el segundo
# guion de cada par se creía interior.
_ENFASIS_GUION_BAJO = re.compile(r"(?<![^\W_])_|_(?![^\W_])")


# Viñeta del listado. Constante y no literal suelto: era un literal concatenado
# FUERA del saneador, y por ahí entró el carácter que rompía el informe entero.
VINETA = "•"

# Pie de página. Constante y no literal dentro de `footer()` por testabilidad:
# embebido allí no hay forma de sustituirlo, y comprobar que pasa por el saneador
# era imposible — el texto actual sobrevive a latin-1 por casualidad.
PIE = "SEIS · página {n}"

# ─────────────── Identificación del documento (Fase 5G.1, deuda D5) ───────────────
# Impreso, un informe oficial tiene que decir qué informe es, y una vista previa
# que NO lo es. La identificación va FUERA del Markdown —cabecera, bloque inicial
# y pie—, de modo que el texto congelado que produjo M14 no se toca nunca.

MARCA_VISTA_PREVIA = "VISTA PREVIA — NO OFICIAL"
TITULO_OFICIAL = "INFORME OFICIAL"
NO_CONSTA = "no consta"
# El pie lleva el id completo y no debe partirse: si no cupiera a 8 pt, se
# reduce el cuerpo hasta este mínimo en vez de saltar de línea.
TAMANO_PIE = 8.0
TAMANO_PIE_MINIMO = 6.0


@dataclass(frozen=True)
class Identificacion:
    """Qué documento es el PDF. `pie` lleva `{n}` para el número de página.
    `fecha_creacion` fija la fecha de los metadatos: con la de emisión, dos
    descargas del mismo informe salen idénticas byte a byte."""
    titulo_documento: str
    cabecera: str
    titulo_bloque: str
    bloque: tuple[str, ...]
    pie: str
    fecha_creacion: datetime | None = None


def _utc(fecha: datetime) -> datetime:
    # SQLite devuelve `generado_en` sin zona; se escribió en UTC (`models._now`).
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)


def identificacion_oficial(informe) -> Identificacion:
    """Identificación de un informe oficial, leída EXCLUSIVAMENTE de su fila.

    Nada del análisis ni de la simulación actuales: la fila es inmutable, así
    que el PDF identifica igual el informe hoy y dentro de un año. Lo que la
    fila no trae se declara («no consta»), nunca se busca fuera.
    """
    resultado = informe.resultado if isinstance(informe.resultado, dict) else {}
    decision = resultado.get("decision") if isinstance(resultado.get("decision"), dict) else {}
    emitido = _utc(informe.generado_en)
    fecha = emitido.strftime("%Y-%m-%d %H:%M:%S UTC")
    if informe.simulacion_id is None:
        procedencia, lineas_sim = "Configuración original", ()
    else:
        procedencia = f"Simulación {informe.simulacion_id[:8]}"
        lineas_sim = (f"Id de la simulación: {informe.simulacion_id}",)
    bloque = (
        f"Id: {informe.id}",
        f"Emitido: {fecha}",
        f"Procedencia: {procedencia}",
        *lineas_sim,
        f"Versión de parámetros: {decision.get('version_parametros') or NO_CONSTA}",
        f"Versión de reglas: {decision.get('version_reglas') or NO_CONSTA}",
        f"Overrides aplicados: {len(informe.overrides or {})}",
    )
    if informe.parametros_aplicados is None:
        bloque += ("Sin snapshot de parámetros (análisis anterior a la migración 0014)",)
    return Identificacion(
        titulo_documento=f"Informe oficial SEIS {informe.id}",
        cabecera=f"Informe oficial · {informe.id[:8]} · emitido {fecha}",
        titulo_bloque=TITULO_OFICIAL,
        bloque=bloque,
        pie=f"SEIS · Informe oficial {informe.id} · {procedencia} · página {{n}}",
        fecha_creacion=emitido,
    )


def identificacion_vista_previa() -> Identificacion:
    """Marca de la vista previa (`/informe.pdf`): la configuración en uso al
    descargar, sin valor de documento. No lleva fecha fija: no hay nada congelado."""
    return Identificacion(
        titulo_documento="Vista previa no oficial SEIS",
        cabecera=MARCA_VISTA_PREVIA,
        titulo_bloque=MARCA_VISTA_PREVIA,
        bloque=("Refleja la configuración en uso al descargarlo.",
                "No es un informe oficial ni queda registrado."),
        pie="SEIS · vista previa no oficial · página {n}",
    )

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
    texto = texto.replace("**", "").replace("`", "")
    texto = _ENFASIS_GUION_BAJO.sub("", texto)
    if not unicode_ok:
        for original, equivalente in _EQUIVALENCIAS.items():
            texto = texto.replace(original, equivalente)
        texto = texto.encode("latin-1", "replace").decode("latin-1")
    return texto.strip()


class _InformePDF(FPDF):
    def __init__(self, identificacion: Identificacion | None = None) -> None:
        super().__init__(format="A4")
        self.identificacion = identificacion
        self.set_auto_page_break(auto=True, margin=18)
        if identificacion is not None:
            self.set_top_margin(15)          # deja sitio a la cabecera
        self.unicode_ok = (_DEJAVU / "DejaVuSans.ttf").exists()
        if self.unicode_ok:
            self.add_font("DejaVu", "", str(_DEJAVU / "DejaVuSans.ttf"))
            self.add_font("DejaVu", "B", str(_DEJAVU / "DejaVuSans-Bold.ttf"))
            self.familia = "DejaVu"
        else:
            self.familia = "helvetica"

    def header(self) -> None:
        if self.identificacion is None:
            return
        self.set_y(6)
        self.set_font(self.familia, "B", 8.5)
        self.set_text_color(90)
        self.cell(0, 5, _limpiar(self.identificacion.cabecera, self.unicode_ok), align="C")
        self.set_text_color(0)
        self.set_y(self.t_margin)

    def _tamano_pie(self, texto: str) -> float:
        """Cuerpo del pie para que quepa en UNA línea del ancho útil: 8 pt, o
        menos si el texto (id completo incluido) no cabe, hasta el mínimo."""
        texto = _limpiar(texto, self.unicode_ok)
        tamano = TAMANO_PIE
        while tamano > TAMANO_PIE_MINIMO:
            self.set_font(self.familia, "", tamano)
            if self.get_string_width(texto) <= self.epw:
                break
            tamano -= 0.5
        return tamano

    def footer(self) -> None:
        self.set_y(-12)
        # También por el saneador: es texto que llega a fpdf igual que el resto,
        # y hoy sobrevive a latin-1 por casualidad, no por diseño. El literal vive
        # en `PIE` para que un test pueda sustituirlo: embebido aquí, comprobar
        # que pasa por el saneador era imposible.
        plantilla = PIE if self.identificacion is None else self.identificacion.pie
        texto = plantilla.format(n=self.page_no())
        self.set_font(self.familia, "", self._tamano_pie(texto))
        self.set_text_color(120)
        self.cell(0, 8, _limpiar(texto, self.unicode_ok), align="C")
        self.set_text_color(0)

    def bloque_identificacion(self) -> None:
        """Recuadro inicial de la primera página, antes del Markdown."""
        ident = self.identificacion
        self.set_draw_color(120)
        self.set_font(self.familia, "B", 11)
        self.multi_cell(0, 7, _limpiar(ident.titulo_bloque, self.unicode_ok), border="LTR",
                        padding=(1, 2, 0, 2), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(self.familia, "", 9)
        lineas = "\n".join(_limpiar(linea, self.unicode_ok) for linea in ident.bloque)
        self.multi_cell(0, 5, lineas, border="LBR", padding=(0, 2, 1.5, 2),
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(0)
        self.ln(4)


def _volcar_tabla(pdf: _InformePDF, filas: list[list[str]]) -> None:
    pdf.set_font(pdf.familia, "", 8.5)
    with pdf.table(text_align="LEFT", line_height=5.5, padding=1.2) as tabla:
        for i, fila in enumerate(filas):
            row = tabla.row()
            for celda in fila:
                row.cell(_limpiar(celda, pdf.unicode_ok))
    pdf.ln(2)


def informe_a_pdf(markdown: str, titulo: str = "Informe de análisis SEIS", *,
                  identificacion: Identificacion | None = None) -> bytes:
    """`markdown` se vuelca tal cual. `identificacion` (Fase 5G.1) añade
    cabecera, bloque inicial y pie SIN tocar el Markdown; sin ella, el PDF es
    el de siempre."""
    pdf = _InformePDF(identificacion)
    if identificacion is not None:
        titulo = identificacion.titulo_documento
        if identificacion.fecha_creacion is not None:
            pdf.set_creation_date(identificacion.fecha_creacion)
    # El título va a los metadatos del PDF, que también se codifican.
    pdf.set_title(_limpiar(titulo, pdf.unicode_ok))
    pdf.add_page()
    if identificacion is not None:
        pdf.bloque_identificacion()
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

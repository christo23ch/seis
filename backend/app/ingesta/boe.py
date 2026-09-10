"""Conector del BOE: PARSEO únicamente (Fase 17-A).

Este módulo convierte HTML en contratos y **no toca la base de datos**. Esa
frontera es deliberada: la Fase 17-B ajustará los selectores contra el HTML real
del portal —que hoy no tenemos, porque el sandbox no puede descargarlo— sin que
eso obligue a revisar nada de la persistencia.

DISEÑO DEFENSIVO, y esto no es una aspiración sino el contrato del módulo:
ninguna función de aquí lanza por culpa del HTML. Un ítem ilegible se cuenta y
se describe; un documento entero irreconocible devuelve lista vacía. La ingesta
de la noche no puede caerse porque el portal cambiara una etiqueta.

⚠️ SELECTORES SIN VERIFICAR. Los valores por defecto de `ingesta.boe.*` en
`params/defaults.yaml` son una estructura PLAUSIBLE, no la real: nadie los ha
contrastado contra subastas.boe.es. Ajustarlos es el trabajo de la Fase 17-B, y
por eso viven en parámetros T3 y no en el código: cambiarlos no exigirá desplegar.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

from app.ingesta.contratos import SubastaCaptada

log = logging.getLogger("seis.ingesta.boe")

# Etiquetas del listado, tomadas de los parámetros T3 (ver `_conf`). Se declaran
# aquí como respaldo para que el módulo sea utilizable en un test unitario sin
# base de datos.
RESPALDO: dict[str, Any] = {
    "marca_item": "subasta-item",
    "etiqueta_identificador": "Identificador",
    "etiqueta_valor": "Valor subasta",
    "etiqueta_puja_minima": "Puja mínima",
    "etiqueta_deposito": "Importe del depósito",
    "etiqueta_localidad": "Localidad",
    "etiqueta_provincia": "Provincia",
    "etiqueta_cierre": "Fecha de conclusión",
    "etiqueta_tipo_bien": "Tipo de bien",
    "fuente_codigo": "judicial_boe",
}

_IMPORTE = re.compile(r"([\d.]+(?:,\d+)?)\s*€?")


def _conf(params: Any | None) -> dict[str, Any]:
    """Configuración efectiva: parámetros T3 si los hay, respaldo si no."""
    if params is None:
        return dict(RESPALDO)
    valores = dict(RESPALDO)
    for clave in RESPALDO:
        try:
            leido = params.get(f"ingesta.boe.{clave}")
        except Exception:                      # noqa: BLE001 — el parser nunca lanza
            leido = None
        if leido not in (None, ""):
            valores[clave] = leido
    return valores


def importe_es(texto: str | None) -> float | None:
    """«152.000,50 €» → 152000.5. Devuelve None si no hay número reconocible.

    Formato español: el punto separa millares y la coma decimales. Confundirlos
    convertiría 152.000 € en 152 €, que es un error silencioso y caro: pasaría
    todos los filtros de alerta por valor máximo.
    """
    if not texto:
        return None
    m = _IMPORTE.search(texto.replace("\xa0", " "))
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def fecha_es(texto: str | None) -> datetime | None:
    """«31-12-2026» o «31/12/2026» → datetime. None si no se reconoce."""
    if not texto:
        return None
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", texto)
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:                          # 31 de febrero y demás
        return None


class _Extractor(HTMLParser):
    """Recoge pares «etiqueta: valor» y los bloques marcados como ítem.

    Se usa `html.parser` de la biblioteca estándar y no BeautifulSoup a
    propósito: no añade dependencia, y para pares etiqueta-valor no hace falta
    más. Si la 17-B descubre que el portal exige selectores CSS de verdad, ese
    es el momento de evaluar la dependencia, con el HTML real delante.
    """

    def __init__(self, marca_item: str) -> None:
        super().__init__(convert_charrefs=True)
        self.marca_item = marca_item
        self.bloques: list[list[str]] = []
        self._actual: list[str] | None = None
        self._profundidad = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        valores = " ".join(v or "" for _, v in attrs)
        if self.marca_item and self.marca_item in valores:
            self._actual = []
            self._profundidad = 1
            return
        if self._actual is not None:
            self._profundidad += 1

    def handle_endtag(self, tag: str) -> None:
        if self._actual is None:
            return
        self._profundidad -= 1
        if self._profundidad <= 0:
            self.bloques.append(self._actual)
            self._actual = None

    def handle_data(self, data: str) -> None:
        texto = data.strip()
        if texto and self._actual is not None:
            self._actual.append(texto)


def _valor_tras(fragmentos: list[str], etiqueta: str) -> str | None:
    """Devuelve el texto que sigue a una etiqueta, dentro o fuera del mismo nodo."""
    for i, trozo in enumerate(fragmentos):
        if etiqueta.lower() in trozo.lower():
            resto = trozo.split(":", 1)
            if len(resto) == 2 and resto[1].strip():
                return resto[1].strip()
            if i + 1 < len(fragmentos):
                return fragmentos[i + 1]
    return None


def _a_contrato(fragmentos: list[str], conf: dict[str, Any]) -> SubastaCaptada | None:
    """Un bloque de texto → contrato. None si le falta lo imprescindible."""
    valor = importe_es(_valor_tras(fragmentos, conf["etiqueta_valor"]))
    if valor is None or valor <= 0:
        return None                              # sin valor no hay subasta analizable
    identificador = _valor_tras(fragmentos, conf["etiqueta_identificador"])
    localidad = _valor_tras(fragmentos, conf["etiqueta_localidad"])
    provincia = _valor_tras(fragmentos, conf["etiqueta_provincia"])
    tipo_bien = _valor_tras(fragmentos, conf["etiqueta_tipo_bien"])
    deposito = importe_es(_valor_tras(fragmentos, conf["etiqueta_deposito"]))

    extra = {k: v for k, v in {"localidad": localidad, "provincia": provincia,
                               "tipo_bien": tipo_bien}.items() if v}
    return SubastaCaptada(
        fuente_codigo=conf["fuente_codigo"],
        identificador_externo=identificador,
        valor_subasta=valor,
        puja_minima=importe_es(_valor_tras(fragmentos, conf["etiqueta_puja_minima"])),
        deposito_pct=(deposito / valor) if (deposito and valor) else 0.05,
        fecha_cierre=fecha_es(_valor_tras(fragmentos, conf["etiqueta_cierre"])),
        tiene_ubicacion=bool(localidad or provincia),
        tiene_descripcion=bool(tipo_bien),
        datos_extra=extra,
    )


def parsear_listado(html: str, params: Any | None = None) -> tuple[list[SubastaCaptada], list[str]]:
    """HTML de resultados → (subastas, motivos de descarte).

    NUNCA lanza. Devuelve `([], [motivo])` si el documento es irreconocible, que
    es lo que un HTML corrupto o una página de error deben producir.
    """
    conf = _conf(params)
    if not html or not html.strip():
        return [], ["documento vacío"]

    extractor = _Extractor(conf["marca_item"])
    try:
        extractor.feed(html)
        extractor.close()
    except Exception as e:                       # noqa: BLE001 — contrato del módulo
        log.warning("ingesta.boe: HTML ilegible (%s)", type(e).__name__)
        return [], [f"HTML ilegible: {type(e).__name__}"]

    if not extractor.bloques:
        # No es un error: también es lo que devuelve una búsqueda sin resultados.
        log.info("ingesta.boe: ningún bloque con la marca %r", conf["marca_item"])
        return [], []

    subastas: list[SubastaCaptada] = []
    motivos: list[str] = []
    for i, bloque in enumerate(extractor.bloques, 1):
        try:
            contrato = _a_contrato(bloque, conf)
        except Exception as e:                   # noqa: BLE001
            motivos.append(f"ítem {i}: {type(e).__name__}")
            continue
        if contrato is None:
            motivos.append(f"ítem {i}: sin valor de subasta reconocible")
            continue
        subastas.append(contrato)

    if motivos:
        log.warning("ingesta.boe: %d de %d ítems descartados", len(motivos),
                    len(extractor.bloques))
    return subastas, motivos


def parsear_detalle(html: str, params: Any | None = None) -> SubastaCaptada | None:
    """HTML de una ficha → contrato, o None si es irreconocible. Nunca lanza."""
    conf = _conf(params)
    if not html or not html.strip():
        return None
    extractor = _Extractor("")                   # la ficha entera es el bloque
    fragmentos: list[str] = []
    try:
        extractor.handle_data = lambda d: (fragmentos.append(d.strip())  # type: ignore[method-assign]
                                           if d.strip() else None)
        extractor.feed(html)
        extractor.close()
    except Exception as e:                       # noqa: BLE001
        log.warning("ingesta.boe: ficha ilegible (%s)", type(e).__name__)
        return None
    try:
        return _a_contrato(fragmentos, conf)
    except Exception:                            # noqa: BLE001
        return None

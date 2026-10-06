"""Utilidades compartidas por las pruebas de humo: identidad y trazabilidad (ADR-0021).

Solo biblioteca estándar, para que la importen los dos entornos virtuales.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

# User-Agent identificable: quién extrae y dónde preguntar. Nunca uno de navegador.
USER_AGENT = "SEIS-investigacion/0.1 (+https://github.com/christo23ch/seis)"

# Únicos destinos autorizados en la Fase E0: sitios de demostración.
DOMINIOS_PERMITIDOS = {"quotes.toscrape.com", "example.com"}

# Segundos entre peticiones al mismo dominio.
RETARDO_SEGUNDOS = 2.0

DIR_DATOS = Path(__file__).resolve().parent.parent / "datos_crudos"


def traza(url: str, contenido: bytes, herramienta: str, estado: int | None = None) -> dict:
    """Registro de trazabilidad de una descarga: URL, fecha UTC y SHA-256 del contenido."""
    return {
        "url": url,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(contenido).hexdigest(),
        "bytes": len(contenido),
        "estado_http": estado,
        "herramienta": herramienta,
    }


def guardar(nombre: str, registros: list[dict]) -> Path:
    """Escribe los registros como JSON Lines en datos_crudos/ (ignorado por git)."""
    DIR_DATOS.mkdir(exist_ok=True)
    destino = DIR_DATOS / f"{nombre}.jsonl"
    with destino.open("w", encoding="utf-8") as f:
        for registro in registros:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return destino

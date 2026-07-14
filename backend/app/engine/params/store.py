"""T3 — Almacén de parámetros versionados.

El motor nunca lee YAML/BD directamente: recibe un `Parametros` inmutable.
En producción se construye desde la tabla `parametro` (con este YAML como semilla
y fallback), garantizando que cada análisis congela `version_parametros` (P1/P3).
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

_DEFAULTS_PATH = Path(__file__).parent / "defaults.yaml"


class Parametros:
    def __init__(self, data: dict[str, Any]):
        self._data = data
        self.version: str = str(data.get("version", "dev"))

    def get(self, ruta: str, default: Any = None) -> Any:
        """Acceso por ruta con puntos: p.ej. 'fiscal.itp_por_ccaa.madrid'."""
        nodo: Any = self._data
        for parte in ruta.split("."):
            if isinstance(nodo, dict) and parte in nodo:
                nodo = nodo[parte]
            else:
                if default is None:
                    raise KeyError(f"Parámetro no encontrado: {ruta}")
                return default
        return nodo

    def seccion(self, ruta: str) -> dict:
        v = self.get(ruta)
        if not isinstance(v, dict):
            raise TypeError(f"'{ruta}' no es una sección")
        return v

    def con_overrides(self, overrides: dict[str, Any]) -> "Parametros":
        """Copia con overrides puntuales (rutas con puntos) — usado por tests y API admin."""
        data = copy.deepcopy(self._data)
        for ruta, valor in overrides.items():
            nodo = data
            partes = ruta.split(".")
            for p in partes[:-1]:
                nodo = nodo.setdefault(p, {})
            nodo[partes[-1]] = valor
        return Parametros(data)

    def raw(self) -> dict:
        return copy.deepcopy(self._data)


def cargar_defaults() -> Parametros:
    with open(_DEFAULTS_PATH, encoding="utf-8") as f:
        return Parametros(yaml.safe_load(f))


def desde_bd(filas: list[tuple[str, dict]], base: Parametros | None = None) -> Parametros:
    """Construye Parametros aplicando filas (clave→valor) de la tabla sobre los defaults."""
    p = base or cargar_defaults()
    overrides = {clave: valor for clave, valor in filas}
    return p.con_overrides(overrides) if overrides else p

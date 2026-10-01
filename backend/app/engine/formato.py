"""Formato de cifras para texto que lee una persona (Fase 5G.2).

Único sitio donde se escribe un importe: antes M14 tenía su `_eur` y M13
formateaba por su cuenta con `:,.0f`, que pone el separador de miles inglés
(«7,600 €», que en España se lee siete euros con sesenta).
"""
from __future__ import annotations


def eur(x: float | None) -> str:
    """Euros sin decimales con punto de miles: `60011` → «60.011 €»,
    `-13894` → «-13.894 €», `None` → «—»."""
    return f"{x:,.0f} €".replace(",", ".") if x is not None else "—"

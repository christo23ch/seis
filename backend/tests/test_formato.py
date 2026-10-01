"""Fase 5G.2 — `app.engine.formato.eur`: el único formato de importes del informe.

Antes había dos: el `_eur` de M14 («60.011 €») y un `:,.0f` suelto en M13 que
escribía «60,011 €» y «7,600 €». Para un lector español «7,600 €» son siete
euros con sesenta.
"""
from __future__ import annotations

import pytest

from app.engine.formato import eur


@pytest.mark.parametrize("valor, esperado", [
    (60011, "60.011 €"),
    (7600, "7.600 €"),
    (999, "999 €"),
    (0, "0 €"),
    (1234567.6, "1.234.568 €"),
    (-13894, "-13.894 €"),
    (-8.4, "-8 €"),
])
def test_eur_usa_el_punto_como_separador_de_miles(valor, esperado):
    assert eur(valor) == esperado


def test_eur_sin_valor_es_una_raya():
    assert eur(None) == "—"

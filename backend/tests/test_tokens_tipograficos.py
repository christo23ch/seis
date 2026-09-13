"""Los tokens de tipografía, vigilados donde el navegador los rompe en silencio.

**El fallo que motiva esta prueba.** `fontFamily.display` se escribió como
`["var(--fuente-display)", "Source Serif 4", "Georgia", "serif"]`. Tailwind lo emite
tal cual, **sin comillas**, y entonces CSS lee `4` como un identificador suelto — y
ningún identificador puede empezar por dígito—. Eso **invalida la declaración entera**,
el navegador la descarta sin avisar y el titular cae a la fuente heredada.

Resultado: el sistema de diseño decía «Source Serif 4 en cabeceras» y la pantalla
mostraba Inter. No lo detectó ninguna prueba ni ninguna captura: lo detectó medir
`getComputedStyle` en el navegador. Esta prueba convierte ese hallazgo en un rojo.

**LO QUE NO CUBRE** (ADR-0014): mira la sintaxis de los tokens, **no lo que pinta el
navegador**. Una familia bien escrita pero que no llega a cargarse —red caída en el
build, subconjunto equivocado— pasa esta prueba igual. Para eso hace falta medir en
el navegador, que es como se encontró el fallo original.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parents[2] / "frontend" / "tailwind.config.ts"


def _familias() -> dict[str, list[str]]:
    texto = CONFIG.read_text(encoding="utf-8")
    bloque = re.search(r"fontFamily:\s*\{(.+?)\n      \},", texto, re.S)
    assert bloque, "no se encuentra el bloque fontFamily: esta prueba no está mirando nada"
    familias = {
        nombre: re.findall(r'"([^"]+)"', lista)
        for nombre, lista in re.findall(r"(\w+):\s*\[(.*?)\]", bloque.group(1), re.S)
    }
    assert set(familias) == {"display", "texto", "cifra"}, (
        f"familias encontradas: {sorted(familias)}; se esperaban display, texto y cifra"
    )
    return familias


@pytest.mark.parametrize("familia", ["display", "texto", "cifra"])
def test_toda_familia_con_un_digito_va_entrecomillada(familia):
    """`Source Serif 4` sin comillas invalida la regla CSS completa, en silencio."""
    for entrada in _familias()[familia]:
        if re.search(r"\d", entrada) and not entrada.startswith("var("):
            assert entrada.startswith("'") and entrada.endswith("'"), (
                f"«{entrada}» lleva un dígito y va sin comillas: CSS descartará la "
                f"declaración entera de font-family y la fuente caerá a la heredada"
            )


@pytest.mark.parametrize("familia", ["display", "texto", "cifra"])
def test_toda_familia_termina_en_una_generica(familia):
    """Sin genérica final, un fallo de carga deja al navegador eligiendo por su cuenta."""
    genericas = {"serif", "sans-serif", "monospace", "system-ui", "ui-monospace"}
    assert _familias()[familia][-1] in genericas, (
        f"la familia «{familia}» no termina en una familia genérica"
    )


def test_las_dos_familias_elegidas_siguen_siendo_las_del_documento():
    """Fase 0' §2: Source Serif 4 en cabeceras, Inter en cuerpo. Si alguien las cambia,
    que sea una decisión y no un descuido — este rojo obliga a tocar el documento."""
    familias = _familias()
    assert "'Source Serif 4'" in familias["display"], "display ya no es Source Serif 4"
    assert "Inter" in familias["texto"], "texto ya no es Inter"

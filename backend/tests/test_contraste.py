"""El contraste de los tokens de color, vigilado por una prueba y no por una tabla.

**Por qué existe.** La Fase 0' midió la paleta y encontró tres parejas del semáforo
pasando AA **por centésimas** (naranja 4,50 exacto). Una tabla en un documento es una
foto de un día concreto: el siguiente que ajuste un color a ojo las rompe y nadie se
entera. Esto lo convierte en un rojo de la suite.

**Por qué vive en el backend** aunque mida el frontend: es el único sitio del proyecto
con ejecutor de pruebas conectado a la CI. Lee `frontend/tailwind.config.ts` como texto
porque no hay Node en esta suite — con el efecto secundario de que un token movido a
otro fichero dejaría de vigilarse (ver «lo que NO cubre»).

**LO QUE ESTA PRUEBA *NO* CUBRE** (regla del ADR-0014):

- Solo mira los tokens **declarados en `tailwind.config.ts`**. Un color escrito a mano
  en una clase (`text-[#999]`) o en `globals.css` **no se comprueba**. Hoy hay uno así:
  el azul de `:focus-visible`, que está duplicado en CSS.
- Comprueba **parejas declaradas aquí**, no combinaciones reales de la interfaz. Si
  alguien pone `text-sem-verde` sobre un fondo oscuro, esto no lo ve.
- No comprueba el contraste de **componentes no textuales** más allá del borde de
  control: iconos, gráficas de Recharts y el mapa quedan fuera.
- No sabe nada de **daltonismo**: la distancia ΔE que se comprueba es la de un ojo
  tricromático estándar.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parents[2] / "frontend" / "tailwind.config.ts"

AA_TEXTO = 4.5
AAA_TEXTO = 7.0
NO_TEXTUAL = 3.0        # WCAG 1.4.11: bordes de controles, iconos de estado
DELTA_E_MINIMO = 10.0   # por debajo, dos estados del semáforo se confunden de un vistazo


def _tokens() -> dict[str, str]:
    """Extrae los tokens de color como `grupo.nombre` desde la configuración.

    Se recorre el bloque `colors` llevando la cuenta del grupo en curso, porque las
    claves sueltas NO son únicas —`DEFAULT` aparece tres veces— y un `dict` plano
    las machacaría entre sí, dejando la prueba mirando menos colores de los que hay.
    """
    texto = CONFIG.read_text(encoding="utf-8")
    inicio = texto.index("colors: {")
    tokens: dict[str, str] = {}
    grupo = ""
    for linea in texto[inicio:].splitlines():
        if (g := re.match(r"\s*(\w+):\s*\{", linea)):
            grupo = g.group(1)
        for nombre, valor in re.findall(r'(\w+):\s*"(#[0-9A-Fa-f]{6})"', linea):
            tokens[f"{grupo}.{nombre}"] = valor
        if re.match(r"\s{6}\},\s*$", linea) and tokens:
            break                                    # fin del bloque `colors`
    assert len(tokens) >= 18, (
        f"solo se han encontrado {len(tokens)} tokens de color en {CONFIG.name}: "
        "o el fichero cambió de forma, o esta prueba está mirando al sitio "
        "equivocado y pasaría en vacío"
    )
    return tokens


def _lineal(hexa: str) -> list[float]:
    h = hexa.lstrip("#")
    canales = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]


def luminancia(hexa: str) -> float:
    r, g, b = _lineal(hexa)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _lab(hexa: str) -> tuple[float, float, float]:
    r, g, b = _lineal(hexa)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)   # noqa: E731
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(_lab(a), _lab(b))))


ESTADOS = ("verde", "amarillo", "naranja", "rojo")
FONDOS_NEUTROS = {"papel.carta": "#FFFFFF", "papel": "#F5F6F8"}


@pytest.mark.parametrize("estado", ESTADOS)
def test_el_semaforo_cumple_aaa_sobre_su_fondo(estado):
    """AAA y no AA: es el elemento más leído del informe, y AA al límite se rompe
    con un brillo bajo o una pantalla mal calibrada."""
    t = _tokens()
    r = contraste(t[f"sem.{estado}"], t[f"sem.{estado}bg"])
    assert r >= AAA_TEXTO, f"sem.{estado} sobre su fondo da {r:.2f}, por debajo de AAA"


@pytest.mark.parametrize("estado", ESTADOS)
@pytest.mark.parametrize("fondo", FONDOS_NEUTROS.items(), ids=lambda f: f[0] if isinstance(f, tuple) else str(f))
def test_el_semaforo_cumple_aaa_tambien_sobre_los_fondos_neutros(estado, fondo):
    """El color del semáforo también se usa como texto suelto (mensajes de error,
    totales), no solo dentro de su chip."""
    nombre, valor = fondo
    r = contraste(_tokens()[f"sem.{estado}"], valor)
    assert r >= AAA_TEXTO, f"sem.{estado} sobre {nombre} da {r:.2f}, por debajo de AAA"


def test_los_estados_del_semaforo_se_distinguen_entre_si():
    """Oscurecer para ganar contraste ACERCA los tonos entre sí. Esta prueba existe
    porque esa mejora tiene un coste medible y no debe cruzar la línea: amarillo y
    naranja son estados adyacentes, y son los que peor se separan."""
    t = _tokens()
    for i, a in enumerate(ESTADOS):
        for b in ESTADOS[i + 1:]:
            d = max(delta_e(t[f"sem.{a}"], t[f"sem.{b}"]),
                    delta_e(t[f"sem.{a}bg"], t[f"sem.{b}bg"]))
            assert d >= DELTA_E_MINIMO, (
                f"{a} y {b} distan ΔE {d:.1f}: por debajo de {DELTA_E_MINIMO} se "
                "confunden de un vistazo, y son estados de un semáforo"
            )


def test_el_borde_de_control_cumple_el_tres_a_uno():
    """WCAG 1.4.11. El borde decorativo (`linea`) no entra: no delimita un control."""
    t = _tokens()
    for nombre, fondo in FONDOS_NEUTROS.items():
        r = contraste(t["borde.control"], fondo)
        assert r >= NO_TEXTUAL, f"borde.control sobre {nombre} da {r:.2f}, por debajo de 3:1"


@pytest.mark.parametrize("token", ["tinta.DEFAULT", "tinta.suave"])
def test_el_texto_principal_cumple_aaa(token):
    assert contraste(_tokens()[token], "#FFFFFF") >= AAA_TEXTO


def test_el_primario_cumple_aa_en_los_dos_sentidos():
    """Se usa como texto de enlace sobre carta y como fondo de botón con texto blanco.
    El contraste es simétrico, así que una comprobación cubre los dos usos."""
    assert contraste(_tokens()["primario.DEFAULT"], "#FFFFFF") >= AA_TEXTO


TOKENS_VIGILADOS = {
    "tinta.DEFAULT", "tinta.suave", "tinta.borde", "papel.DEFAULT", "papel.carta",
    "primario.DEFAULT", "primario.hover", "primario.tenue", "borde.linea", "borde.control",
    "sem.verde", "sem.verdebg", "sem.amarillo", "sem.amarillobg",
    "sem.naranja", "sem.naranjabg", "sem.rojo", "sem.rojobg",
}


def test_estan_todos_los_tokens_que_esta_prueba_cree_vigilar():
    """La guarda de verdad, y por eso está escrita como inventario y no como umbral.

    Un `len(tokens) >= 18` se relaja con un solo carácter y nadie lo nota. Esto no:
    si un token desaparece, se renombra o se mueve a otro fichero, aquí sale en rojo
    con su nombre. Es la lección del punto 6 del ADR-0014 aplicada a esta prueba —
    una comprobación que no sabe qué debería estar mirando puede pasar en vacío.
    """
    faltan = TOKENS_VIGILADOS - set(_tokens())
    assert not faltan, f"tokens que esta prueba debía vigilar y ya no encuentra: {sorted(faltan)}"

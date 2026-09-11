"""Base imponible de la adquisición y su efecto sobre la función de inversión.

**El problema que resuelve.** El impuesto de transmisiones no se liquida sobre lo
que se paga, sino sobre **el mayor** de: valor de referencia del Catastro, valor
declarado y precio pagado (art. 10 TRLITPAJD, redacción de la Ley 11/2021). En una
subasta —donde todo el atractivo consiste en rematar por debajo del valor— aplicar
el tipo a la puja **infraestima el impuesto de forma sistemática**, y justo en las
operaciones más atractivas, que son las de puja más baja.

**Consecuencia sobre el modelo.** Hasta aquí el impuesto vivía dentro de `c_v`, el
tipo proporcional a P, porque `impuesto(P) = t·P` es proporcional. Con la base
correcta deja de serlo:

    impuesto(P) = t · max(P, B)        B = max(valor_referencia, valor_declarado)

que es proporcional por encima de B y **constante** por debajo. Se escribe como

    impuesto(P) = t·P + t·max(0, B − P)

es decir: `c_v` se queda como está, y aparece un **sobrecoste fijo** que solo actúa
en el tramo P < B. Por eso la función de inversión pasa a tener dos tramos, y su
inversa —que es lo que calcula la escalera de precios de M12— también.

**Propiedad de seguridad, y es la que hace revisable este cambio:** cuando no hay
base mínima (`B = 0`), el sobrecoste es 0 en todo P y *todas* las fórmulas
recuperan exactamente su forma anterior. Un análisis sin valor de referencia da el
mismo número que daba antes, hasta el último decimal.

**Alcance declarado (ADR-0014), porque esta red no lo cubre todo:**

- Se aplica **solo al régimen ITP**. En el régimen de IVA la base es el precio
  convenido; `tipo_base_minima` vale 0 ahí y este módulo no hace nada.
- Dentro del ITP se aplica al tipo de TPO. **No se aplica al AJD** aunque la
  Ley 11/2021 también tocó su base (art. 30.1): en una subasta con IVA+AJD la
  cuota gradual queda calculada sobre el precio, como antes. Es una limitación
  conocida, no un olvido.
- No comprueba que el valor de referencia aportado sea el del inmueble ni el del
  ejercicio correcto: eso es dato de entrada, y su ausencia se declara como
  carencia en el informe en vez de inventarse.
"""
from __future__ import annotations

from typing import Callable

from app.engine.contracts import CostesResultado

# Origen de la base imponible efectivamente usada, en orden de prelación legal.
POR_REFERENCIA = "valor_referencia"
POR_DECLARADO = "valor_declarado"
POR_PRECIO = "precio_pagado"


def base_minima(valor_referencia: float | None, valor_declarado: float | None) -> tuple[float, str]:
    """Suelo de la base imponible conocido *antes* de saber a cuánto se remata.

    Devuelve `(importe, origen)`. Sin ningún dato devuelve `(0.0, POR_PRECIO)`:
    el impuesto se calculará sobre la puja, que es un **suelo** —la base real solo
    puede ser igual o mayor—, y el informe lo declara como supuesto no verificado.
    Nunca se estima un valor de referencia a partir de otra cosa.
    """
    candidatos = [(float(v), o) for v, o in ((valor_referencia, POR_REFERENCIA),
                                             (valor_declarado, POR_DECLARADO)) if v]
    if not candidatos:
        return 0.0, POR_PRECIO
    return max(candidatos, key=lambda c: c[0])


def sobrecoste(p: float, costes: CostesResultado) -> float:
    """Parte del impuesto que NO es proporcional a P (0 si P ≥ B, o si no hay B)."""
    return costes.tipo_base_minima * max(0.0, costes.base_fiscal_minima - p)


def inversion(p: float, costes: CostesResultado, c_f: float) -> float:
    """I(P) completa: proporcional + fijos + el tramo no proporcional del impuesto."""
    return p * (1 + costes.c_v) + c_f + sobrecoste(p, costes)


def resolver_por_tramos(costes: CostesResultado,
                        calcular: Callable[[float, float], float]) -> float:
    """Invierte en P una fórmula cerrada de precio, respetando los dos tramos.

    `calcular(c_v_efectivo, fijo_extra)` debe ser la fórmula de siempre, parametrizada
    en el tipo proporcional y en un sumando fijo adicional. Funciona sin tocar cada
    fórmula porque en todas ellas `c_v` multiplica a P y los fijos suman: en el tramo
    bajo basta con mover el impuesto de un sitio al otro (`c_v − t`, `+t·B`).

    I(P) es continua y estrictamente creciente, así que solo uno de los dos tramos
    contiene la solución; se elige el que la contiene, no el que da mejor número.
    """
    b, t = costes.base_fiscal_minima, costes.tipo_base_minima
    if b <= 0 or t <= 0:
        return calcular(costes.c_v, 0.0)
    p_bajo = calcular(costes.c_v - t, t * b)
    if p_bajo < b:
        return p_bajo
    p_alto = calcular(costes.c_v, 0.0)
    # En el empate exacto (P = B) los dos tramos coinciden; si el alto se sale de su
    # propio dominio es que la solución es justo la frontera.
    return p_alto if p_alto >= b else b

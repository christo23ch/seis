"""Fase 5C — Catálogo técnico de metadatos de parámetros T3 (M12/M13).

Qué es esto y qué NO es
------------------------
Este módulo describe, para cada parámetro T3 relevante en la decisión (M12) y
la estrategia de puja (M13), sus METADATOS: nombre legible, módulo, unidad,
si es editable, en qué rango (si se conoce objetivamente), etc.

NO es el almacén de valores — eso sigue siendo exclusivamente
`app.engine.params.store.Parametros` / `defaults.yaml`. Este catálogo no
guarda ningún valor propio; `resolver_valor_referencia()` lee el valor
vigente bajo demanda desde un `Parametros` real (por defecto, los defaults
de fábrica). Así se evita que el catálogo y `defaults.yaml` diverjan.

Tampoco es un motor de simulación, ni persiste nada, ni depende de la BD ni
de ninguna `Session` de SQLAlchemy. Es un componente Python puro, pensado
para que un futuro frontend avanzado (Fase 5D en adelante, no implementada
aquí) pueda listar qué se puede ajustar y con qué información se cuenta hoy.

Disciplina "no inventar" (obligatoria, ver Fase 5C)
----------------------------------------------------
`rango`, `advertencia`, `impacto` y `nivel_riesgo_modificacion` solo llevan
un valor concreto cuando ese valor es objetivamente derivable del código
(una fórmula cuyo signo es inequívoco, una variable con cota matemática
demostrada, una restricción que el propio código ya aplica). Cuando no hay
esa base, el campo vale `PENDIENTE_DE_DEFINIR` — nunca una estimación de
lo que "sonaría razonable". Ver el docstring de cada constante de abajo
para la justificación puntual de los pocos casos en que SÍ se ha podido
rellenar un rango o un impacto.

Estructura
----------
- `ParametroCatalogo`: metadato de una clave T3 física y concreta (o de una
  constante hardcodeada sin clave T3, TIPO 2).
- `ParametroPlantilla` + `resolver_plantillas()`: para dimensiones abiertas
  o mantenidas dinámicamente en YAML (perfil, banda de riesgo, fuente de
  subasta) — el catálogo describe el patrón una vez y lo expande contra un
  `Parametros` real, en vez de enumerar a mano combinaciones que ya viven
  en `defaults.yaml` y podrían desincronizarse.
- `CalculoDerivado`: TIPO 3, informativo, nunca editable — intermedios que
  M12/M13 calculan pero no persisten hoy (ver Fase 5, inspección M12/M13).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.engine.params.store import Parametros, cargar_defaults

PENDIENTE_DE_DEFINIR = "pendiente_de_definir"

Modulo = Literal["M12", "M13"]
Grupo = Literal["A", "B"]  # GRUPO C no existe hoy entre los parámetros T3 reales (Fase 5)

# rango: cota concreta | None (no aplica, p.ej. constante no editable) | pendiente
RangoValor = tuple[float, float] | None | Literal["pendiente_de_definir"]
TextoOpcional = str | Literal["pendiente_de_definir"]


@dataclass(frozen=True)
class ParametroCatalogo:
    """Metadato de UNA clave T3 física (o de una constante hardcodeada TIPO 2)."""

    clave: str
    nombre_legible: str
    modulo: Modulo
    descripcion: str
    unidad: str
    editable: bool
    rango: RangoValor
    advertencia: TextoOpcional
    impacto: TextoOpcional
    dependencia: Grupo | None  # None solo para TIPO 2 (no aplica el grafo de simulación)
    nivel_riesgo_modificacion: TextoOpcional
    origen: str = ""  # archivo:línea de referencia, informativo


@dataclass(frozen=True)
class ParametroPlantilla:
    """Metadato de un patrón `perfiles.{perfil}.m_objetivo`-like.

    No tiene una única `clave` física: `dimension_variable` nombra el eje
    (p.ej. "perfil"), `seccion_dimension` la ruta T3 cuyas claves hijas son
    las instancias válidas de ese eje, y `subclave` el nombre del campo que
    se lee dentro de cada instancia. `resolver_plantillas()` expande esto
    contra un `Parametros` real, incluyendo solo las instancias que
    realmente tienen `subclave` (p.ej. el perfil `rentista` no tiene
    `m_objetivo`/`m_minimo` — ver `defaults.yaml`, sección `perfiles`).
    """

    patron_clave: str
    dimension_variable: str
    seccion_dimension: str
    subclave: str
    nombre_legible: str
    modulo: Modulo
    descripcion: str
    unidad: str
    editable: bool
    rango: RangoValor
    advertencia: TextoOpcional
    impacto: TextoOpcional
    dependencia: Grupo
    nivel_riesgo_modificacion: TextoOpcional
    origen: str = ""


@dataclass(frozen=True)
class ParametroResuelto:
    """Una instancia concreta de una `ParametroPlantilla` contra un `Parametros` real."""

    clave: str
    valor_referencia: object
    plantilla: ParametroPlantilla


@dataclass(frozen=True)
class CalculoDerivado:
    """TIPO 3 — valor intermedio calculado por M12/M13 y no persistido hoy.

    Puramente informativo: no tiene `clave` T3, no es editable, no aparece
    en `obtener_catalogo()` ni en `obtener_parametros_editables()`. Ver
    `obtener_calculos_derivados()`.
    """

    nombre: str
    modulo: Modulo
    descripcion: str
    origen: str


# ─────────────────────────── Cotas técnicas objetivas ───────────────────────────
# No son "rangos profesionales recomendados": son cotas que el propio código
# demuestra matemáticamente sobre la variable que el parámetro umbral compara.
# Un umbral fuera de esta cota sería, por construcción, o bien inalcanzable o
# bien trivialmente siempre cierto — no una elección de negocio inventada.
_COTA_ICO = (0.0, 100.0)   # m12_decision.py:198 — Σ pesos=100, cada utilidad∈[0,100]
_COTA_ICI = (0.0, 100.0)   # m02_validacion.py:55 — ici = max(0, min(100, ...))
_COTA_RA = (0.0, 100.0)    # m12_decision.py:38  — ra = round(min(100, ra))
_COTA_MS = (0.0, 1.0)      # m12_decision.py:287 — margen_seguridad = max(0.0, 1 - i/vs)

_NOTA_PESOS_SUMAN_100 = (
    "Nota técnica: en defaults.yaml, los pesos de esta sección suman 100 "
    "(o 1.00, según escala); el código no impone ni verifica esta restricción "
    "en tiempo de ejecución — es una propiedad del YAML actual, no una regla."
)


# ══════════════════════════ TIPO 1 · M12 · riesgos ══════════════════════════

_RIESGOS_PESOS_DIMS = (
    "juridico", "documental", "ocupacion", "urbanistico", "tecnico",
    "financiero", "comercial", "liquidez", "mercado",
)

PARAMETROS_FIJOS: list[ParametroCatalogo] = []

for _dim in _RIESGOS_PESOS_DIMS:
    PARAMETROS_FIJOS.append(ParametroCatalogo(
        clave=f"riesgos.pesos.{_dim}",
        nombre_legible=f"Peso de riesgo — {_dim}",
        modulo="M12",
        descripcion=(
            f"Peso de la dimensión de riesgo '{_dim}' en el cálculo de RA "
            "base (agregar_ra, §7.6): ra_base = Σ pesos[dim] · (score/25) · 100."
        ),
        unidad="peso relativo (adimensional)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=_NOTA_PESOS_SUMAN_100,
        impacto=PENDIENTE_DE_DEFINIR,
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:21-22 (agregar_ra)",
    ))

for _clave_dom, _nombre_dom in (
    ("una_alta", "Dominancia — una dimensión en nivel alto"),
    ("dos_altas", "Dominancia — dos o más dimensiones en nivel alto"),
    ("critica_mitigable", "Dominancia — dimensión crítica mitigable"),
    ("critica_no_mitigable", "Dominancia — dimensión crítica no mitigable"),
):
    PARAMETROS_FIJOS.append(ParametroCatalogo(
        clave=f"riesgos.dominancia.{_clave_dom}",
        nombre_legible=_nombre_dom,
        modulo="M12",
        descripcion=(
            "Suelo de RA (0-100) que se impone cuando se dispara esta condición "
            "de dominancia — RA final = max(ra_base, este_valor) (agregar_ra, §7.6)."
        ),
        unidad="puntos de RA (0-100)",
        editable=True,
        rango=_COTA_RA,
        advertencia=(
            "Cota técnica: RA queda siempre acotado a [0, 100] por "
            "`ra = round(min(100, ra))` (m12_decision.py:38); un valor fuera "
            "de ese rango para el suelo de dominancia no tiene efecto adicional "
            "más allá de saturar en 100."
        ),
        impacto=PENDIENTE_DE_DEFINIR,
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:26-36 (agregar_ra)",
    ))

PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="riesgos.bandas_ra",
    nombre_legible="Bandas de RA (tramos con banda asociada)",
    modulo="M12",
    descripcion=(
        "Lista de tramos {max, banda} que clasifica el RA final en una banda "
        "textual (agregar_ra, §7.6). Estructura de lista, no un escalar único."
    ),
    unidad="lista de tramos [{max: puntos RA, banda: str}]",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=(
        "Los valores `max` de cada tramo son puntos de RA y por tanto quedan "
        "dentro de [0, 100] por la misma cota que riesgos.dominancia.*; no se "
        "verifica en código que los tramos sean monótonos crecientes ni que "
        "cubran todo el rango."
    ),
    impacto=PENDIENTE_DE_DEFINIR,
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:39 (agregar_ra)",
))


# ══════════════════════════ TIPO 1 · M12 · valoracion (delta_v) ══════════════════════════

PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="valoracion.delta_base_pp",
    nombre_legible="Delta base de prudencia sobre VS",
    modulo="M12",
    descripcion=(
        "Puntos porcentuales base que arrancan el cálculo de δ_v, el descuento "
        "de prudencia aplicado sobre VS para obtener VS_prudente (§9.4)."
    ),
    unidad="puntos porcentuales (pp)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "δ_v mayor ⇒ VS_prudente menor (vs_p = vs·(1-δ_v)) ⇒ toda la escalera "
        "de precios (p_ideal/p_objetivo/p_max) resulta más baja. Derivado "
        "directamente de la fórmula, no de criterio profesional."
    ),
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:46 (calcular_delta_v)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="valoracion.delta_dispersion",
    nombre_legible="Delta adicional por dispersión de comparables (tramos por CV)",
    modulo="M12",
    descripcion=(
        "Lista de tramos {max_cv, pp} que añaden pp a δ_v según la dispersión "
        "(coeficiente de variación) de los comparables usados por M03 (§9.4)."
    ),
    unidad="lista de tramos [{max_cv: float, pp: puntos porcentuales}]",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "Cada `pp` de un tramo, si se activa, aumenta δ_v y por tanto reduce "
        "VS_prudente y toda la escalera de precios — mismo sentido que "
        "delta_base_pp, derivado de la misma fórmula."
    ),
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:48-51 (calcular_delta_v)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="valoracion.delta_max_pct",
    nombre_legible="Tope máximo de delta de prudencia",
    modulo="M12",
    descripcion="Cota superior de δ_v tras sumar todos sus componentes (§9.4).",
    unidad="fracción (0-1)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=(
        "Actúa como techo de `min(delta/100.0, delta_max_pct)`; un valor "
        "≥ 1.0 anularía el efecto de tope (VS_prudente podría llegar a 0 o "
        "negativo si δ_v se acerca a 1) — observación estructural, no un "
        "rango de negocio."
    ),
    impacto=(
        "Techo más alto ⇒ δ_v puede crecer más en escenarios ya penalizados "
        "⇒ VS_prudente puede reducirse más. Sentido derivado de la fórmula."
    ),
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:53 (calcular_delta_v)",
))


# ══════════════════════════ TIPO 1 · M12 · precios / capital / financiacion ══════════════════════════

PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="precios.m_exc_mult",
    nombre_legible="Multiplicador de margen 'excelente' (p_ideal)",
    modulo="M12",
    descripcion=(
        "Multiplica el margen objetivo del perfil para obtener el margen "
        "'excelente' que fija p_ideal en la rama de venta (calcular_escalera, §9.1)."
    ),
    unidad="multiplicador (adimensional)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "m_exc = m_objetivo · m_exc_mult, y `_precio_venta` es decreciente en "
        "el margen `m` (vs/(1+m) decrece si m crece) ⇒ un multiplicador mayor "
        "reduce p_ideal. Derivado del álgebra de la fórmula."
    ),
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:74 (calcular_escalera, rama venta)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="financiacion.stress_tipos_pp",
    nombre_legible="Estrés de tipos de interés sobre financiación",
    modulo="M12",
    descripcion=(
        "Puntos porcentuales que se suman al tipo de interés de la hipoteca "
        "antes de calcular el candidato de precio limitado por DSCR (rentista, §9.2)."
    ),
    unidad="puntos porcentuales (pp)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=PENDIENTE_DE_DEFINIR,
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:106 (calcular_escalera, rama rentista)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="financiacion.dscr_minimo",
    nombre_legible="DSCR mínimo exigido (estresado)",
    modulo="M12",
    descripcion=(
        "Ratio de cobertura de deuda mínimo exigido, bajo el tipo de interés "
        "ya estresado, para el candidato de precio limitado por financiación "
        "(rentista, §9.2). DSCR = renta neta anual / servicio de deuda anual."
    ),
    unidad="ratio (adimensional)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=PENDIENTE_DE_DEFINIR,
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:107-108 (calcular_escalera, rama rentista)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="capital.coste_capital_anual",
    nombre_legible="Coste de capital anual",
    modulo="M12",
    descripcion=(
        "Coste anual de oportunidad del capital inmovilizado, restado de "
        "P_límite: coste_capital = cc_anual · inversión_aprox · plazo/12 (§9.1)."
    ),
    unidad="fracción anual (0-1)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "coste_capital crece linealmente con este parámetro y se resta de "
        "p_lim_bruto ⇒ un valor mayor reduce P_límite. Derivado directamente "
        "de `p_lim = p_lim_bruto - coste_capital`."
    ),
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:121-126 (calcular_escalera)",
))


# ══════════════════════════ TIPO 1 · M12 · ico ══════════════════════════

_ICO_PESOS_CATS = (
    "rentabilidad", "juridico", "urbanistico", "financiero",
    "ubicacion", "revalorizacion", "liquidez", "informacion",
)
for _cat in _ICO_PESOS_CATS:
    PARAMETROS_FIJOS.append(ParametroCatalogo(
        clave=f"ico.pesos.{_cat}",
        nombre_legible=f"Peso ICO — {_cat}",
        modulo="M12",
        descripcion=(
            f"Peso de la categoría '{_cat}' en el índice de conveniencia de "
            "oportunidad: ICO = Σ pesos[k]·u[k] / 100 (calcular_ico, §8.5)."
        ),
        unidad="peso relativo (suma≈100)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=_NOTA_PESOS_SUMAN_100,
        impacto=PENDIENTE_DE_DEFINIR,
        dependencia="A",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:166,198 (calcular_ico)",
    ))

PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="ico.escalon_alta",
    nombre_legible="Escalón de penalización por riesgo alto/crítico",
    modulo="M12",
    descripcion=(
        "Puntos que se restan a la utilidad de un grupo de riesgo cuando "
        "alguna dimensión del grupo está en nivel alto o crítico (_u_grupo_riesgo, §8.5)."
    ),
    unidad="puntos de utilidad (0-100)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "Un escalón mayor reduce más la utilidad del grupo afectado, y por "
        "tanto reduce ICO (ICO es una media ponderada de utilidades). "
        "Sentido derivado de la fórmula, no una magnitud concreta."
    ),
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:154-160,169 (_u_grupo_riesgo)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="ico.bonus_equity_financiero",
    nombre_legible="Bonus de utilidad financiera por compra al contado",
    modulo="M12",
    descripcion=(
        "Puntos que se suman a la utilidad financiera cuando la financiación "
        "es 'cash', con tope en 100 (calcular_ico, §8.5)."
    ),
    unidad="puntos de utilidad (0-100)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=(
        "El resultado queda acotado por `min(100.0, u_fin + bonus)`: un "
        "bonus mayor del necesario para saturar en 100 no tiene efecto "
        "adicional — observación estructural, no un rango de negocio."
    ),
    impacto=(
        "Bonus mayor ⇒ utilidad financiera mayor (hasta el tope 100) ⇒ ICO "
        "mayor en operaciones al contado. Derivado de la fórmula."
    ),
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:181-182 (calcular_ico)",
))
for _clave_dom2, _nombre_dom2 in (
    ("full", "Días de comercialización — liquidez plena (utilidad 100)"),
    ("zero", "Días de comercialización — liquidez nula (utilidad 0)"),
):
    PARAMETROS_FIJOS.append(ParametroCatalogo(
        clave=f"ico.liquidez_dom.{_clave_dom2}",
        nombre_legible=_nombre_dom2,
        modulo="M12",
        descripcion=(
            "Extremo de la escala lineal de utilidad de liquidez sobre días "
            "de comercialización (DOM): u_liq = 100·(zero - dom)/(zero - full), "
            "acotada a [0,100] (calcular_ico, §8.5). DOM en alquiler se "
            "compara ya multiplicado ×3 respecto a DOM en venta (hardcode, "
            "ver `hardcode.m12.multiplicador_dom_alquiler`)."
        ),
        unidad="días",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=PENDIENTE_DE_DEFINIR,
        dependencia="A",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:184-186 (calcular_ico)",
    ))
for _clave_ur, _nombre_ur in (
    ("cero_en_frac_min", "Fracción del margen mínimo donde la utilidad de rentabilidad es cero"),
    ("u_objetivo", "Utilidad de rentabilidad en el margen/yield objetivo"),
    ("u_max_frac", "Fracción del margen objetivo donde la utilidad satura en 100"),
):
    PARAMETROS_FIJOS.append(ParametroCatalogo(
        clave=f"ico.utilidad_rentabilidad.{_clave_ur}",
        nombre_legible=_nombre_ur,
        modulo="M12",
        descripcion=(
            "Parámetro de la curva lineal a tramos de utilidad de "
            "rentabilidad (_u_rentabilidad, §8.5): 0 por debajo del umbral "
            "mínimo, u_objetivo en el objetivo, 100 en el techo."
        ),
        unidad="fracción o puntos de utilidad según la clave",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=PENDIENTE_DE_DEFINIR,
        dependencia="A",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:141-151 (_u_rentabilidad)",
    ))

PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="ici.multiplicador_ico_umbral",
    nombre_legible="Umbral de ICI para penalización estructural de ICO",
    modulo="M12",
    descripcion=(
        "Si ICI queda por debajo de este umbral, ICO se penaliza "
        "multiplicándolo por 0.80 + 0.20·ICI/umbral (calcular_ico, §8.5). "
        "El literal 0.80/0.20 es un hardcode TIPO 2, no editable aquí — ver "
        "`hardcode.m12.coeficiente_base_penalizacion_ici` y "
        "`hardcode.m12.coeficiente_variable_penalizacion_ici`."
    ),
    unidad="puntos de ICI (0-100)",
    editable=True,
    rango=_COTA_ICI,
    advertencia=(
        "Cota técnica: ICI queda acotado a [0, 100] por "
        "`ici = max(0, min(100, ...))` (m02_validacion.py:55); un umbral "
        "por encima de 100 penalizaría siempre, uno por debajo de 0 nunca."
    ),
    impacto=(
        "Umbral mayor ⇒ más casos con ICI por debajo de él ⇒ penalización "
        "de ICO se aplica con más frecuencia. Derivado de la comparación "
        "`ici < umbral`."
    ),
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:199-201 (calcular_ico)",
))


# ══════════════════════════ TIPO 1 · M12 · semaforo ══════════════════════════

_SEMAFORO_COLORES: dict[str, tuple[str, ...]] = {
    "verde": ("ico_min", "ms_valor_min", "rvc_min", "ici_min"),
    "amarillo": ("ico_min", "pes_piso_frac_i", "rvc_min", "ici_min"),
    "naranja": ("ico_min", "rvc_min"),
}
_SEMAFORO_DESC = {
    "ico_min": ("ICO mínimo exigido para este color", "puntos de ICO (0-100)", _COTA_ICO,
                "Cota técnica: ICO∈[0,100] por construcción (Σ pesos=100, "
                "utilidades∈[0,100]) — m12_decision.py:198."),
    "ms_valor_min": ("Margen de seguridad de valor mínimo exigido", "fracción (0-1)", _COTA_MS,
                     "Cota técnica: margen_seguridad = max(0.0, 1 - i_total/vs), "
                     "por construcción en [0, 1) — m12_decision.py:287."),
    "rvc_min": ("RVC mínimo exigido", "ratio (adimensional, puede ser negativo)", PENDIENTE_DE_DEFINIR,
                "RVC = p_max/p_adj no está acotado por el código (puede ser "
                "negativo o crecer sin límite) — no hay cota técnica que citar."),
    "ici_min": ("ICI mínimo exigido para este color", "puntos de ICI (0-100)", _COTA_ICI,
                "Cota técnica: ICI∈[0,100] por `max(0, min(100, ...))` "
                "— m02_validacion.py:55."),
    "pes_piso_frac_i": ("Piso del escenario pesimista, como fracción de la inversión",
                        "fracción de inversión total", PENDIENTE_DE_DEFINIR, PENDIENTE_DE_DEFINIR),
}
for _color, _campos in _SEMAFORO_COLORES.items():
    for _campo in _campos:
        _nombre_c, _unidad_c, _rango_c, _adv_c = _SEMAFORO_DESC[_campo]
        PARAMETROS_FIJOS.append(ParametroCatalogo(
            clave=f"semaforo.{_color}.{_campo}",
            nombre_legible=f"Semáforo {_color} — {_nombre_c}",
            modulo="M12",
            descripcion=(
                f"Umbral '{_campo}' evaluado en `decidir_semaforo` (§8.6) para "
                f"que el candidato de semáforo pueda ser '{_color}'."
            ),
            unidad=_unidad_c,
            editable=True,
            rango=_rango_c,
            advertencia=_adv_c,
            impacto=(
                f"Umbral más exigente (más alto para *_min) ⇒ más difícil "
                f"alcanzar '{_color}' ⇒ semáforo más conservador en ese color."
            ) if _campo != "pes_piso_frac_i" else PENDIENTE_DE_DEFINIR,
            dependencia="A",
            nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
            origen="m12_decision.py:221-281 (decidir_semaforo)",
        ))


# ══════════════════════════ TIPO 1 · M13 · adjudicacion ══════════════════════════

PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="adjudicacion.ajuste_desierta_pp",
    nombre_legible="Ajuste de ratio por subasta desierta previa",
    modulo="M13",
    descripcion=(
        "Puntos porcentuales que se suman al ratio de adjudicación por cada "
        "subasta desierta previa (§11.1, valor típicamente negativo: cada "
        "desierta reduce el ratio esperado)."
    ),
    unidad="puntos porcentuales de ratio, por subasta desierta previa",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "ratio += ajuste·nº_desiertas; p_adj = vt·ratio; RVC = p_max/p_adj. "
        "Si el ajuste es negativo (caso actual en defaults.yaml), más "
        "desiertas ⇒ ratio menor ⇒ p_adj menor ⇒ RVC mayor. Derivado del "
        "álgebra, condicionado al signo configurado."
    ),
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m13_puja.py:29 (ejecutar)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="adjudicacion.ajuste_chollo_pp",
    nombre_legible="Ajuste de ratio cuando VT/VM < 0.6 ('chollo')",
    modulo="M13",
    descripcion=(
        "Puntos porcentuales que se suman al ratio de adjudicación cuando el "
        "valor de subasta es muy inferior al valor de mercado (umbral "
        "hardcodeado 0.6, TIPO 2 — ver `hardcode.m13.umbral_chollo_vt_vm`)."
    ),
    unidad="puntos porcentuales de ratio",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "ratio += ajuste (si se activa); p_adj = vt·ratio; RVC = p_max/p_adj. "
        "Con signo positivo (caso actual), un ajuste mayor sube p_adj y baja "
        "RVC. Derivado del álgebra, condicionado al signo configurado."
    ),
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m13_puja.py:30-31 (ejecutar)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="adjudicacion.rvc_bandas",
    nombre_legible="Bandas de RVC (tramos con banda asociada)",
    modulo="M13",
    descripcion=(
        "Lista de tramos {min, banda} que clasifica el RVC en una banda "
        "textual ('inviable', 'improbable', 'ajustado', etc., §11.1). "
        "Debe terminar cubriendo valores negativos (RVC puede ser negativo, "
        "ver comentario en m13_puja.py:36-48) — el propio código usa "
        "`next(..., \"inviable\")` como último respaldo."
    ),
    unidad="lista de tramos [{min: ratio, banda: str}]",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=(
        "RVC no está acotado por el código (puede ser negativo o crecer sin "
        "límite): no hay cota técnica aplicable a los valores `min` de esta "
        "lista, a diferencia de las cotas de ICO/ICI/RA."
    ),
    impacto=PENDIENTE_DE_DEFINIR,
    dependencia="A",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m13_puja.py:49-50 (ejecutar)",
))

# Fase 5C.1 — cierre de las 3 claves T3 físicas de `perfiles.rentista` detectadas
# por la auditoría PRE-5D: no existen en ningún otro perfil (solo `rentista`
# tiene `tipo: rentista` en defaults.yaml hoy), así que se representan como
# entradas fijas — no como plantilla — igual que el resto de `PARAMETROS_FIJOS`.
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="perfiles.rentista.coc_min",
    nombre_legible="Cash-on-cash mínimo (perfil rentista)",
    modulo="M12",
    descripcion=(
        "Ratio de cash-on-cash mínimo exigido en la rama rentista con "
        "financiación hipotecaria; interviene como un candidato adicional "
        "de precio máximo (`p_de_coc`), evaluado solo si "
        "`financiacion.tipo == 'hipoteca'` y `ltv > 0` (§9.2)."
    ),
    unidad="ratio (adimensional)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "El candidato `p_de_coc` (m12_decision.py:111-115) es decreciente en "
        "`coc_min` en el rango realista de LTV/tipo de interés — en la "
        "derivada, el término cruzado que depende de `coc` se cancela "
        "algebraicamente y el signo resultante es negativo siempre que "
        "LTV < 1 + coste variable efectivo. coc_min mayor ⇒ ese candidato "
        "de precio menor, y p_max puede bajar si pasa a ser el mínimo entre "
        "los candidatos evaluados."
    ),
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:109,111-115 (calcular_escalera, rama rentista con hipoteca)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="perfiles.rentista.y_suelo_pp_sobre_bono",
    nombre_legible="Prima sobre el bono a 10 años (suelo de yield, perfil rentista)",
    modulo="M12",
    descripcion=(
        "Puntos porcentuales sumados a `y_bono_10a` para formar `y_suelo`, "
        "el yield mínimo que fija el candidato de precio límite en la rama "
        "rentista: `p_lim_rent = p_de_y(y_suelo)` (§9.1-9.2)."
    ),
    unidad="puntos porcentuales (pp)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "y_suelo = y_bono_10a + y_suelo_pp_sobre_bono, y `p_de_y` es "
        "decreciente en el yield exigido (m12_decision.py:96-100: "
        "`rna/(y/100)` decrece si y crece) ⇒ y_suelo_pp_sobre_bono mayor ⇒ "
        "p_lim_rent menor ⇒ P_límite puede bajar (`p_lim = min(p_lim, "
        "p_lim_rent)` si p_lim_rent > 0, línea 128)."
    ),
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:94,117,128 (calcular_escalera, rama rentista)",
))
PARAMETROS_FIJOS.append(ParametroCatalogo(
    clave="perfiles.rentista.y_bono_10a",
    nombre_legible="Yield de referencia del bono a 10 años (perfil rentista)",
    modulo="M12",
    descripcion=(
        "Yield de referencia (bono soberano a 10 años) usado como base de "
        "`y_suelo` junto con `y_suelo_pp_sobre_bono`, para el candidato de "
        "precio límite en la rama rentista (§9.1-9.2)."
    ),
    unidad="puntos porcentuales (%)",
    editable=True,
    rango=PENDIENTE_DE_DEFINIR,
    advertencia=PENDIENTE_DE_DEFINIR,
    impacto=(
        "Mismo sentido que y_suelo_pp_sobre_bono: y_bono_10a mayor ⇒ "
        "y_suelo mayor ⇒ p_lim_rent menor ⇒ P_límite puede bajar."
    ),
    dependencia="B",
    nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
    origen="m12_decision.py:94,117,128 (calcular_escalera, rama rentista)",
))


# ══════════════════════════ TIPO 2 · constantes hardcodeadas (no editables) ══════════════════════════

CONSTANTES_HARDCODE: list[ParametroCatalogo] = [
    ParametroCatalogo(
        clave="hardcode.m12.divisor_score_maximo",
        nombre_legible="Divisor de score máximo en RA base",
        modulo="M12",
        descripcion=(
            "Divide el score de cada dimensión de riesgo (score/25) antes de "
            "ponderar por su peso en ra_base; 25 es el score máximo posible "
            "de una dimensión, no un parámetro configurable."
        ),
        unidad="score máximo posible por dimensión",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:22 (agregar_ra)",
    ),
    ParametroCatalogo(
        clave="hardcode.m12.multiplicador_dom_alquiler",
        nombre_legible="Multiplicador ×3 de DOM en alquiler",
        modulo="M12",
        descripcion=(
            "Los días de comercialización en alquiler se multiplican ×3 "
            "antes de compararlos con los umbrales de liquidez de "
            "`ico.liquidez_dom`, para hacerlos comparables con DOM de venta."
        ),
        unidad="factor multiplicativo",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:185 (calcular_ico)",
    ),
    ParametroCatalogo(
        clave="hardcode.m12.umbral_dom_alquiler_prima_iliquidez",
        nombre_legible="Umbral de días DOM-alquiler para prima de iliquidez",
        modulo="M12",
        descripcion=(
            "Si dom_alquiler_dias > 60, se suma una prima de iliquidez al "
            "yield requerido en la rama rentista (§9.2)."
        ),
        unidad="días",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:89-90 (calcular_escalera, rama rentista)",
    ),
    ParametroCatalogo(
        clave="hardcode.m12.prima_iliquidez_alquiler",
        nombre_legible="Prima de iliquidez de alquiler",
        modulo="M12",
        descripcion="Puntos porcentuales sumados al yield requerido cuando se supera el umbral de días DOM-alquiler.",
        unidad="puntos porcentuales (pp)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:90 (calcular_escalera, rama rentista)",
    ),
    ParametroCatalogo(
        clave="hardcode.m12.umbral_ici_prima_informacion",
        nombre_legible="Umbral de ICI para prima de información",
        modulo="M12",
        descripcion=(
            "Si ICI < 60, se suma una prima de información al yield "
            "requerido en la rama rentista (§9.2). Coincide numéricamente "
            "con `ici.multiplicador_ico_umbral` pero es un literal "
            "independiente — no se lee de ese parámetro T3."
        ),
        unidad="puntos de ICI (0-100)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:91-92 (calcular_escalera, rama rentista)",
    ),
    ParametroCatalogo(
        clave="hardcode.m12.prima_informacion",
        nombre_legible="Prima de información (ICI bajo)",
        modulo="M12",
        descripcion="Puntos porcentuales sumados al yield requerido cuando ICI < 60.",
        unidad="puntos porcentuales (pp)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:92 (calcular_escalera, rama rentista)",
    ),
    ParametroCatalogo(
        clave="hardcode.m12.coeficiente_base_penalizacion_ici",
        nombre_legible="Coeficiente base de la penalización de ICO por ICI bajo",
        modulo="M12",
        descripcion=(
            "Término independiente de `ico *= 0.80 + 0.20 · ici/umbral`: "
            "aunque ICI fuera 0, ICO nunca se penaliza más allá de este suelo."
        ),
        unidad="fracción (0-1)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:201 (calcular_ico)",
    ),
    ParametroCatalogo(
        clave="hardcode.m12.coeficiente_variable_penalizacion_ici",
        nombre_legible="Coeficiente variable de la penalización de ICO por ICI bajo",
        modulo="M12",
        descripcion="Coeficiente que multiplica ici/umbral en la misma fórmula de penalización.",
        unidad="fracción (0-1)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m12_decision.py:201 (calcular_ico)",
    ),
    ParametroCatalogo(
        clave="hardcode.m13.ratio_fallback_sin_segmento",
        nombre_legible="Ratio de respaldo sin segmento de adjudicación",
        modulo="M13",
        descripcion=(
            "Valor de respaldo usado si ni la fuente, ni su 'default', ni la "
            "tipología/estado concretos tienen un ratio configurado en "
            "`adjudicacion.ratios` — evita un `None`/`KeyError` en runtime."
        ),
        unidad="ratio (adimensional)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m13_puja.py:19-20 (_ratio_segmento)",
    ),
    ParametroCatalogo(
        clave="hardcode.m13.ratio_clamp_min",
        nombre_legible="Cota mínima del ratio de adjudicación final",
        modulo="M13",
        descripcion="Cota inferior aplicada al ratio tras todos los ajustes de capa B (§11.1).",
        unidad="ratio (adimensional)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m13_puja.py:32 (ejecutar)",
    ),
    ParametroCatalogo(
        clave="hardcode.m13.ratio_clamp_max",
        nombre_legible="Cota máxima del ratio de adjudicación final",
        modulo="M13",
        descripcion="Cota superior aplicada al ratio tras todos los ajustes de capa B (§11.1).",
        unidad="ratio (adimensional)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m13_puja.py:32 (ejecutar)",
    ),
    ParametroCatalogo(
        clave="hardcode.m13.umbral_chollo_vt_vm",
        nombre_legible="Umbral VT/VM para considerar 'chollo'",
        modulo="M13",
        descripcion=(
            "Si valor_subasta/VM < 0.6, se activa `adjudicacion.ajuste_chollo_pp` "
            "sobre el ratio de adjudicación."
        ),
        unidad="ratio (adimensional)",
        editable=False,
        rango=None,
        advertencia=None,
        impacto=None,
        dependencia=None,
        nivel_riesgo_modificacion=None,
        origen="m13_puja.py:30 (ejecutar)",
    ),
]


# ══════════════════════════ TIPO 1 · plantillas (dimensión variable) ══════════════════════════

PLANTILLAS: list[ParametroPlantilla] = [
    ParametroPlantilla(
        patron_clave="perfiles.{perfil}.m_objetivo",
        dimension_variable="perfil",
        seccion_dimension="perfiles",
        subclave="m_objetivo",
        nombre_legible="Margen objetivo del perfil",
        modulo="M12",
        descripcion=(
            "Margen objetivo (rama 'venta') usado para p_objetivo y como base "
            "de m_exc/m_min ajustados por banda de riesgo (§9.1, §10). Solo "
            "existe en perfiles con tipo='venta' — el perfil 'rentista' no "
            "tiene esta clave (usa yields, no márgenes; ver `defaults.yaml`)."
        ),
        unidad="fracción de margen (adimensional)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=(
            "m_objetivo mayor ⇒ p_objetivo menor (misma relación decreciente "
            "de `_precio_venta` respecto al margen que en precios.m_exc_mult)."
        ),
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:72,76 (calcular_escalera, rama venta)",
    ),
    ParametroPlantilla(
        patron_clave="perfiles.{perfil}.m_minimo",
        dimension_variable="perfil",
        seccion_dimension="perfiles",
        subclave="m_minimo",
        nombre_legible="Margen mínimo del perfil",
        modulo="M12",
        descripcion=(
            "Margen mínimo (rama 'venta') usado para el candidato p_a de "
            "p_max (§9.1). Solo existe en perfiles con tipo='venta'."
        ),
        unidad="fracción de margen (adimensional)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=(
            "m_minimo mayor ⇒ p_a menor (misma relación decreciente de "
            "`_precio_venta` respecto al margen) ⇒ p_max puede bajar si p_a "
            "pasa a ser el mínimo entre p_a y p_pes."
        ),
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:73,77 (calcular_escalera, rama venta)",
    ),
    # Fase 5C.1 — piso_pesimista_frac_i y rvc_veto, a diferencia de m_objetivo/
    # m_minimo, SÍ existen en los 6 perfiles de defaults.yaml (incluido
    # 'rentista'): no reutilizar el filtro de las dos plantillas anteriores.
    # resolver_plantillas() ya expande por presencia real de la subclave en
    # cada perfil, así que no hace falta ningún cambio de mecanismo — con los
    # 6 perfiles teniendo la subclave, resolverán 6 instancias, no 5.
    ParametroPlantilla(
        patron_clave="perfiles.{perfil}.piso_pesimista_frac_i",
        dimension_variable="perfil",
        seccion_dimension="perfiles",
        subclave="piso_pesimista_frac_i",
        nombre_legible="Piso del escenario pesimista (fracción de la inversión)",
        modulo="M12",
        descripcion=(
            "Presente en los 6 perfiles de defaults.yaml, incluido 'rentista'. "
            "Se consume en dos puntos distintos: dentro de la rama 'venta' de "
            "`calcular_escalera` fija el suelo de la rama pesimista de la "
            "escalera de precios (§9.1); para cualquier perfil —incluido "
            "'rentista'— también se lee en `decidir_semaforo` como parte de "
            "la condición de acceso a semáforo verde (§8.6)."
        ),
        unidad="fracción de la inversión total (adimensional)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=(
            "En la rama venta: piso mayor ⇒ el término (1+piso) crece en el "
            "denominador de p_pes (m12_decision.py:79-82) ⇒ p_pes menor ⇒ "
            "p_max puede bajar si p_pes pasa a ser el mínimo. En la condición "
            "de verde (m12_decision.py:249,252): piso mayor ⇒ el umbral "
            "`piso · i_base` que debe superar el beneficio pesimista es más "
            "alto ⇒ alcanzar verde es más difícil."
        ),
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:79,249 (calcular_escalera rama venta; decidir_semaforo)",
    ),
    ParametroPlantilla(
        patron_clave="perfiles.{perfil}.rvc_veto",
        dimension_variable="perfil",
        seccion_dimension="perfiles",
        subclave="rvc_veto",
        nombre_legible="Umbral de veto por RVC insuficiente",
        modulo="M12",
        descripcion=(
            "Umbral T3 de perfil, presente en los 6 perfiles de "
            "defaults.yaml. `pipeline.py:44` lo lee de `Parametros` y lo "
            "inyecta en la pizarra de hechos del motor de reglas bajo la "
            "clave `perfil.rvc_veto`; la regla T2 `VETO-COMP-01` "
            "(`app/engine/rules/catalogo.yaml:139-151`) lo compara: "
            "`rvc < perfil.rvc_veto`. IMPORTANTE — `rvc_veto` es el "
            "PARÁMETRO T3 que la regla consulta como umbral; no es la regla "
            "en sí (esa es `VETO-COMP-01`, T2, fuera de este catálogo) ni se "
            "lee directamente dentro de `m12_decision.py`/`m13_puja.py`."
        ),
        unidad="ratio (adimensional, mismo dominio que RVC)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=(
            "RVC no está acotado por el código (puede ser negativo o crecer "
            "sin límite) — misma limitación estructural ya señalada para "
            "`adjudicacion.rvc_bandas` y `semaforo.*.rvc_min`: no hay cota "
            "técnica aplicable a este umbral."
        ),
        impacto=(
            "No es una magnitud que desplace un precio o un score: es un "
            "disparador binario no compensable (P6). Si `rvc < rvc_veto`, "
            "el veto se dispara y `decidir_semaforo` fuerza `semaforo="
            "\"rojo\"` antes de evaluar ICO/RA/RVC ponderado "
            "(m12_decision.py:238-239) — un valor más alto hace el veto más "
            "fácil de disparar; uno más bajo, más difícil."
        ),
        dependencia="A",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen=("pipeline.py:44 (inyecta el hecho); regla T2 VETO-COMP-01 en "
                "app/engine/rules/catalogo.yaml:139-151; efecto en "
                "m12_decision.py:238-239 (decidir_semaforo)"),
    ),
    ParametroPlantilla(
        patron_clave="primas_ra.{banda}.mult_m",
        dimension_variable="banda",
        seccion_dimension="primas_ra",
        subclave="mult_m",
        nombre_legible="Multiplicador de margen por banda de riesgo",
        modulo="M12",
        descripcion=(
            "Multiplica m_objetivo/m_minimo del perfil según la banda de RA "
            "del análisis (rama venta, §9.1)."
        ),
        unidad="multiplicador (adimensional)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=(
            "Multiplicador mayor ⇒ márgenes ajustados mayores ⇒ precios de "
            "la escalera menores (misma relación decreciente en el margen)."
        ),
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:72-73 (calcular_escalera, rama venta)",
    ),
    ParametroPlantilla(
        patron_clave="primas_ra.{banda}.stress_mercado",
        dimension_variable="banda",
        seccion_dimension="primas_ra",
        subclave="stress_mercado",
        nombre_legible="Estrés de mercado por banda de riesgo",
        modulo="M12",
        descripcion=(
            "Fracción de caída de VS_prudente aplicada en la rama pesimista "
            "(vs_pesimista = vs_p·(1-stress_mercado), rama venta, §9.1)."
        ),
        unidad="fracción (0-1)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=(
            "Estrés mayor ⇒ vs_pesimista menor ⇒ p_pes menor ⇒ p_max puede "
            "bajar si p_pes pasa a ser el mínimo entre p_a y p_pes."
        ),
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:80-83 (calcular_escalera, rama venta)",
    ),
    ParametroPlantilla(
        patron_clave="primas_ra.{banda}.y_req_pp",
        dimension_variable="banda",
        seccion_dimension="primas_ra",
        subclave="y_req_pp",
        nombre_legible="Prima de yield requerido por banda de riesgo",
        modulo="M12",
        descripcion=(
            "Puntos porcentuales sumados al yield de zona para formar el "
            "yield requerido de la rama rentista (§9.2)."
        ),
        unidad="puntos porcentuales (pp)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=PENDIENTE_DE_DEFINIR,
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:88 (calcular_escalera, rama rentista)",
    ),
    ParametroPlantilla(
        patron_clave="primas_ra.{banda}.delta_mercado_pp",
        dimension_variable="banda",
        seccion_dimension="primas_ra",
        subclave="delta_mercado_pp",
        nombre_legible="Prima de delta de prudencia por banda de riesgo",
        modulo="M12",
        descripcion=(
            "Puntos porcentuales sumados a δ_v según la banda de RA del "
            "análisis (calcular_delta_v, §9.4)."
        ),
        unidad="puntos porcentuales (pp)",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=PENDIENTE_DE_DEFINIR,
        impacto=(
            "Mismo sentido que valoracion.delta_base_pp: más pp ⇒ δ_v mayor "
            "⇒ VS_prudente menor ⇒ escalera de precios más baja."
        ),
        dependencia="B",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m12_decision.py:47 (calcular_delta_v)",
    ),
    ParametroPlantilla(
        patron_clave="adjudicacion.ratios.{fuente}",
        dimension_variable="fuente",
        seccion_dimension="adjudicacion.ratios",
        subclave="",  # sin subclave: el valor de cada fuente ES el nodo completo
        nombre_legible="Ratio de adjudicación base por fuente de subasta",
        modulo="M13",
        descripcion=(
            "Ratio base sobre VT esperado en adjudicación para esta fuente "
            "(judicial_boe, aeat, tgss, concursal, banco, notarial, privada, "
            "default). El valor NO es siempre un escalar: en `judicial_boe` "
            "es una estructura anidada por tipología y, dentro, por estado "
            "de ocupación (ocupado/vacío/desconocida) más un 'default'; en "
            "el resto de fuentes es `{default: ratio}`. `_ratio_segmento` "
            "(m13_puja.py:7-20) resuelve esa estructura en tiempo de "
            "ejecución — este catálogo no aplana esa jerarquía, la expone "
            "tal cual vive en `defaults.yaml` para cada fuente."
        ),
        unidad="ratio (adimensional) o estructura anidada de ratios, según la fuente",
        editable=True,
        rango=PENDIENTE_DE_DEFINIR,
        advertencia=(
            "El ratio final, tras los ajustes de capa B, queda acotado a "
            "[0.10, 1.10] por el propio código (m13_puja.py:32 — TIPO 2, "
            "ver `hardcode.m13.ratio_clamp_min/max`). Esa cota se aplica al "
            "ratio ya ajustado, no directamente al valor T3 base de esta "
            "plantilla, así que no se traslada aquí como rango del parámetro."
        ),
        impacto=(
            "Ratio base mayor ⇒ p_adj_esperado mayor (p_adj = vt·ratio) ⇒ "
            "RVC menor (RVC = p_max/p_adj). Derivado del álgebra."
        ),
        dependencia="A",
        nivel_riesgo_modificacion=PENDIENTE_DE_DEFINIR,
        origen="m13_puja.py:7-20 (_ratio_segmento)",
    ),
]


# ══════════════════════════ TIPO 3 · cálculos derivados (informativo) ══════════════════════════

CALCULOS_DERIVADOS: list[CalculoDerivado] = [
    CalculoDerivado(
        nombre="ra_base",
        modulo="M12",
        descripcion=(
            "RA antes de aplicar el suelo de dominancia — variable local de "
            "`agregar_ra`; el resultado persistido hoy solo guarda `ra` "
            "(tras dominancia) y `ra_base` como campo informativo del "
            "resultado, pero no hay traza de qué regla de dominancia se "
            "evaluó frente a `ra_base` salvo `dominancia_aplicada`."
        ),
        origen="m12_decision.py:22-40 (agregar_ra)",
    ),
    CalculoDerivado(
        nombre="desglose_delta_v",
        modulo="M12",
        descripcion=(
            "Suma parcial de δ_v por componente (base + mercado por banda + "
            "dispersión por CV + efecto ICI) — `calcular_delta_v` solo "
            "devuelve el total ya sumado y truncado por `delta_max_pct`."
        ),
        origen="m12_decision.py:45-53 (calcular_delta_v)",
    ),
    CalculoDerivado(
        nombre="utilidades_ico_crudas",
        modulo="M12",
        descripcion=(
            "Diccionario `utilidades` (rentabilidad/juridico/urbanistico/"
            "financiero/ubicacion/revalorizacion/liquidez/informacion) antes "
            "de ponderar por pesos — el resultado persistido hoy expone "
            "`desglose` ya multiplicado por peso/100, no las utilidades crudas."
        ),
        origen="m12_decision.py:188-198 (calcular_ico)",
    ),
    CalculoDerivado(
        nombre="candidatos_escalera_rentista",
        modulo="M12",
        descripcion=(
            "Lista `candidatos` de precios (por yield, por DSCR, por "
            "cash-on-cash) antes de tomar el mínimo como p_max en la rama "
            "rentista — solo se persiste el `min(candidatos)` final."
        ),
        origen="m12_decision.py:103-116 (calcular_escalera, rama rentista)",
    ),
    CalculoDerivado(
        nombre="candidato_previo_a_techos",
        modulo="M12",
        descripcion=(
            "Color de semáforo `candidato` antes de aplicar los techos "
            "(dominancia crítica, riesgo alto en verde, techo por ICI) — "
            "solo se persiste el semáforo final tras techos."
        ),
        origen="m12_decision.py:251-280 (decidir_semaforo)",
    ),
    CalculoDerivado(
        nombre="ratio_previo_a_ajustes_m13",
        modulo="M13",
        descripcion=(
            "Ratio de adjudicación resuelto por `_ratio_segmento` antes de "
            "sumar los ajustes de capa B (desiertas previas, 'chollo') y del "
            "clamp final [0.10, 1.10] — solo se persiste `ratio_base` ya "
            "ajustado y saturado."
        ),
        origen="m13_puja.py:26-32 (ejecutar)",
    ),
]


# ══════════════════════════════════════ API ══════════════════════════════════════

def obtener_catalogo() -> list[ParametroCatalogo]:
    """Todos los parámetros T3 con clave física concreta: TIPO 1 fijos + TIPO 2.

    No incluye las plantillas (dimensión variable) ni los cálculos derivados
    (TIPO 3) — ver `obtener_plantillas()` / `resolver_plantillas()` y
    `obtener_calculos_derivados()`.
    """
    return list(PARAMETROS_FIJOS) + list(CONSTANTES_HARDCODE)


def obtener_parametro(clave: str) -> ParametroCatalogo | None:
    """Busca por clave exacta entre los parámetros de clave física (fijos + hardcode).

    No resuelve plantillas: una clave ya expandida como
    'perfiles.flip_integral.m_objetivo' no se encuentra aquí — usar
    `resolver_plantillas()` para esas.
    """
    for p in obtener_catalogo():
        if p.clave == clave:
            return p
    return None


def obtener_parametros_editables() -> list[ParametroCatalogo]:
    """Subconjunto editable de `obtener_catalogo()` (excluye TIPO 2 hardcode)."""
    return [p for p in obtener_catalogo() if p.editable]


def obtener_plantillas() -> list[ParametroPlantilla]:
    """Los patrones de dimensión variable (perfil/banda/fuente), sin expandir."""
    return list(PLANTILLAS)


def obtener_calculos_derivados() -> list[CalculoDerivado]:
    """TIPO 3 — informativo, nunca editable, sin clave T3."""
    return list(CALCULOS_DERIVADOS)


def resolver_plantillas(params: Parametros | None = None) -> list[ParametroResuelto]:
    """Expande todas las plantillas contra un `Parametros` real.

    Solo incluye instancias donde la dimensión realmente tiene la subclave
    (p.ej. `perfiles.rentista` no aporta instancia para `m_objetivo`/
    `m_minimo`, porque esas claves no existen en su sección de
    `defaults.yaml`). Si `subclave` es cadena vacía, el valor resuelto es la
    sección completa de esa instancia (caso `adjudicacion.ratios.{fuente}`,
    donde el nodo entero —no un campo suyo— es lo que representa el ratio).
    """
    p = params or cargar_defaults()
    resueltos: list[ParametroResuelto] = []
    for plantilla in PLANTILLAS:
        try:
            seccion = p.seccion(plantilla.seccion_dimension)
        except (KeyError, TypeError):
            continue
        for instancia, valor_instancia in seccion.items():
            if not isinstance(valor_instancia, dict):
                continue
            if plantilla.subclave:
                if plantilla.subclave not in valor_instancia:
                    continue
                valor = valor_instancia[plantilla.subclave]
            else:
                valor = valor_instancia
            clave = plantilla.patron_clave.format(**{plantilla.dimension_variable: instancia})
            resueltos.append(ParametroResuelto(clave=clave, valor_referencia=valor, plantilla=plantilla))
    return resueltos


def resolver_valor_referencia(clave: str, params: Parametros | None = None) -> object:
    """Valor T3 vigente para `clave` (fija o ya expandida de una plantilla).

    Adaptador puro y decoupled de BD: sin `params`, usa los defaults de
    fábrica (`cargar_defaults()`). No hay "sesión de simulación" en la
    Fase 5C — esto SIEMPRE resuelve contra un `Parametros` concreto, nunca
    contra un estado persistido de usuario (eso es Fase 5D, no implementada).
    """
    p = params or cargar_defaults()
    return p.get(clave)

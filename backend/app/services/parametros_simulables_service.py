"""Fase 5F.7.2 — catálogo de parámetros simulables de UN análisis.

Une tres fuentes que ya existen, sin añadir conocimiento propio:

    catalogo.py (5C/5C.1)            → qué es editable y sus metadatos
    cargar_conocimiento(db)          → valor VIGENTE: la base sobre la que
                                       `crear_simulacion` aplica los overrides
    Analisis.parametros_aplicados    → valor ORIGINAL con el que se analizó

Existe para que el editor de overrides no tenga ninguna lista, tipo, rango ni
etiqueta propia: todo lo que el frontend muestre sale de aquí. Solo lectura:
no ejecuta el motor, no escribe y no audita (no hay patrón de auditar lecturas).

Lo que este servicio NO hace, a propósito:
- No aplica ni completa rangos: se devuelven tal cual vienen del catálogo,
  incluido `pendiente_de_definir`.
- No interpreta `dependencia` (A/B): su significado no está documentado.
- No rellena `valor_original` con el vigente cuando falta: declara la carencia.
- `coincide_con_analisis` compara NOMBRES (la instancia de la plantilla con el
  perfil, la fuente o la banda del análisis). No afirma que un parámetro de
  otra instancia no tenga efecto.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import models
from app.engine.params.store import Parametros
from app.parametros import catalogo
from app.services import conocimiento_service

# Dónde está, en el análisis ORIGINAL, el dato con el que se compara cada
# dimensión de plantilla. La banda sale del resultado original, no de una
# simulación: es la del análisis tal como se hizo. Una dimensión que no esté
# aquí, o cuyo dato falte en el análisis, da `coincide_con_analisis = None`.
_DATO_DE_DIMENSION: dict[str, tuple[str, tuple[str, ...]]] = {
    "perfil": ("entrada", ("perfil",)),
    "fuente": ("entrada", ("subasta", "fuente")),
    "banda": ("resultado", ("riesgos", "banda")),
}

_AUSENTE = object()


def _tipo(valor: object) -> str:
    """Solo dos categorías. Otra forma no se clasifica por aproximación: falla
    en voz alta, porque el editor no sabría qué control construir."""
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return "numero"
    if isinstance(valor, (list, dict)):
        return "estructura"
    raise TypeError(f"Tipo de valor sin categoría en el catálogo simulable: {type(valor).__name__}")


def _rango(rango: object) -> object:
    # Tupla (min, max) → lista para JSON. `None` y `pendiente_de_definir`, tal cual.
    return list(rango) if isinstance(rango, tuple) else rango


def _dato(arbol: object, ruta: tuple[str, ...]) -> object | None:
    nodo = arbol
    for parte in ruta:
        if not isinstance(nodo, dict) or parte not in nodo:
            return None
        nodo = nodo[parte]
    return nodo


def _instancia(clave: str, plantilla: catalogo.ParametroPlantilla) -> str:
    """Segmento de `clave` que ocupa el hueco `{dimension}` del patrón."""
    hueco = "{" + plantilla.dimension_variable + "}"
    return clave.split(".")[plantilla.patron_clave.split(".").index(hueco)]


def _plantilla(resuelto: catalogo.ParametroResuelto, analisis: models.Analisis) -> dict:
    p = resuelto.plantilla
    instancia = _instancia(resuelto.clave, p)
    origen = _DATO_DE_DIMENSION.get(p.dimension_variable)
    dato = _dato(getattr(analisis, origen[0]), origen[1]) if origen else None
    return {"patron": p.patron_clave, "dimension": p.dimension_variable,
            "instancia": instancia,
            "coincide_con_analisis": None if dato is None else instancia == dato}


def _editable(clave: str, meta, plantilla: dict | None, vigentes: Parametros,
              originales: Parametros | None) -> dict:
    valor_vigente = vigentes.get(clave)
    valor_original = (originales.get(clave, _AUSENTE) if originales is not None
                      else _AUSENTE)
    disponible = valor_original is not _AUSENTE
    return {
        "clave": clave, "nombre_legible": meta.nombre_legible, "modulo": meta.modulo,
        "descripcion": meta.descripcion, "unidad": meta.unidad,
        "tipo": _tipo(valor_vigente), "rango": _rango(meta.rango),
        "advertencia": meta.advertencia, "impacto": meta.impacto,
        "nivel_riesgo_modificacion": meta.nivel_riesgo_modificacion,
        "dependencia": meta.dependencia, "origen": meta.origen,
        "plantilla": plantilla,
        "valor_vigente": valor_vigente,
        "valor_original": valor_original if disponible else None,
        "difiere_de_original": (valor_original != valor_vigente) if disponible else None,
    }


def _claves_editables(arbol: Parametros):
    """`(clave, metadatos, resuelto | None)` de cada editable: los fijos del
    catálogo y las instancias de plantilla resueltas contra `arbol`. Única
    enumeración de editables de este módulo, para que catálogo y comparación
    no puedan listar conjuntos distintos."""
    for p in catalogo.obtener_parametros_editables():
        yield p.clave, p, None
    for r in catalogo.resolver_plantillas(arbol):
        yield r.clave, r.plantilla, r


def _arbol(datos: dict | None) -> Parametros | None:
    return Parametros(datos) if datos is not None else None


def obtener_parametros_simulables(db: Session, analisis: models.Analisis) -> dict:
    """Catálogo simulable de `analisis`. El llamador ya ha comprobado que el
    análisis pertenece a su organización (`_analisis_propio`)."""
    vigentes, _, _ = conocimiento_service.cargar_conocimiento(db)
    originales = _arbol(analisis.parametros_aplicados)

    editables = [_editable(clave, meta, _plantilla(r, analisis) if r else None,
                           vigentes, originales)
                 for clave, meta, r in _claves_editables(vigentes)]
    editables.sort(key=lambda e: (e["modulo"], e["clave"]))

    no_editables = sorted(
        ({"clave": p.clave, "nombre_legible": p.nombre_legible, "modulo": p.modulo,
          "descripcion": p.descripcion, "unidad": p.unidad, "origen": p.origen}
         for p in catalogo.CONSTANTES_HARDCODE),
        key=lambda e: e["clave"])
    derivados = sorted(
        ({"nombre": d.nombre, "modulo": d.modulo, "descripcion": d.descripcion,
          "origen": d.origen} for d in catalogo.obtener_calculos_derivados()),
        key=lambda d: d["nombre"])

    return {"analisis_id": analisis.id,
            "version_parametros_vigente": vigentes.version,
            "tiene_parametros_originales": originales is not None,
            "editables": editables, "no_editables": no_editables, "derivados": derivados}


# ─────────────────────── comparación original / simulación (Fase 5F.7.3) ───────────────────────
#
# Toda la comparación se decide aquí; el frontend solo pinta. Lee exclusivamente
# snapshots ya persistidos (`Analisis.parametros_aplicados`/`resultado` y los de
# la `Simulacion`): no carga el conocimiento vigente ni ejecuta el motor.

# Campos del resultado que se ponen lado a lado. Todos existen en `decision` del
# `AnalisisResult` persistido (verificado en el Paso 0 de 5F.7.3); ninguno se calcula.
_RESUMEN_RESULTADO: dict[str, tuple[str, ...]] = {
    "semaforo": ("decision", "semaforo"),
    "ico": ("decision", "ico"),
    "ra": ("decision", "ra"),
    "ici": ("decision", "ici"),
    "icu": ("decision", "icu"),
    "p_ideal": ("decision", "precios", "p_ideal"),
    "p_objetivo": ("decision", "precios", "p_objetivo"),
    "p_max": ("decision", "precios", "p_max"),
    "p_limite": ("decision", "precios", "p_limite"),
    "rvc": ("decision", "rvc"),
    "p_adj_esperado": ("decision", "p_adj_esperado"),
    "margen_seguridad_valor": ("decision", "margen_seguridad_valor"),
}


# Hoja raíz del árbol que NO es un parámetro (ver docstring de `comparar_simulacion`).
# Solo la clave exacta en la raíz: una `version` anidada seguiría comparándose.
_HOJA_VERSION = "version"


def _resumen_resultado(resultado: object) -> dict:
    return {campo: _dato(resultado, ruta) for campo, ruta in _RESUMEN_RESULTADO.items()}


def _hojas(nodo: object, prefijo: str = "") -> dict[str, object]:
    """Árbol → `{ruta con puntos: valor}`. Un objeto no vacío se recorre; una
    lista entera, un escalar o un objeto vacío es UNA hoja."""
    if isinstance(nodo, dict) and nodo:
        hojas: dict[str, object] = {}
        for k, v in nodo.items():
            hojas.update(_hojas(v, f"{prefijo}.{k}" if prefijo else str(k)))
        return hojas
    return {prefijo: nodo}


def _cubierta(ruta: str, editables: set[str]) -> bool:
    """¿La hoja es una clave editable o está DENTRO de una (subclave de una
    estructura, que se compara completa en su propia fila)?"""
    partes = ruta.split(".")
    return any(".".join(partes[:i]) in editables for i in range(1, len(partes) + 1))


def _fila(clave: str, meta, sim: models.Simulacion, hay_original: bool,
          valor_original: object, valor_aplicado: object) -> dict:
    tiene_override = clave in sim.overrides
    if hay_original:
        modificado = valor_aplicado != valor_original
        causa = (("override" if tiene_override else "conocimiento_vigente")
                 if modificado else None)
    else:
        # Sin árbol original no hay contra qué comparar: solo consta lo que el
        # usuario sobrescribió. El original nunca se rellena con otro valor.
        modificado = tiene_override
        causa = "override" if tiene_override else None
    return {"clave": clave,
            "nombre_legible": meta.nombre_legible if meta else None,
            "unidad": meta.unidad if meta else None,
            "editable": meta is not None,
            "valor_original": valor_original if hay_original else None,
            "override": sim.overrides.get(clave), "tiene_override": tiene_override,
            "valor_aplicado": valor_aplicado,
            "modificado": modificado, "causa": causa}


def comparar_simulacion(analisis: models.Analisis, sim: models.Simulacion) -> dict:
    """Original frente a simulación. El llamador ya ha comprobado organización
    (`_analisis_propio`) y pertenencia de la simulación (`obtener_simulacion`).

    Filas de `parametros`:
      a) las claves editables, siempre (instancias de plantilla resueltas contra
         el árbol de la SIMULACIÓN, que es el que usó el motor);
      b) toda hoja que difiera entre los dos árboles completos y no esté cubierta
         por (a), como no editable. Sin árbol original, (b) queda vacío.
         Única exclusión: la hoja RAÍZ `version`. Es la versión del árbol, un
         metadato y no un parámetro (cambia a `…+Nov` en cuanto hay un override
         global), y la respuesta ya la da en `simulacion.version_parametros_base`
         y `original.version_parametros`. Como fila solo duplicaría ese dato
         disfrazado de parámetro modificado.
    `modificado`/`causa` los decide este servicio; orden: modificadas primero,
    luego por clave.
    """
    aplicados = Parametros(sim.parametros_aplicados)
    originales = _arbol(analisis.parametros_aplicados)
    hay_original = originales is not None

    filas, editables = [], set()
    for clave, meta, _ in _claves_editables(aplicados):
        editables.add(clave)
        original = originales.get(clave, _AUSENTE) if hay_original else _AUSENTE
        aplicado = aplicados.get(clave, _AUSENTE)
        filas.append(_fila(clave, meta, sim, hay_original,
                           None if original is _AUSENTE else original,
                           None if aplicado is _AUSENTE else aplicado))

    if hay_original:
        hojas_original = _hojas(analisis.parametros_aplicados)
        hojas_aplicadas = _hojas(sim.parametros_aplicados)
        for ruta in sorted(hojas_original.keys() | hojas_aplicadas.keys()):
            if ruta == _HOJA_VERSION or _cubierta(ruta, editables):
                continue
            original = hojas_original.get(ruta, _AUSENTE)
            aplicado = hojas_aplicadas.get(ruta, _AUSENTE)
            if original is not _AUSENTE and aplicado is not _AUSENTE and original == aplicado:
                continue
            filas.append(_fila(ruta, None, sim, True,
                               None if original is _AUSENTE else original,
                               None if aplicado is _AUSENTE else aplicado))

    filas.sort(key=lambda f: (not f["modificado"], f["clave"]))

    return {
        "analisis_id": analisis.id,
        "simulacion": {
            "id": sim.id, "estado": sim.estado,
            "creado_en": sim.creado_en.isoformat() if sim.creado_en else None,
            "fecha_validacion": (sim.fecha_validacion.isoformat()
                                 if sim.fecha_validacion else None),
            "version_parametros_base": sim.version_parametros_base,
            "version_reglas": sim.version_reglas,
            # Mismo criterio que el listado (`_resumen_simulacion`): el puntero
            # tal cual, para que ambos endpoints no puedan contradecirse.
            "es_configuracion_actual": sim.id == analisis.simulacion_validada_id,
        },
        "original": {
            "creado_en": analisis.creado_en.isoformat() if analisis.creado_en else None,
            "version_parametros": analisis.version_parametros,
            "version_reglas": analisis.version_reglas,
            "parametros_disponibles": hay_original,
        },
        "parametros": filas,
        "resultado": {"original": _resumen_resultado(analisis.resultado),
                      "simulacion": _resumen_resultado(sim.resultado)},
    }

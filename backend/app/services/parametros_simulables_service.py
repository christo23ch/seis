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


def obtener_parametros_simulables(db: Session, analisis: models.Analisis) -> dict:
    """Catálogo simulable de `analisis`. El llamador ya ha comprobado que el
    análisis pertenece a su organización (`_analisis_propio`)."""
    vigentes, _, _ = conocimiento_service.cargar_conocimiento(db)
    originales = (Parametros(analisis.parametros_aplicados)
                  if analisis.parametros_aplicados is not None else None)

    editables = [_editable(p.clave, p, None, vigentes, originales)
                 for p in catalogo.obtener_parametros_editables()]
    editables += [_editable(r.clave, r.plantilla, _plantilla(r, analisis), vigentes, originales)
                  for r in catalogo.resolver_plantillas(vigentes)]
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

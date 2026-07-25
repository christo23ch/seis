"""Fase 12 — Scoring exprés de subastas captadas (0–100).

LÍMITES (documentados a propósito, mostrados en la UI como «orientativa»):
- Es una puntuación PRE-ANÁLISIS con los datos brutos de la captación: no conoce
  cargas registrales, situación posesoria, comparables ni financiación.
- NO sustituye al motor M01–M14 ni a los vetos no compensatorios (P6): una subasta
  con score alto puede ser ROJO tras el análisis completo, y viceversa.
- Sirve solo para priorizar qué subastas captadas merecen un análisis completo
  y para filtrar alertas (criterio score_min).

Coherencia con los principios del sistema:
- P1 (determinismo): mismo input + misma versión de parámetros ⇒ mismo score.
- P4 (la ausencia penaliza): toda dimensión sin dato puntúa 0, nunca el valor optimista.

Este módulo es NUEVO y vive fuera de `modules/` y del DAG: no altera el caso dorado §19.
Los pesos son parámetros T3 (sección `scoring_expres` de defaults.yaml), editables
sin desplegar código.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.engine.params.store import Parametros

# Fallbacks si la sección T3 no existiera (nunca romper la ingesta).
_PESOS_DEFECTO = {"descuento": 40, "fuente": 15, "desiertas": 15,
                  "informacion": 20, "plazo": 10}
_FUENTES_DEFECTO = {"judicial_boe": 70, "aeat": 65, "tgss": 60, "concursal": 75,
                    "banco": 45, "notarial": 60, "privada": 35, "default": 50}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def puntuar_subasta(datos: dict[str, Any], params: Parametros, ahora: datetime) -> dict[str, Any]:
    """Puntúa una subasta captada. Determinista; datos ausentes puntúan 0 (P4).

    `ahora` es OBLIGATORIO y explícito (cierre Fase 12, P0.3): la función ya no
    lee el reloj de pared internamente. El llamador lo calcula UNA vez en el
    momento de la captación y lo persiste junto al resultado (`score_calculado_en`
    en `datos_brutos`), de modo que reevaluar el mismo snapshot con el mismo
    `ahora` produce siempre el mismo score — P1 (mismo input ⇒ mismo output),
    no solo "en el mismo instante".

    `datos` esperado (todo opcional salvo valor_subasta):
      valor_subasta, valor_referencia (tasación/mercado si la fuente lo da),
      fuente_codigo, subastas_desiertas_previas, fecha_cierre (ISO o datetime),
      y flags de información disponible: tiene_descripcion, tiene_superficie,
      tiene_ubicacion, tiene_fotos.
    """
    pesos = params.get("scoring_expres.pesos", _PESOS_DEFECTO)
    fuentes = params.get("scoring_expres.fuentes", _FUENTES_DEFECTO)
    desglose: dict[str, float] = {}

    # 1) Descuento aparente sobre el valor de referencia (0 si no hay referencia — P4).
    vs = float(datos.get("valor_subasta") or 0)
    vref = float(datos.get("valor_referencia") or 0)
    if vs > 0 and vref > 0 and vref >= vs:
        descuento = (vref - vs) / vref                     # 0..1
        desglose["descuento"] = _clamp(descuento / 0.5 * 100)   # 50 % descuento ⇒ 100
    else:
        desglose["descuento"] = 0.0

    # 2) Atractivo típico de la fuente (ratios de adjudicación históricos, §11.1).
    fuente = str(datos.get("fuente_codigo") or "")
    desglose["fuente"] = float(fuentes.get(fuente, fuentes.get("default", 50)))

    # 3) Subastas desiertas previas: menos competencia esperada.
    desiertas = int(datos.get("subastas_desiertas_previas") or 0)
    desglose["desiertas"] = _clamp(desiertas * 40.0)       # 1 desierta ⇒ 40, ≥3 ⇒ 100

    # 4) Información disponible (P4: cada dato ausente resta).
    flags = ("tiene_descripcion", "tiene_superficie", "tiene_ubicacion", "tiene_fotos")
    presentes = sum(1 for f in flags if datos.get(f))
    desglose["informacion"] = presentes / len(flags) * 100

    # 5) Plazo hasta el cierre: con <48 h no hay due diligence posible (cf. VETO-INF-01).
    horas = _horas_hasta_cierre(datos.get("fecha_cierre"), ahora)
    if horas is None:
        desglose["plazo"] = 0.0                            # sin fecha ⇒ 0 (P4)
    elif horas < 48:
        desglose["plazo"] = 0.0
    elif horas >= 240:
        desglose["plazo"] = 100.0
    else:
        desglose["plazo"] = (horas - 48) / (240 - 48) * 100

    total_pesos = sum(pesos.values()) or 1
    score = round(sum(desglose[k] * pesos.get(k, 0) for k in desglose) / total_pesos)
    return {"score": int(_clamp(score)), "desglose": {k: round(v, 1) for k, v in desglose.items()},
            "version_parametros": params.version}


def _horas_hasta_cierre(fecha_cierre: Any, ahora: datetime) -> float | None:
    if not fecha_cierre:
        return None
    if isinstance(fecha_cierre, str):
        try:
            fecha_cierre = datetime.fromisoformat(fecha_cierre)
        except ValueError:
            return None
    if fecha_cierre.tzinfo is None:
        fecha_cierre = fecha_cierre.replace(tzinfo=timezone.utc)
    return (fecha_cierre - ahora).total_seconds() / 3600

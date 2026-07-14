"""M01 — Captura y normalización (§6.1).

En F1 la entrada llega ya estructurada (asistente); este módulo la normaliza,
deriva hechos primarios y aplica el triaje E0 (§8.7.1) documental mínimo.
Los adaptadores de fuentes externas y la extracción LLM se acoplan aquí en F2 (P8).
"""
from __future__ import annotations

from app.engine.contracts import AnalisisInput


def ejecutar(inp: AnalisisInput, params, hechos: dict) -> None:
    a, s = inp.activo, inp.subasta

    hechos.update({
        "activo.tipologia": a.tipologia,
        "activo.superficie_m2": a.superficie_m2,
        "activo.estado_conservacion": a.estado_conservacion,
        "activo.vpo": a.vpo,
        "activo.es_vivienda_habitual": a.es_vivienda_habitual,
        "subasta.fuente": s.fuente,
        "subasta.valor_subasta": s.valor_subasta,
        "subasta.deposito_pct": s.deposito_pct,
        "subasta.desiertas_previas": s.subastas_desiertas_previas,
        "subasta.horas_hasta_cierre": s.horas_hasta_cierre if s.horas_hasta_cierre is not None else 9999,
        "ocupacion.estado": inp.ocupacion.estado,
        "perfil.codigo": inp.perfil,
        "financiacion.tipo": inp.financiacion.tipo,
        "financiacion.preaprobada": inp.financiacion.preaprobada,
        "urbanistico.uso_compatible": inp.urbanistico.uso_compatible,
        "urbanistico.fuera_ordenacion": inp.urbanistico.fuera_ordenacion,
        "urbanistico.orden_demolicion": inp.urbanistico.orden_demolicion,
        "urbanistico.suelo_protegido": inp.urbanistico.suelo_protegido,
    })

    # Hechos de cargas (M07 los cuantifica; aquí solo presencia estructural)
    subsistentes = [c for c in inp.cargas if c.es_anterior and not c.se_purga]
    hechos["carga_anterior_indeterminada"] = any(c.importe is None for c in subsistentes)
    hechos["cargas_sin_verificar"] = any(not c.verificada for c in subsistentes)
    hechos["prohibicion_disponer"] = any(c.prohibicion_disponer for c in inp.cargas)
    hechos["condicion_resolutoria"] = any(c.condicion_resolutoria for c in inp.cargas)

    hechos["documentos.cert_comunidad"] = inp.documentos.cert_comunidad

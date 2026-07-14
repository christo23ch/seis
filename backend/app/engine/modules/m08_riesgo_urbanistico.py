"""M08 — Riesgo urbanístico y técnico (§7.3)."""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, ReformaResultado, RiesgoOut
from app.engine.modules.m07_riesgo_juridico import _mk


def ejecutar(inp: AnalisisInput, params, hechos: dict, reforma: ReformaResultado) -> list[RiesgoOut]:
    u = inp.urbanistico
    riesgos: list[RiesgoOut] = []

    # ── Dimensión 4: urbanístico ─────────────────────────────────────────
    p, i, cond, ev, mit = 2, 2, [], [], True
    if u.fuera_ordenacion:
        p, i = max(p, 3), max(i, 3 if reforma.nivel in ("ninguna", "refresco", "ligera") else 4)
        ev.append("fuera_ordenacion")
        cond.append("Confirmar con el ayuntamiento el alcance de obras autorizables en fuera de ordenación")
    if u.cargas_urbanizacion > 0:
        i = max(i, 3)
        ev.append(f"cargas_urbanizacion={u.cargas_urbanizacion:,.0f}€")
        cond.append("Incorporar cargas de urbanización pendientes al plan de costes")
    if u.zona_inundable_alta:
        p, i = max(p, 3), max(i, 3)
        ev.append("zona_inundable_alta")
        cond.append("Verificar asegurabilidad y limitaciones de uso en zona inundable (SNCZI)")
    if u.servidumbres_incompatibles:
        p, i, mit = 4, 4, False
        ev.append("servidumbres_incompatibles")
    extra = params.get(f"perfiles.{inp.perfil}.riesgo_extra", {}) or {}
    if "urbanistico" in extra:
        p += int(extra["urbanistico"].get("p", 0))
        cond.append("Estrategia con dependencia urbanística: verificar norma zonal por escrito antes de pujar")
    riesgos.append(_mk("urbanistico", p, i, params, mitigable=mit, condiciones=cond, evidencias=ev))

    # ── Dimensión 5: técnico (evidencia de M05) ──────────────────────────
    tabla = {"ninguna": (1, 2), "refresco": (1, 2), "ligera": (2, 2),
             "media": (2, 3), "integral": (3, 3), "estructural": (4, 4)}
    pt, it = tabla[reforma.nivel]
    ev_t = [f"nivel_reforma={reforma.nivel}"]
    cond_t = []
    if not inp.reforma.visita_interior and reforma.nivel not in ("ninguna", "refresco"):
        pt += 1
        ev_t.append("sin_visita_interior")
        cond_t.append("Visita interior (o con cerrajero tras adjudicación) para cerrar presupuesto P50")
    if (inp.activo.anio_construccion or 2000) < 1960 and not inp.documentos.ite_cee:
        pt += 1
        ev_t.append("anterior_1960_sin_ITE")
        cond_t.append("Consultar ITE/IEE del edificio y derramas estructurales aprobadas")
    riesgos.append(_mk("tecnico", pt, it, params, condiciones=cond_t, evidencias=ev_t))

    for r in riesgos:
        hechos[f"riesgo.{r.dimension}.score"] = r.score
    return riesgos

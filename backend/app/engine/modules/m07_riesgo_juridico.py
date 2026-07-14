"""M07 — Riesgo jurídico: dimensiones jurídico, documental y ocupación (§7.2)."""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, ICIResultado, RiesgoOut


def _nivel(score: int, params) -> str:
    n = params.seccion("riesgos.niveles")
    if score <= n["bajo"]:
        return "bajo"
    if score <= n["medio"]:
        return "medio"
    if score <= n["alto"]:
        return "alto"
    return "critico"


def _mk(dim, p, i, params, mitigable=True, condiciones=None, evidencias=None) -> RiesgoOut:
    p, i = max(1, min(5, p)), max(1, min(5, i))
    return RiesgoOut(dimension=dim, probabilidad=p, impacto=i, score=p * i,
                     nivel=_nivel(p * i, params), mitigable=mitigable,
                     condiciones=condiciones or [], evidencias=evidencias or [])


def ejecutar(inp: AnalisisInput, params, hechos: dict, ici: ICIResultado,
             vs_referencia: float) -> list[RiesgoOut]:
    riesgos: list[RiesgoOut] = []

    # ── Dimensión 1: jurídico ────────────────────────────────────────────
    p, i = 2, 3                                  # proceso de ejecución inherente
    cond, ev = [], ["procedimiento_subasta"]
    subsist = [c for c in inp.cargas if c.es_anterior and not c.se_purga]
    total = sum(c.importe or 0.0 for c in subsist)
    hechos["carga_subsistente_total"] = total
    if total > 0:
        ev.append(f"cargas_subsistentes={total:,.0f}€")
        i = max(i, 4 if total > 0.15 * vs_referencia else 3)
        cond.append("Cuantificar y consignar en costes todas las cargas anteriores subsistentes")
    if any(not c.verificada for c in subsist):
        p += 1
        cond.append("Verificar cargas con nota simple ≤ 5 días antes del cierre")
    if inp.activo.vpo:
        p += 1
        ev.append("vpo")
        cond.append("Verificar régimen VPO: precio máximo legal y posibilidad de descalificación")
    riesgos.append(_mk("juridico", p, i, params, condiciones=cond, evidencias=ev))

    # ── Dimensión 2: documental (derivada del ICI, §7.2) ────────────────
    tramos = [(80, 1, 2), (60, 2, 3), (40, 3, 3), (25, 3, 4), (0, 4, 5)]
    pd, idd = next((pp, ii) for m, pp, ii in tramos if ici.ici >= m)
    riesgos.append(_mk("documental", pd, idd, params,
                       condiciones=[f"Subsanar: {c}" for c in ici.carencias[:4]],
                       evidencias=[f"ICI={ici.ici}"]))

    # ── Dimensión 3: ocupación (árbol §8.7.2 / tabla §7.2) ──────────────
    tabla = params.seccion("ocupacion")
    estado = inp.ocupacion.estado
    clave = tabla["desconocida"]["usa"] if estado == "desconocida" else estado
    fila = tabla[clave]
    p3, i3 = int(fila["p"]), int(fila["i"])
    mit, cond3, ev3 = True, [], [f"estado={estado}"]
    perfil_tipo = params.get(f"perfiles.{inp.perfil}.tipo", "venta")

    if estado == "desconocida":
        cond3.append("Verificación posesoria in situ obligatoria antes de pujar (se asume precario, P5)")
    if estado == "arrendado_anterior" and perfil_tipo == "venta":
        extra = params.seccion("ocupacion.flip_arrendado_anterior")
        p3, i3 = int(extra["p"]), int(extra["i"])
        cond3.append("Arrendatario oponible: la venta exige esperar fin de contrato o negociar salida")
    if estado == "arrendado_anterior" and perfil_tipo == "rentista":
        renta_mercado = (inp.rentista.renta_mensual_estimada if inp.rentista else 0) or 1
        umbral = float(params.get("ocupacion.rentista_arrendado_umbral_renta"))
        if (inp.ocupacion.renta_mensual or 0) < umbral * renta_mercado:
            p3, i3 = 3, 3
            cond3.append("Renta actual por debajo de mercado: valorar actualización legal o salida pactada")
    if estado == "renta_antigua":
        mit = perfil_tipo == "rentista"
        cond3.append("Renta antigua: solo viable capitalizando la renta real (perfil rentista)")

    riesgos.append(_mk("ocupacion", p3, i3, params, mitigable=mit,
                       condiciones=cond3, evidencias=ev3))

    for r in riesgos:
        hechos[f"riesgo.{r.dimension}.score"] = r.score
    return riesgos

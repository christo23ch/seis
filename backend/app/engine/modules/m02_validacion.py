"""M02 — Validación documental → ICI (§6.2). 100% determinista."""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, ICIResultado


def _factor_frescura_nota(dias: int | None, tabla: list[dict]) -> float:
    if dias is None:
        return 1.0                       # marcada presente sin fecha ⇒ se acepta (F1)
    for tramo in tabla:
        if dias <= tramo["max_dias"]:
            return float(tramo["factor"])
    return 0.3


def ejecutar(inp: AnalisisInput, params, hechos: dict) -> ICIResultado:
    pesos: dict = params.seccion("ici.pesos")
    d = inp.documentos
    desglose: dict[str, float] = {}
    carencias: list[str] = []

    presencia = {
        "nota_simple": d.nota_simple,
        "cert_cargas": d.cert_cargas,
        "posesion_verificada": d.posesion_verificada,
        "avaluo": d.avaluo,
        "fotos_interior_o_visita": d.fotos_interior_o_visita,
        "fotos_exterior": d.fotos_exterior,
        "cert_comunidad": d.cert_comunidad,
        "recibo_ibi": d.recibo_ibi,
        "ite_cee": d.ite_cee,
        "catastro_conciliado": d.catastro_conciliado,
    }
    for item, peso in pesos.items():
        if item == "comparables_ok":
            n_min = params.get("valoracion.n_min_comparables")
            cv_max = params.get("valoracion.cv_max_ok")
            ok = len(inp.comparables) >= n_min and hechos.get("valoracion.cv", 1.0) <= cv_max
            desglose[item] = float(peso) if ok else 0.0
            if not ok:
                carencias.append(f"Comparables insuficientes (n≥{n_min}, CV≤{int(cv_max*100)}%)")
            continue
        presente = presencia.get(item, False)
        factor = 1.0
        if item == "nota_simple" and presente:
            factor = _factor_frescura_nota(d.nota_simple_dias, params.get("ici.frescura_nota_simple"))
        desglose[item] = float(peso) * factor if presente else 0.0
        if not presente:
            carencias.append(item)

    penal_tabla: dict = params.seccion("ici.penalizaciones")
    penalizaciones = [f"{c} (−{penal_tabla.get(c, penal_tabla['otra'])})" for c in d.inconsistencias]
    total_penal = sum(penal_tabla.get(c, penal_tabla["otra"]) for c in d.inconsistencias)

    ici = max(0, min(100, round(sum(desglose.values()) - total_penal)))

    # Efectos en cascada (§6.2): tramos min→(δ_v, contingencia, techo)
    efecto = next(e for e in params.get("ici.efectos") if ici >= e["min"])
    res = ICIResultado(
        ici=ici, desglose=desglose, carencias=carencias, penalizaciones=penalizaciones,
        efecto_delta_v_pp=float(efecto["delta_pp"]),
        efecto_contingencia_pp=float(efecto["conting_pp"]),
        techo_semaforo=efecto["techo"],
    )
    hechos["ici"] = ici
    hechos["ici.techo"] = efecto["techo"]
    return res

"""M03 — Valoración inmobiliaria (§6.3).

AVM ligero y explicable: mediana ponderada de comparables normalizados a estado
'reformado', con ajustes de origen (oferta→cierre) y temporales asimétricos (P5:
solo se ajusta a la baja si el mercado cae; el mercado alcista no infla testigos).
"""
from __future__ import annotations

import math

from app.engine.contracts import AnalisisInput, ComparableValoradoOut, ValoracionResultado


def _mediana_ponderada(valores: list[float], pesos: list[float]) -> float:
    pares = sorted(zip(valores, pesos))
    total = sum(pesos)
    acum = 0.0
    for v, w in pares:
        acum += w
        if acum >= total / 2:
            return v
    return pares[-1][0]


def _percentil(valores: list[float], q: float) -> float:
    if not valores:
        return 0.0
    s = sorted(valores)
    idx = (len(s) - 1) * q
    lo, hi = int(math.floor(idx)), int(math.ceil(idx))
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def ejecutar(inp: AnalisisInput, params, hechos: dict) -> ValoracionResultado:
    k_estado: dict = params.seccion("valoracion.k_estado")
    desc_oferta = float(params.get("valoracion.descuento_oferta_portal"))
    tendencia = inp.zona.macro.tendencia_5a_pct / 100.0
    m2 = inp.activo.superficie_m2
    hechos_out: list[str] = []

    normalizados: list[float] = []
    pesos: list[float] = []
    detalle_comparables: list[ComparableValoradoOut] = []
    for c in inp.comparables:
        precio = c.precio_m2
        if c.origen == "portal_oferta":
            precio *= (1 - desc_oferta)
        # Ajuste temporal asimétrico (P5): solo a la baja
        if tendencia < 0 and c.meses_antiguedad > 0:
            precio *= (1 + tendencia) ** (c.meses_antiguedad / 12.0)
        normalizado = precio / k_estado[c.estado]
        peso = 1.0 / (1.0 + c.meses_antiguedad / 6.0)               # frescura
        normalizados.append(normalizado)
        pesos.append(peso)
        # Fase 4: snapshot de los intermedios de este comparable — no altera
        # `normalizados`/`pesos`, que siguen siendo lo único que usa el cálculo.
        detalle_comparables.append(ComparableValoradoOut(
            precio_ajustado_m2=round(precio, 2), normalizado_m2=round(normalizado, 2),
            peso=round(peso, 4)))

    n = len(normalizados)
    if n == 0:
        # Sin comparables: se degrada todo (P4). VM provisional = VT con máxima desconfianza.
        vt = inp.subasta.valor_subasta
        hechos["valoracion.cv"] = 1.0
        hechos["vm"] = vt
        hechos["vs"] = vt
        return ValoracionResultado(vm=vt, vm_rango=(vt * 0.7, vt * 1.3), vs=vt,
                                   vs_rango=(vt * 0.7, vt * 1.3), vs_m2=vt / m2,
                                   metodo="sin_comparables", n_comparables=0,
                                   dispersion_cv=1.0, confianza=0.0,
                                   hechos=["sin_comparables"], detalle_comparables=[])

    vs_m2 = _mediana_ponderada(normalizados, pesos)
    media = sum(normalizados) / n
    var = sum((x - media) ** 2 for x in normalizados) / n
    cv = (math.sqrt(var) / media) if media > 0 else 1.0

    vs = vs_m2 * m2                                                # salida en estado reformado
    k_estado_activo = k_estado[inp.activo.estado_conservacion]     # Fase 4: nombrado, mismo valor
    vm = vs_m2 * k_estado_activo * m2                               # estado actual
    p25 = _percentil(normalizados, 0.25) * m2
    p75 = _percentil(normalizados, 0.75) * m2

    # Fase 4: snapshots para trazabilidad, poblados solo si el override aplica —
    # el cálculo de vs/vs_cap no cambia, solo se conserva lo que antes se perdía.
    vs_antes_de_capitalizacion: float | None = None
    vs_capitalizacion: float | None = None

    # Rentista: contraste por capitalización (§6.3.4) — prudente: el menor de ambos
    perfil_tipo = params.get(f"perfiles.{inp.perfil}.tipo", "venta")
    if perfil_tipo == "rentista" and inp.rentista and inp.rentista.renta_mensual_estimada > 0:
        r = inp.rentista
        rna_bruta = r.renta_mensual_estimada * 12 * (1 - r.vacancia_pct / 100)
        vs_cap = rna_bruta / max(inp.zona.macro.y_zona_pct / 100.0, 0.01)
        if vs_cap < vs:
            vs_antes_de_capitalizacion = round(vs, 2)
            vs_capitalizacion = round(vs_cap, 2)
            vs = vs_cap
            hechos_out.append("vs_por_capitalizacion")

    # Contraste de sanidad de la tasación (§6.3.6)
    banda = params.seccion("valoracion.sanidad_vt_vm")
    ratio = inp.subasta.valor_subasta / vm if vm > 0 else 99
    if not (banda["min"] <= ratio <= banda["max"]):
        hechos_out.append("tasacion_anomala")
        hechos["tasacion_anomala"] = True

    confianza = max(0.0, min(1.0, 0.4 + 0.06 * min(n, 8) - 1.2 * cv))

    hechos["valoracion.cv"] = cv
    hechos["valoracion.n"] = n
    hechos["vm"] = vm
    hechos["vs"] = vs
    hechos["vs_m2"] = vs_m2

    return ValoracionResultado(
        vm=round(vm, 2), vm_rango=(round(p25 * k_estado_activo, 2),
                                   round(p75 * k_estado_activo, 2)),
        vs=round(vs, 2), vs_rango=(round(p25, 2), round(p75, 2)), vs_m2=round(vs_m2, 2),
        metodo="comparables_ajustados", n_comparables=n, dispersion_cv=round(cv, 4),
        confianza=round(confianza, 3), hechos=hechos_out,
        detalle_comparables=detalle_comparables, k_estado_activo=round(k_estado_activo, 2),
        ratio_sanidad=round(ratio, 4), vs_antes_de_capitalizacion=vs_antes_de_capitalizacion,
        vs_capitalizacion=vs_capitalizacion,
    )

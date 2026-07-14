"""M05 — Estimación de reforma (§6.5). Paramétrica por baremos €/m² versionados."""
from __future__ import annotations

from app.engine.contracts import AnalisisInput, ReformaResultado


def ejecutar(inp: AnalisisInput, params, hechos: dict) -> ReformaResultado:
    r = inp.reforma
    nivel_estado: dict = params.seccion("reforma.nivel_por_estado")
    nivel_perfil = params.get(f"perfiles.{inp.perfil}.nivel_reforma_defecto", "null")

    nivel = r.nivel_override or (nivel_perfil if nivel_perfil not in (None, "null") else None) \
        or nivel_estado[inp.activo.estado_conservacion]

    coste_m2 = r.coste_m2_override if r.coste_m2_override is not None \
        else float(params.get(f"reforma.baremos_m2.{nivel}"))
    obra_p50 = coste_m2 * inp.activo.superficie_m2 * r.k_provincia + r.partidas_extra

    clave_visita = "con_visita" if r.visita_interior else "sin_visita"
    spread = float(params.get(f"reforma.spread_p80.{clave_visita}.{nivel}"))
    obra_p80 = obra_p50 * (1 + spread)

    mayor = nivel in params.get("reforma.niveles_obra_mayor")
    pct_tec = float(params.get(f"reforma.pct_tecnico_licencia.{'mayor' if mayor else 'menor'}"))
    tec_p50, tec_p80 = obra_p50 * pct_tec, obra_p80 * pct_tec

    plazo = float(params.get(f"reforma.plazo_obra_meses.{nivel}"))

    hechos.update({"reforma.nivel": nivel, "reforma.sin_visita": not r.visita_interior,
                   "reforma.obra_mayor": mayor})

    return ReformaResultado(
        nivel=nivel, obra_p50=round(obra_p50, 2), obra_p80=round(obra_p80, 2),
        tecnicos_licencia_p50=round(tec_p50, 2), tecnicos_licencia_p80=round(tec_p80, 2),
        total_p50=round(obra_p50 + tec_p50, 2), total_p80=round(obra_p80 + tec_p80, 2),
        plazo_obra_meses=plazo,
        partidas={"obra": round(obra_p50, 2), "tecnicos_licencia": round(tec_p50, 2),
                  "extras_conocidos": round(r.partidas_extra, 2)},
    )

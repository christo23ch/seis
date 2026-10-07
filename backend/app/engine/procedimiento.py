"""Fase 5J-1 — datos del procedimiento de subasta (diseño A, ADR-0022).

Calcula, con los parámetros T3 de `procedimiento.regimenes`, lo que la norma exige
para pujar en el procedimiento de la subasta: régimen aplicable, depósito y capital
para pujar, plazo de pago, meses de inmovilización, puja mínima aprobable sin
depender de la autoridad, puja de aprobación segura y suelo absoluto.

Es INFORMATIVO por construcción: vive fuera de `modules/` y del DAG, no escribe en
la pizarra de hechos y ningún módulo M01-M14 ni regla T2 lee lo que devuelve. La
escalera, el RVC, el semáforo y la rentabilidad no cambian
(`tests/test_invariante_5h1.py`).

Datos ausentes (P4): un valor `null` del parámetro no se rellena; el importe que
depende de él queda en `None` y se declara en `avisos`. Dos supuestos prudentes,
decididos por el responsable y declarados siempre:
  · régimen judicial «No sé» ⇒ el desfavorable (LO 1/2025: depósito 20 %, pago en
    20 días, y sus umbrales, que nunca son menores que los de 2015);
  · vivienda habitual «No consta» en una vivienda ⇒ se aplica su regla (70 % y suelo
    del 60 %), como el «No consta» del estado de conservación (ADR-0020).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.contracts import DatoLegal, ProcedimientoResultado
from app.engine.formato import decimal, eur, pct

if TYPE_CHECKING:
    from app.engine.contracts import AnalisisInput
    from app.engine.params.store import Parametros

REGIMEN_JUDICIAL = {"posterior": "judicial_lec_2025", "anterior": "judicial_lec_2015",
                    "no_se": "judicial_lec_2025"}
NOMBRE_VENTA_NO_REGLADA = "Venta no reglada (bancaria o privada)"
# Etiquetas del formulario (las sirve `/opciones`): el orden es el de la pregunta.
ETIQUETAS_PROCEDIMIENTO = {
    "judicial": "Judicial (juzgado, Portal de Subastas del BOE)",
    "aeat": "Agencia Tributaria (AEAT)",
    "tgss": "Seguridad Social (TGSS)",
    "notarial": "Subasta notarial",
    "extrajudicial": "Venta extrajudicial hipotecaria ante notario",
    "concursal": "Concursal",
    "no_aplica": "No aplica (venta bancaria o privada)",
}

# Orden y nombre legible de cada dato legal en el informe y la interfaz.
NOMBRES_DATO = {
    "deposito_pct": "Depósito para pujar",
    "deposito_minimo_eur": "Depósito mínimo",
    "plazo_pago_dias": "Plazo de pago del resto",
    "umbral_aprobacion_segura_pct": "Aprobación segura",
    "umbral_aprobacion_pct": "Aprobación sin depender de la autoridad",
    "umbral_cubre_deuda_pct": "Aprobación si la puja cubre la deuda",
    "vivienda_habitual_umbral_pct": "Vivienda habitual del ejecutado: umbral",
    "vivienda_habitual_suelo_pct": "Vivienda habitual del ejecutado: suelo absoluto",
    "puja_minima_pct": "Puja mínima admitida",
    "meses_inmovilizacion": "Meses de inmovilización del depósito",
    "forma_puja": "Forma de puja",
}
# Fase 5J-2b (ADR-0025): valor legible de `forma_puja`.
FORMAS_PUJA = {
    "secretas_sin_prorroga": "pujas secretas; cierre improrrogable",
    "visibles_con_prorroga": "pujas visibles; el cierre se prorroga tras la última puja",
    "visibles": "pujas visibles; la norma no fija la prórroga del cierre",
    "presencial": "presencial: sobre cerrado y pujas a viva voz",
}
UNIDAD_PLAZO = {"naturales": "días naturales", "habiles": "días hábiles"}


def _texto(regimen: dict, clave: str) -> str | None:
    """Valor textual de un dato del régimen; `None` si la clave no existe o vale null."""
    dato = regimen.get(clave)
    if not isinstance(dato, dict) or dato.get("valor") is None:
        return None
    return str(dato["valor"])


def _meses_si_no_consta(params: "Parametros") -> float:
    return float(params.get("procedimiento.meses_inmovilizacion_si_no_consta.valor"))


def _valor(regimen: dict, clave: str) -> float | None:
    """Valor de un dato del régimen; `None` si la clave no existe o vale null."""
    dato = regimen.get(clave)
    if not isinstance(dato, dict) or dato.get("valor") is None:
        return None
    return float(dato["valor"])


def _resolver_procedimiento(inp: "AnalisisInput", params: "Parametros") -> tuple[str, bool]:
    """(procedimiento, deducido). Sin dato en el alta se toma el de la fuente."""
    if inp.subasta.procedimiento is not None:
        return inp.subasta.procedimiento, False
    mapa = params.seccion("procedimiento.deducido_de_fuente")
    return mapa.get(inp.subasta.fuente) or "no_aplica", True


def _vivienda_habitual(inp: "AnalisisInput") -> str:
    """Respuesta efectiva a «¿vivienda habitual del ejecutado?». Las entradas
    anteriores a 5J-1 solo traen el booleano: `True` es «si»; `False` no distingue
    «no» de «no marcado», y por eso es «no_consta» (P4)."""
    declarada = inp.activo.vivienda_habitual_ejecutado
    if declarada is not None:
        return declarada
    return "si" if inp.activo.es_vivienda_habitual else "no_consta"


def _datos_legales(regimen: dict) -> list[DatoLegal]:
    def dato(clave: str, nombre: str) -> DatoLegal:
        forma = clave == "forma_puja"           # Fase 5J-2b: dato descriptivo, no una cifra
        texto = _texto(regimen, clave) if forma else None
        return DatoLegal(dato=nombre, valor=None if forma else _valor(regimen, clave),
                         articulo=str(regimen[clave]["articulo"]), estado=regimen[clave]["estado"],
                         nota=regimen[clave].get("nota"),
                         texto=FORMAS_PUJA.get(texto, texto) if forma else None)
    return [dato(clave, nombre) for clave, nombre in NOMBRES_DATO.items() if isinstance(regimen.get(clave), dict)]


def _puja_minima_aprobable(regimen: dict, vt: float, cantidad: float | None,
                           vivienda: bool) -> float | None:
    """Menor puja que la norma aprueba sin depender de la autoridad (LAJ, Mesa…).

    General: el umbral de aprobación, o menos si cubre la deuda y alcanza el umbral
    de ese supuesto (solo si se conoce la cantidad reclamada). Vivienda habitual del
    ejecutado: nunca menos que su umbral, salvo que cubra la deuda, y nunca por debajo
    de su suelo (LEC, art. 670, apdo. 3, último párrafo)."""
    aprob = _valor(regimen, "umbral_aprobacion_pct")
    if aprob is None:
        return None
    minimo = aprob * vt
    cubre = _valor(regimen, "umbral_cubre_deuda_pct")
    if cantidad is not None and cubre is not None:
        minimo = min(minimo, max(cubre * vt, cantidad))
    vh_umbral = _valor(regimen, "vivienda_habitual_umbral_pct")
    if vivienda and vh_umbral is not None:
        vh_minimo = vh_umbral * vt
        vh_suelo = _valor(regimen, "vivienda_habitual_suelo_pct")
        if cantidad is not None and vh_suelo is not None:
            vh_minimo = min(vh_minimo, max(vh_suelo * vt, cantidad))
        minimo = max(minimo, vh_minimo)
    return minimo


def _sin_procedimiento(inp: "AnalisisInput", deducido: bool, aviso_orientativo: str,
                       meses: float) -> ProcedimientoResultado:
    aviso = ("Venta no reglada (bancaria o privada): no hay depósito, plazos ni umbrales legales "
             "que calcular; rigen las condiciones que fije el vendedor.")
    aviso_meses = (f"Mientras no conste el plazo de pago del vendedor, el plazo de la operación suma "
                   f"{decimal(meses, 1)} meses de cierre y pago: estimación prudente, sin base legal.")
    return ProcedimientoResultado(
        procedimiento="no_aplica", procedimiento_deducido=deducido, regimen=None,
        regimen_nombre=NOMBRE_VENTA_NO_REGLADA, regimen_asumido=False,
        vivienda_habitual=_vivienda_habitual(inp), vivienda_habitual_asumida=False,
        valor_subasta=inp.subasta.valor_subasta, cantidad_reclamada=inp.subasta.cantidad_reclamada,
        deposito_pct=None, deposito_eur=None, deposito_declarado_pct=inp.subasta.deposito_pct,
        capital_para_pujar=None, plazo_pago_dias=None, plazo_pago_unidad=None,
        meses_inmovilizacion=None, umbral_aprobacion_pct=None, puja_minima_aprobable=None,
        umbral_aprobacion_segura_pct=None, puja_aprobacion_segura=None,
        suelo_absoluto_pct=None, suelo_absoluto=None, datos_legales=[],
        avisos=[aviso, aviso_meses], aviso_orientativo=aviso_orientativo,
        meses_inmovilizacion_aplicados=meses, meses_inmovilizacion_asumidos=True, forma_puja=None)


def calcular(inp: "AnalisisInput", params: "Parametros") -> ProcedimientoResultado:
    """Resultado informativo del procedimiento. Puro y determinista (P1)."""
    aviso_orientativo = (
        f"Cálculo orientativo con los parámetros legales de SEIS (versión {params.version}): no es "
        "asesoramiento jurídico. Confirme depósito, plazos y umbrales en el edicto y con un profesional "
        "antes de pujar. Los umbrales de aprobación no modifican la escalera de precios, el RVC ni el "
        "semáforo; el depósito exigido sí se usa en el plan de puja, y los meses de inmovilización, en "
        "el plazo de la operación.")
    procedimiento, deducido = _resolver_procedimiento(inp, params)
    if procedimiento == "no_aplica":
        return _sin_procedimiento(inp, deducido, aviso_orientativo, _meses_si_no_consta(params))

    regimenes = params.seccion("procedimiento.regimenes")
    clave = REGIMEN_JUDICIAL[inp.subasta.regimen_judicial] if procedimiento == "judicial" else procedimiento
    regimen = regimenes[clave]
    asumido = procedimiento == "judicial" and inp.subasta.regimen_judicial == "no_se"

    vt = inp.subasta.valor_subasta
    cantidad = inp.subasta.cantidad_reclamada
    vh = _vivienda_habitual(inp)
    tiene_regla_vh = _valor(regimen, "vivienda_habitual_umbral_pct") is not None
    # «No consta» solo se asume «sí» si el inmueble es una vivienda: un garaje o un
    # local no pueden ser la vivienda habitual del ejecutado.
    vh_asumida = vh == "no_consta" and tiene_regla_vh and inp.activo.tipologia == "vivienda"
    vivienda = tiene_regla_vh and (vh == "si" or vh_asumida)

    dep_pct = _valor(regimen, "deposito_pct")
    dep_min = _valor(regimen, "deposito_minimo_eur") or 0.0
    deposito = round(max(vt * dep_pct, dep_min), 2) if dep_pct is not None else None
    plazo = _valor(regimen, "plazo_pago_dias")
    unidad = regimen["plazo_pago_dias"].get("unidad") if plazo is not None else None

    minimo = _puja_minima_aprobable(regimen, vt, cantidad, vivienda)
    segura_pct = _valor(regimen, "umbral_aprobacion_segura_pct")
    vh_umbral = _valor(regimen, "vivienda_habitual_umbral_pct")
    if vivienda and segura_pct is not None and vh_umbral is not None:
        segura_pct = max(segura_pct, vh_umbral)
    suelo_pct = (_valor(regimen, "vivienda_habitual_suelo_pct") if vivienda
                 else _valor(regimen, "puja_minima_pct"))

    datos = _datos_legales(regimen)
    meses_norma = _valor(regimen, "meses_inmovilizacion")
    meses_aplicados = meses_norma if meses_norma is not None else _meses_si_no_consta(params)
    if asumido:
        # Fase 5J-2b: sin fecha de inicio, lo desfavorable en cada dato: el depósito del régimen
        # de la LO 1/2025 (20 %) y el plazo del régimen que lo tenga más largo.
        candidatos = [_valor(regimenes[c], "meses_inmovilizacion") for c in set(REGIMEN_JUDICIAL.values())]
        meses_aplicados = max((m for m in candidatos if m is not None), default=_meses_si_no_consta(params))
    resultado = ProcedimientoResultado(
        procedimiento=procedimiento, procedimiento_deducido=deducido, regimen=clave,
        regimen_nombre=str(regimen["nombre"]), regimen_asumido=asumido,
        vivienda_habitual=vh, vivienda_habitual_asumida=vh_asumida,
        valor_subasta=vt, cantidad_reclamada=cantidad,
        deposito_pct=dep_pct, deposito_eur=deposito, deposito_declarado_pct=inp.subasta.deposito_pct,
        capital_para_pujar=deposito,
        plazo_pago_dias=int(plazo) if plazo is not None else None, plazo_pago_unidad=unidad,
        meses_inmovilizacion=meses_norma,
        meses_inmovilizacion_aplicados=meses_aplicados,
        meses_inmovilizacion_asumidos=meses_norma is None,
        forma_puja=_texto(regimen, "forma_puja"),
        umbral_aprobacion_pct=round(minimo / vt, 4) if minimo is not None else None,
        puja_minima_aprobable=round(minimo, 2) if minimo is not None else None,
        umbral_aprobacion_segura_pct=segura_pct,
        puja_aprobacion_segura=round(segura_pct * vt, 2) if segura_pct is not None else None,
        suelo_absoluto_pct=suelo_pct,
        suelo_absoluto=round(suelo_pct * vt, 2) if suelo_pct is not None else None,
        datos_legales=datos, avisos=[], aviso_orientativo=aviso_orientativo)
    return resultado.model_copy(update={"avisos": _avisos(resultado, regimen, regimenes, inp)})


def _avisos(r: ProcedimientoResultado, regimen: dict, regimenes: dict, inp: "AnalisisInput") -> list[str]:
    avisos: list[str] = []
    if r.procedimiento_deducido:
        avisos.append(f"El alta no indica el procedimiento: se toma el de la fuente de la subasta, "
                      f"{r.regimen_nombre}. Confírmelo en el edicto.")
    if r.regimen_asumido and r.deposito_eur is not None and r.deposito_pct is not None:
        anterior = regimenes["judicial_lec_2015"]
        dep_ant, plazo_ant = _valor(anterior, "deposito_pct"), _valor(anterior, "plazo_pago_dias")
        avisos.append(
            f"No consta cuándo se inició el procedimiento judicial: se aplica el régimen desfavorable, el "
            f"de la LO 1/2025 (depósito del {pct(r.deposito_pct, 0)}, {eur(r.deposito_eur)}, y pago del resto "
            f"en {r.plazo_pago_dias} días naturales). Si se inició antes del 3-4-2025, el depósito es del "
            f"{pct(dep_ant or 0, 0)} y el plazo de {int(plazo_ant or 0)} días. Compruebe la fecha de "
            f"incoación en el edicto.")
    if r.vivienda_habitual_asumida:
        umbral = _valor(regimen, "vivienda_habitual_umbral_pct") or 0.0
        suelo = _valor(regimen, "vivienda_habitual_suelo_pct") or 0.0
        avisos.append(
            f"No consta si es la vivienda habitual del ejecutado: se asume que sí, por prudencia. El remate no se "
            f"aprueba por debajo del {pct(umbral, 0)} del valor de subasta ({eur(umbral * r.valor_subasta)}) "
            f"salvo que cubra lo debido al ejecutante, y nunca por debajo del {pct(suelo, 0)} "
            f"({eur(suelo * r.valor_subasta)}). Confírmelo en el edicto o en la escritura.")
    if r.deposito_pct is not None and abs(r.deposito_declarado_pct - r.deposito_pct) > 1e-9:
        avisos.append(
            f"El depósito indicado en el alta ({pct(r.deposito_declarado_pct, 0)}) no coincide con el que "
            f"fija la norma para este procedimiento ({pct(r.deposito_pct, 0)}). Prevalece el que figure en "
            f"el edicto.")
    if r.deposito_pct is None:
        avisos.append("No hay un depósito confirmado para este procedimiento: no se calcula el capital "
                      "necesario para pujar. Consulte el edicto.")
    if r.puja_minima_aprobable is None:
        avisos.append("No hay umbrales de aprobación confirmados para este procedimiento: no se calcula "
                      "la puja mínima aprobable ni la de aprobación segura.")
    aprob = regimen.get("umbral_aprobacion_pct")
    if isinstance(aprob, dict) and aprob.get("estricto") and r.puja_minima_aprobable is not None:
        avisos.append(f"La norma exige superar el {pct(float(aprob['valor']), 0)} del valor de subasta, no "
                      f"igualarlo: la puja debe ser mayor que la mínima aprobable indicada.")
    cubre = _valor(regimen, "umbral_cubre_deuda_pct")
    if cubre is not None and inp.subasta.cantidad_reclamada is None and r.puja_minima_aprobable is not None:
        desde = "sin porcentaje mínimo" if cubre == 0 else f"desde el {pct(cubre, 0)} del valor de subasta"
        avisos.append(f"Sin la cantidad reclamada no se puede aplicar la aprobación por cubrir la deuda "
                      f"({desde}): se toma el umbral general.")
    if r.meses_inmovilizacion_asumidos and r.meses_inmovilizacion_aplicados is not None:
        avisos.append(f"La norma no da un plazo de cierre y pago para este procedimiento: el plazo de la "
                      f"operación suma {decimal(r.meses_inmovilizacion_aplicados, 1)} meses, estimación "
                      f"prudente, sin base legal.")
    if r.regimen_asumido and r.meses_inmovilizacion_aplicados != r.meses_inmovilizacion:
        avisos.append(f"Por no constar la fecha de inicio, el plazo de la operación suma "
                      f"{decimal(r.meses_inmovilizacion_aplicados or 0.0, 1)} meses de cierre y pago, los del "
                      f"régimen judicial más largo (con la LO 1/2025 serían "
                      f"{decimal(r.meses_inmovilizacion or 0.0, 1)}).")
    sin_confirmar = [d.dato for d in r.datos_legales
                     if d.estado == "sin_confirmar" and (d.valor is not None or d.texto is not None)]
    if sin_confirmar:
        avisos.append(f"Datos sin confirmar en la norma: {', '.join(sin_confirmar).lower()}. No los use "
                      f"sin validarlos.")
    return avisos


def _texto_meses(r: ProcedimientoResultado) -> str:
    """Fase 5J-2b (ADR-0026): los meses que se suman al plazo de la operación y su origen."""
    m = r.meses_inmovilizacion_aplicados
    if m is None:                       # resultado anterior a la fase
        return "no consta" if r.meses_inmovilizacion is None else f"{decimal(r.meses_inmovilizacion, 1)} meses (plazo legal máximo)"
    if r.meses_inmovilizacion_asumidos:
        return f"{decimal(m, 1)} meses (estimación prudente, sin base legal)"
    if r.regimen_asumido and m != r.meses_inmovilizacion:
        return f"{decimal(m, 1)} meses (régimen judicial más largo: no consta la fecha de inicio)"
    return f"{decimal(m, 1)} meses (plazo legal máximo)"


def seccion_informe(r: ProcedimientoResultado) -> str:
    """Subapartado del informe (al final del §8). Empieza por una línea en blanco
    para que, sin él, el informe quede idéntico al anterior a la fase."""
    def importe(valor: float | None, porcentaje: float | None) -> str:
        if valor is None:
            return "no consta"
        return eur(valor) + (f" ({pct(porcentaje, 0)} del valor de subasta)" if porcentaje is not None else "")

    plazo = ("no consta" if r.plazo_pago_dias is None
             else f"{r.plazo_pago_dias} {UNIDAD_PLAZO.get(r.plazo_pago_unidad or '', 'días')}")
    meses = _texto_meses(r)
    regimen = (r.regimen_nombre or NOMBRE_VENTA_NO_REGLADA) + (" — supuesto: no consta la fecha de inicio"
                                                                if r.regimen_asumido else "")
    filas = [
        ("Procedimiento y régimen", regimen),
        ("Depósito exigido", importe(r.deposito_eur, r.deposito_pct)),
        ("Capital necesario para pujar", importe(r.capital_para_pujar, None)),
        ("Pago del resto del precio", plazo),
        ("Inmovilización estimada del depósito", meses),
        ("Puja mínima aprobable sin depender de la autoridad", importe(r.puja_minima_aprobable, r.umbral_aprobacion_pct)),
        ("Puja de aprobación segura", importe(r.puja_aprobacion_segura, r.umbral_aprobacion_segura_pct)),
        ("Suelo absoluto", importe(r.suelo_absoluto, r.suelo_absoluto_pct)),
    ]
    tabla = "\n".join(f"| {k} | {v} |" for k, v in filas)
    avisos = "\n".join(f"- {a}" for a in r.avisos) or "- (ninguno)"
    fuentes = "\n".join(f"- {d.dato}{f' ({d.texto})' if d.texto else ''}: {d.articulo} "
                        f"({'confirmado' if d.estado == 'confirmado' else 'sin confirmar'})"
                        for d in r.datos_legales) or "- (no aplica)"
    return (f"\n\n**Procedimiento y umbrales legales (orientativo)**\n\n"
            f"| Dato | Valor |\n|---|---|\n{tabla}\n\n"
            f"**Avisos del procedimiento:**\n{avisos}\n\n"
            f"**Base legal aplicada:**\n{fuentes}\n\n"
            f"_{r.aviso_orientativo}_")


def texto_deposito(r: ProcedimientoResultado) -> str:
    """Fase 5J-2b (ADR-0024): el depósito exigido, para el plan de puja y el informe."""
    if r.procedimiento == "no_aplica":
        return "según las condiciones del vendedor (venta no reglada)"
    if r.deposito_eur is None or r.deposito_pct is None:
        return "no consta en la norma para este procedimiento: confírmelo en el edicto"
    minimo = r.deposito_eur > round(r.deposito_pct * r.valor_subasta, 2)
    texto = (f"{eur(r.deposito_eur)} ({pct(r.deposito_pct, 0)} del valor de subasta"
             f"{', con el mínimo legal' if minimo else ''})")
    if r.regimen_asumido:
        texto += ("; supuesto desfavorable: no consta cuándo se inició el procedimiento judicial "
                  "(si fue antes del 3-4-2025, es menor)")
    return texto

"""Servicio de análisis: ejecuta el pipeline y persiste el snapshot inmutable (P1, T4)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app import models
from app.engine.contracts import AnalisisInput, AnalisisResult
from app.engine.params.store import Parametros
from app.engine.pipeline import ejecutar_analisis
from app.services import conocimiento_service


def _json(obj) -> dict:
    return json.loads(obj.model_dump_json())


def _ejecutar_con_contexto(db: Session, inp: AnalisisInput) -> tuple[AnalisisResult, Parametros]:
    """Resuelve el conocimiento vigente y ejecuta el motor — única implementación
    de este flujo dentro de este módulo (Fase 5F.1A: antes, `simular()` era el
    único punto que lo hacía; `crear_analisis()` necesitaba además el objeto
    `Parametros` ya resuelto —para congelar `Analisis.parametros_aplicados`—
    y no solo el `AnalisisResult`, así que esa parte común se extrae aquí en
    vez de resolver conocimiento una segunda vez).

    No persiste nada: sin `db.add`, sin `db.commit`. No modifica `inp` ni el
    `Parametros` devuelto — el motor (M01-M14, verificado por inspección) solo
    lee de él.
    """
    params, reglas, version_reglas = conocimiento_service.cargar_conocimiento(db)
    resultado = ejecutar_analisis(inp, params=params, reglas=reglas, version_reglas=version_reglas)
    return resultado, params


def simular(db: Session, inp: AnalisisInput) -> AnalisisResult:
    """Motor con el conocimiento vigente de BD, sin persistencia."""
    resultado, _ = _ejecutar_con_contexto(db, inp)
    return resultado


def crear_analisis(db: Session, inp: AnalisisInput, quien: str | None = None,
                   organizacion_id: str | None = None,
                   subasta_id: str | None = None) -> tuple[str, AnalisisResult] | None:
    """Ejecuta el motor y persiste el snapshot inmutable (P1, T4).

    `subasta_id` (Fase 1 — puente captación → análisis): si se pasa, el `Activo`
    cuelga de la `Subasta` YA CAPTADA con ese id (`app/services/ingesta_service.py`)
    en vez de crear una fila nueva. Antes de esta fase, cada análisis creaba su
    propia `Subasta` sin relación con las que la Fase 17-A ya persiste, de modo
    que una subasta captada no se podía analizar sin re-teclearla entera
    (`docs/ESTADO_ACTUAL.md`, «Frente abierto de PRODUCTO»).

    Fail-closed, mismo contrato que `obtener_analisis`: si `subasta_id` no
    existe, se devuelve `None` **antes** de tocar la sesión — no se crea ni
    Subasta, ni Activo, ni Analisis. El llamador traduce `None` a 404.

    Si `subasta_id` es `None` (el caso de siempre, alta manual), el
    comportamiento es IDÉNTICO al anterior: una `Subasta` nueva por análisis.
    """
    subasta: models.Subasta | None = None
    if subasta_id is not None:
        subasta = db.get(models.Subasta, subasta_id)
        if subasta is None:
            return None

    # Fase 5F.1: `params` es el mismo objeto que recibió ejecutar_analisis —
    # una única resolución de conocimiento, sin volver a llamar
    # cargar_conocimiento() después. `params.raw()` congela el árbol T3
    # efectivo exacto (incluida la fusión de PerfilInversion) tal y como lo
    # usó el motor, para reconstrucción histórica futura sin depender de
    # `version_parametros` (insuficiente, ver auditoría PRE-5D) ni de
    # volver a ejecutar M01-M14.
    resultado, params = _ejecutar_con_contexto(db, inp)

    if subasta is None:
        subasta = models.Subasta(
            fuente_codigo=inp.subasta.fuente,
            identificador_externo=inp.subasta.identificador_externo, url=inp.subasta.url,
            valor_subasta=inp.subasta.valor_subasta, puja_minima=inp.subasta.puja_minima,
            tramo=inp.subasta.tramo, deposito_pct=inp.subasta.deposito_pct,
            subastas_desiertas_previas=inp.subasta.subastas_desiertas_previas,
        )
        db.add(subasta)
        db.flush()

    activo = models.Activo(
        subasta_id=subasta.id, tipologia=inp.activo.tipologia,
        ref_catastral=inp.activo.ref_catastral, finca_registral=inp.activo.finca_registral,
        direccion=inp.activo.direccion, municipio=inp.activo.municipio,
        provincia=inp.activo.provincia, ccaa=inp.activo.ccaa,
        lat=inp.activo.lat, lng=inp.activo.lng, superficie_m2=inp.activo.superficie_m2,
        anio_construccion=inp.activo.anio_construccion,
        estado_conservacion=inp.activo.estado_conservacion,
        es_vivienda_habitual=inp.activo.es_vivienda_habitual, vpo=inp.activo.vpo,
        atributos=inp.activo.atributos,
    )
    db.add(activo)
    db.flush()
    for c in inp.cargas:
        db.add(models.Carga(activo_id=activo.id, tipo=c.tipo, importe=c.importe,
                            es_anterior=c.es_anterior, se_purga=c.se_purga, verificada=c.verificada))

    dec = resultado.decision
    analisis = models.Analisis(
        organizacion_id=organizacion_id,
        activo_id=activo.id, perfil_codigo=inp.perfil,
        version_reglas=dec.version_reglas, version_parametros=dec.version_parametros,
        entrada=_json(inp), hechos={}, resultado=_json(resultado),
        parametros_aplicados=params.raw(),
        ici=dec.ici, icu=dec.icu, ra=dec.ra, ico=dec.ico,
    )
    db.add(analisis)
    db.flush()

    for r in resultado.riesgos.dimensiones:
        db.add(models.RiesgoEvaluado(analisis_id=analisis.id, dimension=r.dimension,
                                     probabilidad=r.probabilidad, impacto=r.impacto,
                                     score=r.score, nivel=r.nivel, mitigable=r.mitigable,
                                     condiciones=r.condiciones, evidencias=r.evidencias))
    for e in resultado.rentabilidad.escenarios:
        db.add(models.Escenario(analisis_id=analisis.id, nombre=e.nombre,
                                probabilidad=e.probabilidad, vs=e.vs, plazo_meses=e.plazo_meses,
                                coste_total=e.coste_total, beneficio=e.beneficio, roi=e.roi))
    db.add(models.Decision(analisis_id=analisis.id, semaforo=dec.semaforo,
                           p_ideal=dec.precios.p_ideal, p_objetivo=dec.precios.p_objetivo,
                           p_max=dec.precios.p_max, p_limite=dec.precios.p_limite,
                           margen_seguridad=dec.margen_seguridad_valor,
                           p_adj_esperado=dec.p_adj_esperado, rvc=dec.rvc,
                           vetos=[v.model_dump() for v in dec.vetos], condiciones=dec.condiciones))
    for i, rd in enumerate(resultado.reglas_disparadas):
        db.add(models.ReglaDisparada(analisis_id=analisis.id, regla_codigo=rd.codigo,
                                     regla_version=rd.version, efecto=rd.efecto,
                                     evidencias=rd.evidencias, orden=i))
    # Fase 3: snapshot de los comparables exactos que M03 recibió — la lista
    # completa de `inp.comparables`, en su orden original, sin filtrar ni
    # deduplicar (M03 usa el 100 % de lo recibido; ver m03_valoracion.py). El
    # objeto `inp` original no se toca, solo se lee.
    comparables_usados: list[models.ComparableUsado] = []
    for i, c in enumerate(inp.comparables):
        cu = models.ComparableUsado(analisis_id=analisis.id, precio_m2=c.precio_m2,
                                    estado=c.estado, origen=c.origen,
                                    meses_antiguedad=c.meses_antiguedad,
                                    superficie_m2=c.superficie_m2, orden=i)
        db.add(cu)
        comparables_usados.append(cu)
    if comparables_usados:
        db.flush()   # asigna id a cada ComparableUsado antes de enlazar el detalle (Fase 4)

    # Fase 4: intermedios de M03 por comparable — 1:1 con cada ComparableUsado
    # recién creado, mismo orden. `resultado.valoracion.detalle_comparables`
    # es la lista que M03 ya construyó en su propio bucle (m03_valoracion.py);
    # aquí solo se persiste, no se recalcula nada.
    for cu, det in zip(comparables_usados, resultado.valoracion.detalle_comparables):
        db.add(models.ComparableValorado(analisis_id=analisis.id, comparable_usado_id=cu.id,
                                         precio_ajustado_m2=det.precio_ajustado_m2,
                                         normalizado_m2=det.normalizado_m2, peso=det.peso))

    # Fase 4: agregados de valoración sin columna propia hoy (factor de estado
    # aplicado, ratio de sanidad, VS desplazado por capitalización). Solo
    # existen si M03 llegó a valorar (no en el caso sin_comparables, donde
    # k_estado_activo es None — ver m03_valoracion.py).
    val = resultado.valoracion
    if val.k_estado_activo is not None:
        db.add(models.ValoracionAjustes(
            analisis_id=analisis.id, k_estado_activo=val.k_estado_activo,
            ratio_sanidad=val.ratio_sanidad,
            vs_antes_de_capitalizacion=val.vs_antes_de_capitalizacion,
            vs_capitalizacion=val.vs_capitalizacion))

    db.add(models.Auditoria(quien=quien, entidad="analisis", entidad_id=analisis.id,
                            accion="crear", delta={"semaforo": dec.semaforo, "ico": dec.ico}))
    db.commit()
    return analisis.id, resultado


def listar_analisis(db: Session, limit: int = 50, *,
                    organizacion_id: str | None) -> list[dict]:
    """Lista los análisis de UNA organización.

    `organizacion_id` es obligatorio y sin tenant no se devuelve nada: antes el
    filtro era *fail-open* (`if organizacion_id is not None`), de modo que un
    usuario sin organización — la columna es nullable — habría visto los análisis
    de todas. Ante la duda, no se devuelve nada.
    """
    if organizacion_id is None:
        return []
    q = (db.query(models.Analisis, models.Decision, models.Activo)
         .join(models.Decision, models.Decision.analisis_id == models.Analisis.id)
         .outerjoin(models.Activo, models.Activo.id == models.Analisis.activo_id))
    q = q.filter(models.Analisis.organizacion_id == organizacion_id)   # Fase 9: aislamiento
    filas = q.order_by(models.Analisis.creado_en.desc()).limit(limit).all()
    out = []
    for a, d, act in filas:
        out.append({
            "id": a.id, "creado_en": a.creado_en.isoformat() if a.creado_en else None,
            "perfil": a.perfil_codigo, "semaforo": d.semaforo, "ico": a.ico, "ra": a.ra,
            "ici": a.ici, "icu": a.icu,
            "p_objetivo": float(d.p_objetivo or 0), "p_max": float(d.p_max or 0), "rvc": float(d.rvc or 0),
            "tipologia": act.tipologia if act else None,
            "municipio": act.municipio if act else None,
            "superficie_m2": float(act.superficie_m2 or 0) if act else None,
            "lat": float(act.lat) if act and act.lat is not None else None,
            "lng": float(act.lng) if act and act.lng is not None else None,
            "direccion": act.direccion if act else None,
        })
    return out


def obtener_analisis(db: Session, analisis_id: str, *,
                     organizacion_id: str | None) -> models.Analisis | None:
    """Devuelve el análisis solo si pertenece a `organizacion_id`.

    Sin tenant no se devuelve nada (*fail-closed*): la ausencia de organización
    no puede ser una llave maestra. El llamador traduce el `None` a 404 —nunca
    403—, para no confirmar que el recurso existe.
    """
    if organizacion_id is None:
        return None
    a = db.get(models.Analisis, analisis_id)
    if a is None:
        return None
    if a.organizacion_id != organizacion_id:
        return None
    return a

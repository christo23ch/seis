"""Servicio de análisis: ejecuta el pipeline y persiste el snapshot inmutable (P1, T4)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app import models
from app.engine.contracts import AnalisisInput, AnalisisResult
from app.engine.pipeline import ejecutar_analisis
from app.services import conocimiento_service


def _json(obj) -> dict:
    return json.loads(obj.model_dump_json())


def simular(db: Session, inp: AnalisisInput) -> AnalisisResult:
    """Motor con el conocimiento vigente de BD, sin persistencia."""
    params, reglas, version_reglas = conocimiento_service.cargar_conocimiento(db)
    return ejecutar_analisis(inp, params=params, reglas=reglas, version_reglas=version_reglas)


def crear_analisis(db: Session, inp: AnalisisInput, quien: str | None = None,
                   organizacion_id: str | None = None) -> tuple[str, AnalisisResult]:
    resultado = simular(db, inp)

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

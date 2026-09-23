"""API REST v1 — análisis (protegido por JWT desde la Fase 2)."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app import models
from app.api.deps import ROLES_ESCRITURA, get_current_user, require_rol
from app.core.config import get_settings
from app.core.db import get_db
from app.engine.contracts import AnalisisInput
from app.services import (analisis_service, informe_service, pdf_service,
                          simulacion_service)

router = APIRouter(tags=["analisis"])


@router.get("/health")
def health() -> dict:
    """Sonda de LIVENESS. Debe seguir siendo trivial: O(1) y sin ninguna E/S.

    La plataforma de hosting la consulta cada pocos segundos y por réplica. Si
    tocara la base de datos o Redis, una dependencia lenta o caída bastaría para
    que la plataforma matase y reiniciase los procesos web sanos, convirtiendo
    una degradación parcial en una caída total del servicio.

    Quien necesite el estado real de los componentes —monitorización externa,
    balanceador— tiene `GET /health/listo` (readiness) y, autenticado como
    superadministrador, `GET /health/detalle`. Ambos en `app/api/salud.py`.
    NO añadir aquí comprobaciones de dependencias (Fase 11, Bloque A).
    """
    return {"status": "ok", "servicio": "seis-backend"}


@router.post("/analisis")
def crear_analisis(inp: AnalisisInput, subasta_id: str | None = None,
                   db: Session = Depends(get_db),
                   user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """`subasta_id` (query, opcional — Fase 1 del puente captación → análisis):
    reutiliza una Subasta ya captada en vez de crear una fila nueva. Sin él,
    comportamiento idéntico al alta manual de siempre."""
    creado = analisis_service.crear_analisis(
        db, inp, quien=user.email, organizacion_id=user.organizacion_id,
        subasta_id=subasta_id)
    if creado is None:
        raise HTTPException(404, "Subasta no encontrada")
    analisis_id, resultado = creado
    return {"id": analisis_id, "resultado": resultado.model_dump()}


@router.post("/analisis/simular")
def simular_analisis(inp: AnalisisInput, db: Session = Depends(get_db),
                     _u: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """Ejecuta el motor con el conocimiento vigente sin persistir (paso 11 del asistente)."""
    return analisis_service.simular(db, inp).model_dump()


@router.post("/analisis/async", status_code=202)
def crear_analisis_async(inp: AnalisisInput,
                         user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    from app.tasks.celery_app import analizar_task
    t = analizar_task.delay(json.loads(inp.model_dump_json()),
                            organizacion_id=user.organizacion_id, quien=user.email)
    if get_settings().celery_task_always_eager:               # tests / modo síncrono
        return {"tarea_id": t.id, "estado": t.status, "resultado": t.result}
    return {"tarea_id": t.id, "estado": "PENDING"}


@router.get("/tareas/{tarea_id}")
def estado_tarea(tarea_id: str, db: Session = Depends(get_db),
                 user: models.Usuario = Depends(get_current_user)) -> dict:
    """Estado de una tarea de análisis, aislado por organización.

    El estado en crudo no distingue una tarea ajena de una inexistente (Celery
    responde PENDING a cualquier UUID), así que no filtra nada. Lo que sí filtra
    es el resultado: contiene el id del análisis y su semáforo. Por eso solo se
    entrega si ese análisis pertenece a la organización de quien pregunta, y en
    caso contrario se responde 404 — nunca 403, que confirmaría su existencia.
    """
    from app.tasks.celery_app import celery
    r = celery.AsyncResult(tarea_id)
    out = {"tarea_id": tarea_id, "estado": r.status}
    if r.successful():
        resultado = r.result if isinstance(r.result, dict) else {}
        propio = analisis_service.obtener_analisis(
            db, str(resultado.get("id", "")), organizacion_id=user.organizacion_id)
        if propio is None:
            raise HTTPException(404, "Tarea no encontrada")
        out["resultado"] = r.result
    elif r.failed():
        # El texto de la excepción puede describir datos de otra organización y
        # aquí no hay análisis contra el que comprobar la propiedad: se informa
        # del fallo sin detallarlo.
        out["error"] = "La tarea terminó con error"
    return out


@router.get("/analisis")
def listar(limit: int = 50, db: Session = Depends(get_db),
           user: models.Usuario = Depends(get_current_user)) -> list[dict]:
    return analisis_service.listar_analisis(db, limit, organizacion_id=user.organizacion_id)


@router.get("/analisis/{analisis_id}")
def detalle(analisis_id: str, db: Session = Depends(get_db),
            user: models.Usuario = Depends(get_current_user)) -> dict:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    # Fase 5E: `entrada` es siempre la del análisis original (el inmueble no
    # se simula); `resultado` es el de la configuración actualmente
    # seleccionada — la del propio análisis si no hay ninguna simulación
    # validada como vigente. `simulacion_validada_id` se añade de forma
    # aditiva para que el frontend sepa qué configuración está activa, sin
    # tocar ninguna de las claves que ya devolvía este endpoint.
    config = simulacion_service.obtener_configuracion_actual(db, analisis_id)
    return {"id": a.id, "creado_en": a.creado_en.isoformat() if a.creado_en else None,
            "perfil": a.perfil_codigo, "version_reglas": a.version_reglas,
            "version_parametros": a.version_parametros, "entrada": config.entrada,
            "resultado": config.resultado,
            "simulacion_validada_id": config.simulacion_id}


@router.get("/analisis/{analisis_id}/informe", response_class=PlainTextResponse)
def informe(analisis_id: str, db: Session = Depends(get_db),
            user: models.Usuario = Depends(get_current_user)) -> str:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    config = simulacion_service.obtener_configuracion_actual(db, analisis_id)
    return config.resultado.get("informe_markdown", "")


@router.get("/analisis/{analisis_id}/informe.pdf")
def informe_pdf(analisis_id: str, db: Session = Depends(get_db),
                user: models.Usuario = Depends(get_current_user)) -> Response:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    config = simulacion_service.obtener_configuracion_actual(db, analisis_id)
    pdf = pdf_service.informe_a_pdf(config.resultado.get("informe_markdown", ""))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="SEIS_informe_{analisis_id[:8]}.pdf"'})


@router.get("/analisis/{analisis_id}/checklist")
def checklist(analisis_id: str, db: Session = Depends(get_db),
              user: models.Usuario = Depends(get_current_user)) -> list[dict]:
    a = analisis_service.obtener_analisis(db, analisis_id, organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    config = simulacion_service.obtener_configuracion_actual(db, analisis_id)
    return config.resultado.get("checklist", [])


# ───────────────────── Informes oficiales (Fase 5F.4) ─────────────────────
#
# Espacio de nombres SEPARADO de `/informe` y `/informe.pdf`, que siguen
# significando «configuración actualmente seleccionada» y cambian cuando el
# usuario cambia de simulación. Todo lo que cuelga de `/informes` es un
# documento histórico congelado: se lee del snapshot, nunca se recalcula y
# nunca consulta los parámetros vigentes.
#
# Aislamiento: las cuatro rutas resuelven primero el análisis con
# `obtener_analisis(..., organizacion_id=...)`, que es fail-closed. Un
# análisis ajeno da 404, nunca 403, para no confirmar que existe.

def _analisis_propio(db: Session, analisis_id: str, user: models.Usuario) -> models.Analisis:
    a = analisis_service.obtener_analisis(db, analisis_id,
                                          organizacion_id=user.organizacion_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    return a


def _resumen_informe(i: models.Informe) -> dict:
    """Fila de listado: metadatos más lo mínimo del snapshot para que la lista
    sea útil sin abrir cada informe. No incluye `resultado` completo — serían
    N copias de un JSON grande. Mismo criterio que `listar_analisis`."""
    decision = i.resultado.get("decision", {}) if isinstance(i.resultado, dict) else {}
    return {"id": i.id, "analisis_id": i.analisis_id, "simulacion_id": i.simulacion_id,
            "generado_por": i.generado_por,
            "generado_en": i.generado_en.isoformat() if i.generado_en else None,
            "semaforo": decision.get("semaforo"), "ico": decision.get("ico")}


def _detalle_informe(i: models.Informe) -> dict:
    """Contenido congelado íntegro. `parametros_aplicados` puede ser `None` en
    análisis anteriores a la migración 0014 y se devuelve tal cual: declarar la
    carencia, nunca rellenarla con los parámetros vigentes hoy."""
    return {"id": i.id, "analisis_id": i.analisis_id, "simulacion_id": i.simulacion_id,
            "entrada_snapshot": i.entrada_snapshot,
            "parametros_aplicados": i.parametros_aplicados,
            "overrides": i.overrides, "resultado": i.resultado,
            "generado_por": i.generado_por,
            "generado_en": i.generado_en.isoformat() if i.generado_en else None}


@router.post("/analisis/{analisis_id}/informes", status_code=201)
def generar_informe(analisis_id: str, db: Session = Depends(get_db),
                    user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """Emite un informe oficial desde la configuración actualmente seleccionada.

    Acción explícita y deliberada: congela un documento histórico. No modifica
    el `Analisis` ni la `Simulacion`, ni cambia qué configuración está
    seleccionada. Puede emitirse más de uno por análisis.
    """
    _analisis_propio(db, analisis_id, user)
    try:
        informe = informe_service.generar_informe_oficial(
            db, analisis_id, usuario_id=user.id, quien=user.email)
    except informe_service.ConfiguracionInconsistenteError as exc:
        # 409 y no un informe degradado: emitir aquí declararía procedencia
        # original siendo falso. Único precedente de conflicto del proyecto.
        raise HTTPException(409, str(exc))
    except informe_service.PertenenciaCruzadaError as exc:
        raise HTTPException(409, str(exc))
    return _detalle_informe(informe)


@router.get("/analisis/{analisis_id}/informes")
def listar_informes(analisis_id: str, db: Session = Depends(get_db),
                    user: models.Usuario = Depends(get_current_user)) -> list[dict]:
    _analisis_propio(db, analisis_id, user)
    return [_resumen_informe(i) for i in informe_service.listar_informes(db, analisis_id)]


@router.get("/analisis/{analisis_id}/informes/{informe_id}")
def detalle_informe(analisis_id: str, informe_id: str, db: Session = Depends(get_db),
                    user: models.Usuario = Depends(get_current_user)) -> dict:
    _analisis_propio(db, analisis_id, user)
    try:
        informe = informe_service.obtener_informe(db, analisis_id, informe_id)
    except informe_service.InformeNoEncontradoError:
        raise HTTPException(404, "Informe no encontrado")
    return _detalle_informe(informe)


@router.get("/analisis/{analisis_id}/informes/{informe_id}/pdf")
def informe_oficial_pdf(analisis_id: str, informe_id: str, db: Session = Depends(get_db),
                        user: models.Usuario = Depends(get_current_user)) -> Response:
    """PDF derivado EXCLUSIVAMENTE del Markdown congelado de este informe.

    No pasa por `obtener_configuracion_actual`, así que no cambia cuando
    cambia la configuración seleccionada. No ejecuta M14 ni lee parámetros.
    """
    _analisis_propio(db, analisis_id, user)
    try:
        informe = informe_service.obtener_informe(db, analisis_id, informe_id)
    except informe_service.InformeNoEncontradoError:
        raise HTTPException(404, "Informe no encontrado")
    pdf = pdf_service.informe_a_pdf(informe.resultado.get("informe_markdown", ""))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="SEIS_informe_{informe_id[:8]}.pdf"'})


# ───────────────────── Simulaciones (Fase 5F.6) ─────────────────────
#
# Superficie HTTP de `simulacion_service` (Fases 5D/5E/5E.1). Las rutas no
# reimplementan nada: estados, transiciones, pertenencia y selección los
# decide el servicio; aquí solo se autoriza, se traduce el error y se
# serializa el snapshot ya persistido — ningún GET ejecuta el motor.
#
# Aislamiento en dos capas, igual que los informes: `_analisis_propio`
# primero (análisis ajeno o inexistente → 404, nunca 403) y después el
# guardián de pertenencia del servicio, porque el id de simulación es global:
# `/analisis/A/simulaciones/{sim-de-B}` da 404 aunque A y B sean de la misma
# organización. Ajena e inexistente responden igual para no confirmar nada.

class SimulacionNueva(BaseModel):
    # Fase 5F.7.1: un campo desconocido (p. ej. `override` en singular) da 422
    # en vez de ignorarse y crear en silencio una simulación sin overrides.
    model_config = ConfigDict(extra="forbid")

    overrides: dict[str, Any] = {}


def _detalle_simulacion(s: models.Simulacion) -> dict:
    """Snapshot persistido íntegro; `resultado` es el que produjo el motor al
    crearla, nunca se recalcula ni se completa con parámetros vigentes."""
    return {"id": s.id, "analisis_id": s.analisis_id, "estado": s.estado,
            "overrides": s.overrides, "parametros_aplicados": s.parametros_aplicados,
            "resultado": s.resultado, "version_parametros_base": s.version_parametros_base,
            "version_reglas": s.version_reglas, "usuario": s.usuario,
            "creado_en": s.creado_en.isoformat() if s.creado_en else None,
            "fecha_validacion": s.fecha_validacion.isoformat() if s.fecha_validacion else None}


def _resumen_simulacion(s: models.Simulacion, simulacion_actual_id: str | None) -> dict:
    """Fila de listado: sin `resultado` completo — serían N copias de un JSON
    grande. Mismo criterio que `_resumen_informe`."""
    decision = s.resultado.get("decision", {}) if isinstance(s.resultado, dict) else {}
    precios = decision.get("precios") or {}
    return {"id": s.id, "estado": s.estado,
            "creado_en": s.creado_en.isoformat() if s.creado_en else None,
            "fecha_validacion": s.fecha_validacion.isoformat() if s.fecha_validacion else None,
            "usuario": s.usuario, "overrides": s.overrides,
            "semaforo": decision.get("semaforo"), "ico": decision.get("ico"),
            "p_objetivo": precios.get("p_objetivo"), "p_max": precios.get("p_max"),
            "es_configuracion_actual": s.id == simulacion_actual_id}


def _error_simulacion(exc: simulacion_service.SimulacionError) -> HTTPException:
    """Traducción única de los errores del servicio al contrato HTTP de 5F.6.
    Pertenencia cruzada da 404 con el mismo mensaje que «inexistente»."""
    if isinstance(exc, simulacion_service.AnalisisNoEncontradoError):
        return HTTPException(404, "Análisis no encontrado")
    if isinstance(exc, (simulacion_service.SimulacionNoEncontradaError,
                        simulacion_service.PertenenciaCruzadaError)):
        return HTTPException(404, "Simulación no encontrada")
    if isinstance(exc, simulacion_service.OverrideInvalidoError):
        return HTTPException(422, str(exc))
    if isinstance(exc, (simulacion_service.TransicionInvalidaError,
                        simulacion_service.ReconstruccionInvalidaError)):
        return HTTPException(409, str(exc))
    raise exc


@router.post("/analisis/{analisis_id}/simulaciones", status_code=201)
def crear_simulacion(analisis_id: str, body: SimulacionNueva | None = None,
                     db: Session = Depends(get_db),
                     user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """Ejecuta M01-M14 con los overrides y persiste una simulación `pendiente`.

    No toca el `Analisis` ni cambia la configuración seleccionada. Se guarda
    `user.id` en `Simulacion.usuario`, no el correo: `borrado_service` no
    alcanza esa tabla y el correo sobreviviría al derecho de supresión.
    """
    _analisis_propio(db, analisis_id, user)
    overrides = body.overrides if body is not None else {}
    try:
        sim = simulacion_service.crear_simulacion(db, analisis_id, overrides,
                                                  usuario=user.id, quien=user.email)
    except simulacion_service.SimulacionError as exc:
        raise _error_simulacion(exc)
    return _detalle_simulacion(sim)


@router.get("/analisis/{analisis_id}/simulaciones")
def listar_simulaciones(analisis_id: str, db: Session = Depends(get_db),
                        user: models.Usuario = Depends(get_current_user)) -> list[dict]:
    a = _analisis_propio(db, analisis_id, user)
    return [_resumen_simulacion(s, a.simulacion_validada_id)
            for s in simulacion_service.listar_simulaciones(db, analisis_id)]


@router.get("/analisis/{analisis_id}/simulaciones/{simulacion_id}")
def detalle_simulacion(analisis_id: str, simulacion_id: str, db: Session = Depends(get_db),
                       user: models.Usuario = Depends(get_current_user)) -> dict:
    _analisis_propio(db, analisis_id, user)
    try:
        sim = simulacion_service.obtener_simulacion(db, analisis_id, simulacion_id)
    except simulacion_service.SimulacionError as exc:
        raise _error_simulacion(exc)
    return _detalle_simulacion(sim)


@router.post("/analisis/{analisis_id}/simulaciones/{simulacion_id}/validar")
def validar_simulacion(analisis_id: str, simulacion_id: str, db: Session = Depends(get_db),
                       user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """`pendiente → validada` y la fija como configuración actual (una transacción)."""
    _analisis_propio(db, analisis_id, user)
    try:
        sim = simulacion_service.validar_simulacion(db, analisis_id, simulacion_id,
                                                    quien=user.email)
    except simulacion_service.SimulacionError as exc:
        raise _error_simulacion(exc)
    return _detalle_simulacion(sim)


@router.post("/analisis/{analisis_id}/simulaciones/{simulacion_id}/descartar")
def descartar_simulacion(analisis_id: str, simulacion_id: str, db: Session = Depends(get_db),
                         user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """`pendiente → descartada`. No mueve la configuración seleccionada."""
    _analisis_propio(db, analisis_id, user)
    try:
        sim = simulacion_service.descartar_simulacion(db, analisis_id, simulacion_id,
                                                      quien=user.email)
    except simulacion_service.SimulacionError as exc:
        raise _error_simulacion(exc)
    return _detalle_simulacion(sim)


@router.post("/analisis/{analisis_id}/simulaciones/{simulacion_id}/seleccionar")
def seleccionar_simulacion(analisis_id: str, simulacion_id: str, db: Session = Depends(get_db),
                           user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """Vuelve a fijar como actual una simulación YA `validada`, sin cambiar su
    estado. Devuelve el detalle de la simulación seleccionada."""
    _analisis_propio(db, analisis_id, user)
    try:
        simulacion_service.seleccionar_simulacion_validada(db, analisis_id, simulacion_id,
                                                           quien=user.email)
        sim = simulacion_service.obtener_simulacion(db, analisis_id, simulacion_id)
    except simulacion_service.SimulacionError as exc:
        raise _error_simulacion(exc)
    return _detalle_simulacion(sim)


@router.post("/analisis/{analisis_id}/configuracion/original")
def volver_a_configuracion_original(
        analisis_id: str, db: Session = Depends(get_db),
        user: models.Usuario = Depends(require_rol(*ROLES_ESCRITURA))) -> dict:
    """`simulacion_validada_id = NULL`. Idempotente; no toca ninguna simulación.

    Fuera de `/simulaciones/` a propósito: cambia la configuración del análisis,
    no una simulación. Responde con el mismo cuerpo que `GET /analisis/{id}`,
    llamando a esa ruta en vez de duplicar su serialización.
    """
    _analisis_propio(db, analisis_id, user)
    try:
        simulacion_service.volver_a_configuracion_original(db, analisis_id, quien=user.email)
    except simulacion_service.SimulacionError as exc:
        raise _error_simulacion(exc)
    return detalle(analisis_id, db=db, user=user)

"""Derechos del titular sobre su cuenta (Fase 14, RGPD).

Acceso (`GET /cuenta/exportar`), supresión (`DELETE /cuenta`) y el
arrepentimiento dentro de la gracia (`POST /cuenta/borrado/cancelar`).

Todo aquí actúa **sobre quien pide**, nunca sobre un identificador que venga en
la petición. No hay ninguna ruta con `{usuario_id}`: no es un descuido, es lo
que hace estructuralmente imposible que un usuario exporte o borre la cuenta de
otro. Un endpoint que aceptara el id tendría que comprobar la propiedad en cada
llamada, y esa comprobación es justo la que se olvida.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_current_user
from app.core.db import get_db
from app.legal import textos
from app.services import cuenta_service

router = APIRouter(prefix="/cuenta", tags=["cuenta"])

# Router aparte y SIN autenticar: los textos legales hay que poder leerlos antes
# de tener cuenta. Una casilla de consentimiento que no deja leer lo que se
# acepta no recoge consentimiento, recoge un clic.
router_legal = APIRouter(prefix="/legal", tags=["legal"])


@router_legal.get("/{tipo}")
def texto_legal(tipo: str) -> dict:
    """Devuelve un texto legal con su versión. Público."""
    texto = textos.TEXTOS.get(tipo)
    if texto is None:
        raise HTTPException(404, "Texto no encontrado")
    return {"tipo": texto.tipo, "titulo": texto.titulo, "version": texto.version,
            "cuerpo": texto.cuerpo, "obligatorio": texto.obligatorio,
            # El frontend lo usa para avisar de que aún no es definitivo. Se
            # informa en vez de ocultarlo: un texto provisional que se presenta
            # como definitivo es peor que uno que se declara provisional.
            "pendiente_de_redaccion": texto.pendiente}


@router_legal.get("")
def indice_legal() -> dict:
    return {"version_vigente": textos.VERSION_VIGENTE,
            "textos": [{"tipo": t.tipo, "titulo": t.titulo,
                        "obligatorio": t.obligatorio}
                       for t in textos.TEXTOS.values()]}


class RespuestaBorrado(BaseModel):
    ok: bool
    mensaje: str
    se_ejecutara_en: str | None = None


@router.get("/exportar")
def exportar(user: models.Usuario = Depends(get_current_user),
             db: Session = Depends(get_db)) -> JSONResponse:
    """Derecho de acceso: todo lo que el sistema guarda sobre quien pide.

    Se sirve como descarga (`Content-Disposition`) y no como respuesta suelta
    para que el titular acabe con un fichero que pueda guardar, que es lo que el
    derecho de portabilidad busca.
    """
    datos = cuenta_service.exportar_datos(db, user)
    return JSONResponse(
        content=datos,
        headers={"Content-Disposition": 'attachment; filename="seis-mis-datos.json"'})


@router.delete("", response_model=RespuestaBorrado)
def solicitar_borrado(user: models.Usuario = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> RespuestaBorrado:
    """Derecho de supresión, con {} días de gracia.

    Responde 200 y no 204 a propósito: el titular necesita saber **cuándo** se
    ejecutará y que hasta entonces puede echarse atrás. Un 204 mudo dejaría esa
    información solo en la documentación.
    """
    cuando = cuenta_service.solicitar_borrado(db, user)
    return RespuestaBorrado(
        ok=True,
        mensaje=(f"Su cuenta se borrará el {cuando:%d-%m-%Y}. Hasta entonces puede "
                 "cancelarlo desde su cuenta."),
        se_ejecutara_en=cuando.isoformat())


@router.post("/borrado/cancelar", response_model=RespuestaBorrado)
def cancelar_borrado(user: models.Usuario = Depends(get_current_user),
                     db: Session = Depends(get_db)) -> RespuestaBorrado:
    """Retira una solicitud de borrado que aún esté en gracia."""
    habia = cuenta_service.cancelar_borrado(db, user)
    return RespuestaBorrado(
        ok=True,
        mensaje=("Se ha cancelado el borrado de su cuenta." if habia
                 else "No había ningún borrado pendiente."))


@router.get("/consentimientos")
def mis_consentimientos(user: models.Usuario = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> dict:
    """Qué aceptó, en qué versión y cuándo — y si esa versión sigue vigente.

    `vigente` es lo que convierte esto en algo útil: cuando lleguen los textos
    reales y suba la versión, esta pantalla dice a quién hay que volver a
    preguntar en vez de asumir que lo aceptado hace un año sigue valiendo.
    """
    filas = (db.query(models.Consentimiento)
             .filter(models.Consentimiento.usuario_id == user.id)
             .order_by(models.Consentimiento.otorgado_en.desc()).all())
    return {
        "version_vigente": textos.VERSION_VIGENTE,
        "consentimientos": [
            {"tipo": c.tipo, "version": c.version, "otorgado": c.otorgado,
             "otorgado_en": c.otorgado_en.isoformat() if c.otorgado_en else None,
             "vigente": c.version == textos.VERSION_VIGENTE}
            for c in filas],
    }

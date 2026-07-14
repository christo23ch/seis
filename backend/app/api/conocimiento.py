"""API de gobernanza del conocimiento (T2/T3): reglas, parámetros y perfiles."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_current_user, require_superadmin
from app.core.db import get_db
from app.services import conocimiento_service as cs

router = APIRouter(tags=["conocimiento"])


class ParametroUpdate(BaseModel):
    clave: str
    valor: Any
    fuente_legal: str | None = None


class ReglaNueva(BaseModel):
    definicion: dict
    justificacion: str


class PerfilUpdate(BaseModel):
    parametros: dict


# ─────────────── Reglas (T2) ───────────────
@router.get("/reglas")
def reglas(db: Session = Depends(get_db),
           _u: models.Usuario = Depends(get_current_user)) -> dict:
    defs, version = cs.reglas_vigentes(db)
    return {"version": version, "reglas": defs}


@router.get("/reglas/{codigo}/historial")
def historial(codigo: str, db: Session = Depends(get_db),
              _u: models.Usuario = Depends(get_current_user)) -> list[dict]:
    filas = cs.historial_regla(db, codigo)
    if not filas:
        raise HTTPException(404, "Regla sin historial en BD")
    return [{"version": f.version, "categoria": f.categoria,
             "vigente_desde": f.vigente_desde.isoformat() if f.vigente_desde else None,
             "vigente_hasta": f.vigente_hasta.isoformat() if f.vigente_hasta else None,
             "autor": f.autor, "justificacion": f.justificacion} for f in filas]


@router.post("/reglas", status_code=201)
def nueva_version(body: ReglaNueva, db: Session = Depends(get_db),
                  admin: models.Usuario = Depends(require_superadmin)) -> dict:
    try:
        fila = cs.crear_version_regla(db, body.definicion, admin.email, body.justificacion)
    except ValueError as e:
        raise HTTPException(400, f"Regla inválida: {e}")
    return {"codigo": fila.codigo, "version": fila.version}


# ─────────────── Parámetros (T3) ───────────────
@router.get("/parametros")
def parametros(db: Session = Depends(get_db),
               _u: models.Usuario = Depends(get_current_user)) -> dict:
    return cs.parametros_vigentes(db).raw()


@router.put("/parametros")
def actualizar_parametro(body: ParametroUpdate, db: Session = Depends(get_db),
                         admin: models.Usuario = Depends(require_superadmin)) -> dict:
    try:
        cs.set_parametro(db, body.clave, body.valor, body.fuente_legal, admin.email)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"clave": body.clave, "valor": body.valor, "vigente": True}


# ─────────────── Perfiles ───────────────
@router.get("/perfiles")
def perfiles(db: Session = Depends(get_db),
             _u: models.Usuario = Depends(get_current_user)) -> dict:
    params, _, _ = cs.cargar_conocimiento(db)
    return params.seccion("perfiles")


@router.put("/perfiles/{codigo}")
def actualizar_perfil(codigo: str, body: PerfilUpdate, db: Session = Depends(get_db),
                      admin: models.Usuario = Depends(require_superadmin)) -> dict:
    try:
        fila = cs.actualizar_perfil(db, codigo, body.parametros, admin.email)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"codigo": fila.codigo, "parametros": fila.parametros}


@router.get("/opciones")
def opciones(db: Session = Depends(get_db),
             _u: models.Usuario = Depends(get_current_user)) -> dict:
    params, _, _ = cs.cargar_conocimiento(db)
    return {
        "tipologias": ["vivienda", "garaje", "trastero", "local", "oficina", "nave",
                       "suelo_urbano", "suelo_rustico", "hotel", "singular"],
        "fuentes": list(params.seccion("adjudicacion.ratios").keys()),
        "estados_conservacion": ["ruina", "malo", "regular", "bueno", "reformado"],
        "estados_ocupacion": ["desconocida", "vacio", "propietario", "precario",
                              "arrendado_posterior", "arrendado_anterior", "renta_antigua"],
        "ccaa": list(params.seccion("fiscal.itp_por_ccaa").keys()),
        "perfiles": {k: v.get("nombre", k) for k, v in params.seccion("perfiles").items()},
    }

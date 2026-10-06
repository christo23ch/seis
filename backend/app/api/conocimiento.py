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
from app.services.simulacion_service import OverrideInvalidoError

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
    except OverrideInvalidoError as e:            # Fase 5G.4: fuera de rango
        raise HTTPException(422, str(e))
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
        # Fase 5I-D: «desconocido» = «No consta» (ADR-0020); solo para el inmueble.
        "estados_conservacion": ["desconocido", "ruina", "malo", "regular", "bueno", "reformado"],
        "estados_ocupacion": ["desconocida", "vacio", "propietario", "precario",
                              "arrendado_posterior", "arrendado_anterior", "renta_antigua"],
        "ccaa": list(params.seccion("fiscal.itp_por_ccaa").keys()),
        "perfiles": {k: v.get("nombre", k) for k, v in params.seccion("perfiles").items()},
        # Fase 5I: lo que el motor aplica cuando un campo opcional del alta va vacío,
        # leído del catálogo T3 vigente para que el formulario lo muestre sin copiar
        # cifras. Solo informa: el cálculo sigue en el motor (M05, M06).
        "valores_defecto": {
            "itp_por_ccaa": params.seccion("fiscal.itp_por_ccaa"),
            "tenencia_mensual": float(params.get("tenencia.mensual_defecto")),
            "atrasos_pct_valor_subasta": float(params.get("atrasos.defecto_pct_vt")),
            "atrasos_minimo": float(params.get("atrasos.minimo")),
            # Misma suma que M06 (`m06_costes.py`, C_F sin override y sin hipoteca);
            # `test_el_coste_fijo_mostrado_es_el_que_aplica_el_motor` vigila que coincidan.
            "adquisicion_fija": float(params.get("aranceles.adquisicion_fija"))
                                + float(params.get("aranceles.procurador")),
            "tasacion_banco": float(params.get("financiacion.tasacion_banco")),
            "baremos_reforma_m2": params.seccion("reforma.baremos_m2"),
            "estado_conservacion_desconocido": params.get("conservacion.desconocido_usa"),
        },
    }

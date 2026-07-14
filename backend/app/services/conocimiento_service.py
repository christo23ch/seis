"""Gobernanza del conocimiento (§8.3, T2/T3): reglas, parámetros y perfiles
versionados en BD con vigencias, validación estructural y auditoría.

El pipeline consume SIEMPRE el conocimiento vigente en BD (sembrado desde los
YAML); los YAML quedan como semilla y fallback de arranque.
"""
from __future__ import annotations

import ast as pyast
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app import models
from app.engine.params.store import Parametros, cargar_defaults
from app.engine.pipeline import cargar_catalogo

_EFECTOS_VALIDOS = {"veto", "techo_semaforo", "condicion", "hechos"}
_OPS_VALIDOS = {">", ">=", "<", "<=", "==", "!=", "in", "not_in", "is_true", "is_false"}


# ───────────────────────── PARÁMETROS (T3) ─────────────────────────
def parametros_vigentes(db: Session) -> Parametros:
    base = cargar_defaults()
    filas = (db.query(models.Parametro)
             .filter(models.Parametro.clave != "__defaults__").all())
    ultimo: dict[str, models.Parametro] = {}
    for f in filas:                                   # última vigencia por clave
        if f.clave not in ultimo or f.vigente_desde > ultimo[f.clave].vigente_desde:
            ultimo[f.clave] = f
    if not ultimo:
        return base
    overrides = {clave: fila.valor for clave, fila in ultimo.items()}
    overrides["version"] = f"{base.version}+{len(ultimo)}ov"
    return base.con_overrides(overrides)


def set_parametro(db: Session, clave: str, valor, fuente_legal: str | None,
                  quien: str) -> models.Parametro:
    base = cargar_defaults()
    try:
        base.get(clave)                               # la ruta debe existir en el árbol T3
    except KeyError:
        raise ValueError(f"Ruta de parámetro desconocida: {clave}")
    fila = models.Parametro(clave=clave, ambito="nacional",
                            vigente_desde=date.today().isoformat(),
                            valor=valor, fuente_legal=fuente_legal)
    db.merge(fila)                                    # misma clave+fecha ⇒ reemplaza
    db.add(models.Auditoria(quien=quien, entidad="parametro", entidad_id=clave,
                            accion="actualizar", delta={"valor": valor}))
    db.commit()
    return fila


# ───────────────────────── REGLAS (T2) ─────────────────────────
def validar_regla(definicion: dict) -> None:
    """Validación estructural + compilación de expresiones (falla antes de guardar)."""
    for campo in ("codigo", "cuando", "efecto"):
        if campo not in definicion:
            raise ValueError(f"Regla sin campo obligatorio '{campo}'")
    cuando = definicion["cuando"]
    if not any(k in cuando for k in ("all", "any")):
        raise ValueError("'cuando' debe contener 'all' o 'any'")
    for cond in cuando.get("all", []) + cuando.get("any", []):
        if "hecho" not in cond:
            raise ValueError("Condición sin 'hecho'")
        if cond.get("op", "==") not in _OPS_VALIDOS:
            raise ValueError(f"Operador no permitido: {cond.get('op')}")
        if "expr" in cond:
            pyast.parse(cond["expr"], mode="eval")    # sintaxis de la expresión
    desconocidos = set(definicion["efecto"]) - _EFECTOS_VALIDOS
    if desconocidos:
        raise ValueError(f"Efectos desconocidos: {sorted(desconocidos)}")


def reglas_vigentes(db: Session) -> tuple[list[dict], str]:
    filas = db.query(models.Regla).filter(models.Regla.vigente_hasta.is_(None)).all()
    if not filas:
        return cargar_catalogo()                      # fallback semilla YAML
    defs = [f.definicion for f in filas]
    version = max(f.version for f in filas)
    return defs, version


def historial_regla(db: Session, codigo: str) -> list[models.Regla]:
    return (db.query(models.Regla).filter(models.Regla.codigo == codigo)
            .order_by(models.Regla.version).all())


def crear_version_regla(db: Session, definicion: dict, autor: str,
                        justificacion: str) -> models.Regla:
    validar_regla(definicion)
    ahora = datetime.now(timezone.utc)
    codigo = definicion["codigo"]
    hoy = ahora.strftime("%Y.%m.%d")
    seq = 1 + sum(1 for r in historial_regla(db, codigo) if r.version.startswith(hoy))
    version = f"{hoy}.{seq}"
    definicion = {**definicion, "version": version}

    (db.query(models.Regla)
       .filter(models.Regla.codigo == codigo, models.Regla.vigente_hasta.is_(None))
       .update({models.Regla.vigente_hasta: ahora}))
    fila = models.Regla(codigo=codigo, version=version,
                        categoria=definicion.get("categoria", "regla"),
                        prioridad=int(definicion.get("prioridad", 100)),
                        definicion=definicion, vigente_desde=ahora,
                        autor=autor, justificacion=justificacion)
    db.add(fila)
    db.add(models.Auditoria(quien=autor, entidad="regla", entidad_id=codigo,
                            accion="nueva_version", delta={"version": version,
                                                           "justificacion": justificacion}))
    db.commit()
    return fila


# ───────────────────────── PERFILES ─────────────────────────
def actualizar_perfil(db: Session, codigo: str, parametros: dict, quien: str) -> models.PerfilInversion:
    fila = db.get(models.PerfilInversion, codigo)
    if not fila:
        raise LookupError(f"Perfil desconocido: {codigo}")
    tipo = parametros.get("tipo")
    if tipo not in ("venta", "rentista"):
        raise ValueError("El perfil debe declarar tipo 'venta' o 'rentista'")
    if tipo == "venta" and not {"m_objetivo", "m_minimo", "rvc_veto"} <= set(parametros):
        raise ValueError("Perfil de venta requiere m_objetivo, m_minimo y rvc_veto")
    if tipo == "rentista" and "coc_min" not in parametros:
        raise ValueError("Perfil rentista requiere coc_min")
    anterior = fila.parametros
    fila.parametros = parametros
    db.add(models.Auditoria(quien=quien, entidad="perfil", entidad_id=codigo,
                            accion="actualizar", delta={"antes": anterior, "despues": parametros}))
    db.commit()
    db.refresh(fila)
    return fila


# ───────────────────────── CARGA CONSOLIDADA ─────────────────────────
def cargar_conocimiento(db: Session) -> tuple[Parametros, list[dict], str]:
    """Conocimiento vigente completo para el pipeline: parámetros (+overrides),
    perfiles de BD fusionados y catálogo de reglas vigente."""
    params = parametros_vigentes(db)
    perfiles = db.query(models.PerfilInversion).all()
    if perfiles:
        params = params.con_overrides({f"perfiles.{p.codigo}": p.parametros for p in perfiles})
    reglas, version_reglas = reglas_vigentes(db)
    return params, reglas, version_reglas

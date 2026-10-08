"""Siembra del conocimiento y del administrador inicial (Fase 11, Bloque E).

Extraído de `init_db.py` para separar dos cosas que no deben ir juntas:

- **Crear el esquema** es responsabilidad exclusiva de Alembic fuera de
  desarrollo. Ver `init_db.py` para el porqué.
- **Sembrar** es idempotente y sí puede correr en cualquier arranque: cada
  bloque comprueba antes si ya hay datos.

Tenerlo en su propio módulo permite además invocarlo a mano
(`python -m scripts.sembrar`) contra una base ya migrada, sin arrastrar consigo
ninguna creación de tablas.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import cargar_catalogo

FUENTES = ("judicial_boe", "aeat", "tgss", "concursal", "banco", "notarial", "privada")


def sembrar_conocimiento(db: Session) -> None:
    """Perfiles, reglas T2, parámetros T3 y fuentes de subasta. Idempotente."""
    params = cargar_defaults()
    if not db.query(models.PerfilInversion).first():
        for codigo, cfg in params.seccion("perfiles").items():
            db.add(models.PerfilInversion(codigo=codigo,
                                          nombre=cfg.get("nombre", codigo),
                                          parametros=cfg))
    sincronizar_reglas(db)
    if not db.query(models.Parametro).first():
        db.add(models.Parametro(clave="__defaults__", ambito="nacional",
                                valor=params.raw(),
                                fuente_legal="Semilla v" + params.version))
    for codigo in FUENTES:
        if not db.query(models.FuenteSubasta).filter_by(codigo=codigo).first():
            db.add(models.FuenteSubasta(codigo=codigo, perfil={}))
    db.commit()


def sincronizar_reglas(db: Session) -> list[str]:
    """Reglas T2 del catálogo YAML en la tabla `regla` (Fase 5J-3). Idempotente.

    Antes solo se copiaba el catálogo con la tabla vacía y, como `reglas_vigentes` ignora el
    YAML en cuanto hay filas, una versión nueva de una regla (SEM-EJEC-01 2026.10 en la 5J-2b)
    no llegaba nunca a las bases ya sembradas. Ahora, por cada regla del catálogo:

    - sin fila vigente con ese código ⇒ se inserta;
    - con fila vigente de OTRA versión **que vino de la siembra** (sin autor) ⇒ se cierra su
      vigencia y se inserta la del catálogo, también sin autor;
    - con fila vigente creada por la API (con autor) ⇒ no se toca: manda quien la editó;
    - si la versión del catálogo ya existió y se cerró, no se resucita.

    Una regla que desaparece del YAML no se borra de la base. Devuelve lo que ha cambiado.
    """
    catalogo, version_catalogo = cargar_catalogo()
    ahora = datetime.now(timezone.utc)
    cambios: list[str] = []
    for r in catalogo:
        codigo, version = r["codigo"], str(r.get("version", version_catalogo))
        vigente = (db.query(models.Regla)
                     .filter(models.Regla.codigo == codigo, models.Regla.vigente_hasta.is_(None))
                     .order_by(models.Regla.version.desc()).first())
        if vigente is not None and (vigente.version == version or vigente.autor is not None):
            continue
        if db.get(models.Regla, (codigo, version)) is not None:
            continue
        if vigente is not None:
            vigente.vigente_hasta = ahora
        db.add(models.Regla(codigo=codigo, version=version, categoria=r.get("categoria", "regla"),
                            prioridad=int(r.get("prioridad", 100)), definicion=r,
                            vigente_desde=ahora if vigente is not None else None,
                            justificacion=None if vigente is None else
                            f"Sincronizada con el catálogo YAML (antes {vigente.version})"))
        cambios.append(f"{codigo} {vigente.version} → {version}" if vigente is not None
                       else f"{codigo} {version} (nueva)")
        if vigente is not None:
            db.add(models.Auditoria(quien="semilla", entidad="regla", entidad_id=codigo,
                                    accion="sincronizar_catalogo",
                                    delta={"version_anterior": vigente.version, "version": version}))
    db.flush()
    return cambios


def sembrar_admin(db: Session) -> bool:
    """Crea el administrador inicial **solo si no hay ningún usuario**.

    La condición no es cosmética: es lo que impide que un arranque cree un
    superadministrador en una instalación que ya está en marcha. Devuelve True si
    lo creó.
    """
    if db.query(models.Usuario).first():
        return False
    from app.services.usuario_service import crear_organizacion, crear_usuario

    s = get_settings()
    org = (db.query(models.Organizacion).first()
           or crear_organizacion(db, "Organización por defecto"))
    crear_usuario(db, s.admin_email, s.admin_password, "Administrador", "admin",
                  organizacion_id=org.id, rol_org="propietario", es_superadmin=True)
    return True


def main() -> None:
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        sembrar_conocimiento(db)
        if sembrar_admin(db):
            print(f"Usuario administrador creado: {get_settings().admin_email} "
                  "— CAMBIE LA CONTRASEÑA.")
        print("SEIS · conocimiento sembrado (reglas, parámetros, perfiles, fuentes).")
    finally:
        db.close()


if __name__ == "__main__":
    main()

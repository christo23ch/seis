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
    if not db.query(models.Regla).first():
        catalogo, version = cargar_catalogo()
        for r in catalogo:
            db.add(models.Regla(codigo=r["codigo"],
                                version=str(r.get("version", version)),
                                categoria=r.get("categoria", "regla"),
                                prioridad=int(r.get("prioridad", 100)),
                                definicion=r))
    if not db.query(models.Parametro).first():
        db.add(models.Parametro(clave="__defaults__", ambito="nacional",
                                valor=params.raw(),
                                fuente_legal="Semilla v" + params.version))
    for codigo in FUENTES:
        if not db.query(models.FuenteSubasta).filter_by(codigo=codigo).first():
            db.add(models.FuenteSubasta(codigo=codigo, perfil={}))
    db.commit()


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

"""Inicializa el esquema y siembra el conocimiento (reglas T2, parámetros T3, perfiles)."""
from app.core.db import Base, SessionLocal, engine
from app import models
from app.engine.params.store import cargar_defaults
from app.engine.pipeline import cargar_catalogo
from app.core.config import get_settings


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        params = cargar_defaults()
        if not db.query(models.PerfilInversion).first():
            for codigo, cfg in params.seccion("perfiles").items():
                db.add(models.PerfilInversion(codigo=codigo, nombre=cfg.get("nombre", codigo),
                                              parametros=cfg))
        if not db.query(models.Regla).first():
            catalogo, version = cargar_catalogo()
            for r in catalogo:
                db.add(models.Regla(codigo=r["codigo"], version=str(r.get("version", version)),
                                    categoria=r.get("categoria", "regla"),
                                    prioridad=int(r.get("prioridad", 100)), definicion=r))
        if not db.query(models.Parametro).first():
            db.add(models.Parametro(clave="__defaults__", ambito="nacional",
                                    valor=params.raw(),
                                    fuente_legal="Semilla v" + params.version))
        for codigo in ["judicial_boe", "aeat", "tgss", "concursal", "banco", "notarial", "privada"]:
            if not db.query(models.FuenteSubasta).filter_by(codigo=codigo).first():
                db.add(models.FuenteSubasta(codigo=codigo, perfil={}))
        db.commit()
        if not db.query(models.Usuario).first():
            from app.services.usuario_service import crear_usuario
            s = get_settings()
            crear_usuario(db, s.admin_email, s.admin_password, "Administrador", "admin")
            print(f"Usuario administrador creado: {s.admin_email} — CAMBIE LA CONTRASEÑA.")
        print("SEIS · esquema creado y conocimiento sembrado (reglas, parámetros, perfiles, fuentes).")
    finally:
        db.close()


if __name__ == "__main__":
    main()

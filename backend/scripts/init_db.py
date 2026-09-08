"""Arranque de la base: esquema en desarrollo, siembra siempre.

**`create_all` NO se ejecuta fuera de desarrollo, y esa es la razón de ser de
este módulo tal como está escrito.**

`CLAUDE.md` §6.9 prohíbe derivar la DDL de los modelos dentro de
`alembic/versions/`, porque una revisión así no describe un cambio de esquema:
reproduce el estado que los modelos tengan **el día que se ejecute**. Hasta la
Fase 11, ese mismo antipatrón vivía aquí, en la ruta de arranque, y
`docker-compose.yml` lo encadenaba **después** de `alembic upgrade head`.

La consecuencia era exactamente la que la prohibición busca evitar, solo que
peor situada: si un modelo declara una tabla o una columna que ninguna migración
crea, `create_all` **la crea en silencio en producción**. El esquema real deja
de ser el que describe la cadena de migraciones, dos instalaciones con la misma
revisión acaban distintas, y la deriva que el test T4 existe para detectar queda
enmascarada justo donde más caro sale.

En `development` y `test` sí se ejecuta, porque ahí no hay migraciones que
respetar y crear el esquema al vuelo es lo cómodo y lo inocuo.
"""
from __future__ import annotations

from app.core.config import entorno_normalizado, get_settings

# Entornos donde el esquema se crea desde los modelos. El resto lo gobierna
# Alembic, sin excepción.
ENTORNOS_CON_CREATE_ALL = ("development", "test")


def crear_esquema_si_procede() -> bool:
    """Crea el esquema desde los modelos solo en desarrollo. Devuelve si lo hizo."""
    from app.core.db import Base, engine

    entorno = entorno_normalizado(get_settings().seis_env)
    if entorno not in ENTORNOS_CON_CREATE_ALL:
        print(f"SEIS · entorno «{entorno}»: el esquema lo gobierna Alembic, "
              "no se ejecuta create_all.")
        return False
    Base.metadata.create_all(engine)
    return True


def main() -> None:
    from app.core.db import SessionLocal
    from scripts.sembrar import sembrar_admin, sembrar_conocimiento

    creado = crear_esquema_si_procede()
    db = SessionLocal()
    try:
        # La siembra sí corre en todos los entornos: es idempotente —cada bloque
        # comprueba antes si ya hay datos— y sin ella una instalación nueva
        # arranca sin reglas, sin parámetros y sin administrador, es decir,
        # inservible. Quitarla del arranque reintroduciría por otra puerta el
        # defecto que originó la Fase 9.5: que `docker compose up` no baste para
        # tener un sistema en pie.
        sembrar_conocimiento(db)
        if sembrar_admin(db):
            print(f"Usuario administrador creado: {get_settings().admin_email} "
                  "— CAMBIE LA CONTRASEÑA.")
    finally:
        db.close()
    print(f"SEIS · listo (esquema creado aquí: {'sí' if creado else 'no'}; "
          "conocimiento sembrado).")


if __name__ == "__main__":
    main()

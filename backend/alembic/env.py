"""Entorno Alembic de SEIS: la URL se toma de la configuración de la aplicación."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.db import Base
import app.models  # noqa: F401  (registra todas las tablas)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Sobre `render_as_batch` (Fase 9.5, Bloque I): NO se activa, y no por olvido.
    # Es una opción de `autogenerate` —hace que Alembic ESCRIBA bloques
    # `op.batch_alter_table()` al generar una revisión— y no altera en absoluto lo
    # que ocurre al EJECUTARLA. Medido sobre SQLite (SQLAlchemy 2.0.51 · Alembic
    # 1.18.5), los cuatro cruces posibles:
    #     alter_column      + render_as_batch=False -> FALLO (near "ALTER")
    #     alter_column      + render_as_batch=True  -> FALLO (near "ALTER")
    #     batch_alter_table + render_as_batch=False -> OK
    #     batch_alter_table + render_as_batch=True  -> OK
    # Es decir: no repara nada y `batch_alter_table` no lo necesita. Para alterar
    # una columna en SQLite hay que escribir `op.batch_alter_table()` a mano.
    # Activarlo aquí daría una falsa sensación de cobertura — ver CLAUDE.md §6.11.
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

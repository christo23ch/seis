"""Fase 10 — Alta self-service y recuperación de cuenta.

Introduce el soporte para registro público, verificación de email y
recuperación de contraseña:
- `usuario` += email_verificado (backfill: usuarios existentes → True, ya que
  fueron dados de alta por un administrador/propietario, no por sí mismos).
- Tabla nueva `token_consumido` (jti PK, proposito, consumido_en): garantiza
  el uso único de los tokens de propósito ("verificar" / "resetear").

Idempotente por el mismo motivo que 0002: en una BD nueva creada con
`Base.metadata.create_all` (tests/init_db) la columna y la tabla ya existen,
así que cada paso comprueba el esquema real antes de actuar.
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _tiene_columna(inspector, tabla: str, columna: str) -> bool:
    return columna in {c["name"] for c in inspector.get_columns(tabla)}


def _tiene_tabla(inspector, tabla: str) -> bool:
    return tabla in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Columna nueva en usuario, con backfill honesto: las cuentas existentes
    #    fueron creadas por un administrador (Fase 2) o un propietario (Fase 9),
    #    no por registro self-service, así que se consideran ya verificadas.
    if not _tiene_columna(inspector, "usuario", "email_verificado"):
        op.add_column("usuario", sa.Column("email_verificado", sa.Boolean,
                                           nullable=False, server_default=sa.false()))
        bind.execute(sa.text("UPDATE usuario SET email_verificado = :t"), {"t": True})

    # 2) Tabla de tokens de un solo uso
    if not _tiene_tabla(inspector, "token_consumido"):
        op.create_table(
            "token_consumido",
            sa.Column("jti", sa.String(36), primary_key=True),
            sa.Column("proposito", sa.String(16), nullable=False),
            sa.Column("consumido_en", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _tiene_tabla(inspector, "token_consumido"):
        op.drop_table("token_consumido")

    if _tiene_columna(inspector, "usuario", "email_verificado"):
        op.drop_column("usuario", "email_verificado")

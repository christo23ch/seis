"""Fase 10 — alta self-service: verificación de email y uso único de tokens.

Añade `usuario.email_verificado` y crea la tabla `token_consumido`.

Tres decisiones que conviene no reinventar al leer esta revisión:

1. **`email_verificado` se añade CON `server_default`.** La revisión fundacional
   `0005` no usa `server_default` en ninguna de sus 21 tablas —todos los defaults
   viven en el ORM—, pero allí todas las tablas se crean vacías. Aquí la columna
   es `NOT NULL` sobre una tabla que ya tiene filas, así que sin default de
   servidor el `ALTER` no puede completarse. El default se deja puesto de forma
   permanente: retirarlo exigiría `op.alter_column`, que SQLite no implementa
   (CLAUDE.md §6.11). No produce deriva detectable porque T4 no compara defaults
   de servidor: `_describir_esquema` recoge de cada columna solo nombre, tipo y
   nulabilidad, más los nombres de los índices.

2. **El `downgrade` usa `op.drop_column` plano, no `op.batch_alter_table`.**
   SQLite implementa `DROP COLUMN` de forma nativa desde 3.35.0 (el entorno de
   esta fase trae 3.49.1) siempre que la columna no sea clave primaria, ni única,
   ni esté indexada — `email_verificado` no es ninguna de las tres. El modo batch
   recrearía la tabla `usuario` completa, con su clave ajena y sus dos índices, y
   T4 **sí** compara los nombres de los índices: recrear la tabla es precisamente
   donde podrían derivar. La vía simple es aquí la vía segura.

3. **El backfill da por verificados a los usuarios preexistentes.** Son cuentas
   creadas por un superadmin o por el propietario de su organización, es decir,
   altas ya confiadas. Exigirles verificación dejaría fuera al administrador
   bootstrap y, con él, a cualquier instalación en marcha.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("email_verificado", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    # DML con la columna nombrada explícitamente (CLAUDE.md §6.10). El literal
    # `true` lo entienden tanto PostgreSQL como SQLite (≥ 3.23); un `1` sería
    # rechazado por PostgreSQL, que no convierte integer a boolean de forma
    # implícita en un UPDATE.
    op.execute("UPDATE usuario SET email_verificado = true")

    op.create_table(
        "token_consumido",
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("proposito", sa.String(length=24), nullable=False),
        sa.Column("consumido_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    # Sin índices adicionales a propósito: el único patrón de acceso es la
    # búsqueda por clave primaria (`jti`) al consumir un token, más la inserción.


def downgrade() -> None:
    op.drop_table("token_consumido")
    op.drop_column("usuario", "email_verificado")

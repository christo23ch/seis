"""Fase 14 — RGPD: consentimientos con versión y marca de borrado con gracia.

Dos cambios, ambos aditivos y ambos con `downgrade` real:

- `consentimiento`: una fila por consentimiento otorgado o negado, con la
  VERSIÓN del texto aceptado. Sin la versión, publicar una política nueva
  convertiría retroactivamente lo aceptado antes en un consentimiento a un texto
  que nadie leyó.
- `usuario.borrado_solicitado_en`: cuándo pidió el titular borrar su cuenta.
  Nulo mientras no lo pida. El borrado no ocurre aquí: ocurre al vencer la
  gracia de 14 días.

`batch_alter_table` para la columna nueva porque SQLite no admite ADD/DROP
CONSTRAINT y necesita recrear la tabla; en PostgreSQL emite el ALTER de siempre.
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consentimiento",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("usuario_id", sa.String(36),
                  sa.ForeignKey("usuario.id"), nullable=False, index=True),
        sa.Column("tipo", sa.String(32), nullable=False, index=True),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("otorgado", sa.Boolean(), nullable=False),
        sa.Column("otorgado_en", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("usuario") as batch:
        batch.add_column(sa.Column("borrado_solicitado_en",
                                   sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_usuario_borrado_solicitado_en", "usuario",
                    ["borrado_solicitado_en"])


def downgrade() -> None:
    op.drop_index("ix_usuario_borrado_solicitado_en", table_name="usuario")
    with op.batch_alter_table("usuario") as batch:
        batch.drop_column("borrado_solicitado_en")
    op.drop_table("consentimiento")

"""Fase 15 — onboarding: constancia de los pasos de arranque completados.

**Tabla propia, no una columna JSON en `usuario`.** La decisión está razonada en
el docstring de `models.PasoOnboarding`; lo que importa aquí es que por eso esta
migración crea una tabla con columnas tipadas y una restricción de unicidad, en
vez de añadir un campo sin esquema que ninguna migración podría validar después.

Solo se guardan las FINALIZACIONES. El catálogo de pasos vive en
`app/services/onboarding_service.py`, así que añadir un paso nuevo **no necesita
migración ni toca ninguna fila existente**.

Aditiva y con `downgrade` real.
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paso_onboarding",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("usuario_id", sa.String(36),
                  sa.ForeignKey("usuario.id"), nullable=False, index=True),
        sa.Column("clave", sa.String(32), nullable=False),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=False),
        # Marcar dos veces el mismo paso no crea una segunda fila: la unicidad lo
        # impide en la base, no solo en el servicio. Un servicio se puede
        # esquivar; una restricción no.
        sa.UniqueConstraint("usuario_id", "clave", name="uq_paso_onboarding_usuario_clave"),
    )


def downgrade() -> None:
    op.drop_table("paso_onboarding")

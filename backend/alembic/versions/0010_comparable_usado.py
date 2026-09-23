"""Fase 3 — trazabilidad de comparables: snapshot inmutable por análisis.

Responde de forma auditable "¿qué comparables concretos se utilizaron para
producir esta valoración?" — hoy los comparables solo sobreviven dentro del
JSON de `analisis.entrada`, sin ser consultables.

Snapshot, no referencia: no hay ninguna identidad estable de comparable a la
que apuntar (la tabla `comparable` es un catálogo huérfano y mutable —
`activo_flag` —, sin FK a `analisis`, y esta fase no la toca). Cada análisis
persiste su propia copia de los comparables que M03 recibió, en el mismo
orden, sin selección ni deduplicación: M03 usa el 100 % de lo que recibe
(`app/engine/modules/m03_valoracion.py`), así que el snapshot es fiel a eso.

Sin `UniqueConstraint`: dos comparables idénticos dentro del mismo análisis
son datos legítimos (el usuario los tecleó dos veces, M03 los pondera dos
veces) y deben conservarse como dos filas, no colapsarse.

Aditiva y con `downgrade` real. No toca ninguna tabla existente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comparable_usado",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analisis_id", sa.String(36),
                  sa.ForeignKey("analisis.id"), nullable=False, index=True),
        sa.Column("precio_m2", sa.Numeric(10, 2), nullable=False),
        sa.Column("estado", sa.String(16), nullable=False),
        sa.Column("origen", sa.String(24), nullable=False),
        sa.Column("meses_antiguedad", sa.Numeric(5, 1), nullable=False),
        sa.Column("superficie_m2", sa.Numeric(10, 2), nullable=True),
        sa.Column("orden", sa.SmallInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("comparable_usado")

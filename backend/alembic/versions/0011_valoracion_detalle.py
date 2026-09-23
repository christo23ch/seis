"""Fase 4 — trazabilidad de la valoración: intermedios de M03 que hoy se pierden.

Responde de forma auditable "¿cómo se obtuvo VM/VS a partir de estos
comparables?" — hoy solo se persisten los agregados finales (VM, VS, método),
dentro del JSON de `analisis.resultado`; los intermedios por comparable
(precio ajustado, normalizado, peso) y ciertos agregados sin columna propia
(el factor de estado aplicado, el ratio de sanidad, el VS desplazado por el
contraste de capitalización) son variables locales de `m03_valoracion.py`
que nunca salían de la función.

Dos tablas, ambas aditivas:

- `comparable_valorado`: snapshot 1:1 con `comparable_usado` (Fase 3, no
  modificada aquí). No lleva `UniqueConstraint`: el 1:1 lo garantiza el
  código que la puebla (`analisis_service.crear_analisis`), no el esquema —
  mismo criterio ya usado para `comparable_usado`, que tampoco la lleva.
- `valoracion_ajustes`: 1:1 con `analisis`, mismo patrón que `decision`
  (PK = analisis_id, sin id propio). No existe fila si el análisis fue
  `sin_comparables` (M03 no llega a calcular estos valores).

No modifica ninguna tabla existente. `downgrade` limpio: borra ambas, en
orden inverso a su creación por la FK de `comparable_valorado`.
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comparable_valorado",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analisis_id", sa.String(36),
                  sa.ForeignKey("analisis.id"), nullable=False, index=True),
        sa.Column("comparable_usado_id", sa.String(36),
                  sa.ForeignKey("comparable_usado.id"), nullable=False, index=True),
        sa.Column("precio_ajustado_m2", sa.Numeric(10, 2), nullable=False),
        sa.Column("normalizado_m2", sa.Numeric(10, 2), nullable=False),
        sa.Column("peso", sa.Numeric(6, 4), nullable=False),
    )
    op.create_table(
        "valoracion_ajustes",
        sa.Column("analisis_id", sa.String(36),
                  sa.ForeignKey("analisis.id"), primary_key=True),
        sa.Column("k_estado_activo", sa.Numeric(4, 2), nullable=False),
        sa.Column("ratio_sanidad", sa.Numeric(6, 4), nullable=False),
        sa.Column("vs_antes_de_capitalizacion", sa.Numeric(14, 2), nullable=True),
        sa.Column("vs_capitalizacion", sa.Numeric(14, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("comparable_valorado")
    op.drop_table("valoracion_ajustes")

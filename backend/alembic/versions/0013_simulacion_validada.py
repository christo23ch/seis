"""Fase 5E — `Analisis.simulacion_validada_id`: configuración actualmente
seleccionada para ese análisis.

Semántica (no cambia el motor ni el snapshot original):

    NULL  -> configuración actual = Analisis.entrada / Analisis.resultado
    UUID  -> configuración actual = Analisis.entrada / Simulacion.resultado

`Analisis.entrada` y `Analisis.resultado` NO se tocan: el análisis original
sigue siendo el snapshot inmutable de siempre (P1). Esta columna es solo un
puntero de selección; no crea un nuevo `Analisis` ni modifica ninguna
`Simulacion`.

FK a `simulacion.id` con `ondelete="SET NULL"`: si una futura fase permite
borrar físicamente una `Simulacion` actualmente seleccionada, el análisis
vuelve automáticamente a su configuración original en vez de quedar con una
referencia inválida — el borrado en sí no se implementa en esta migración.

Aditiva: una sola columna nueva sobre `analisis`, indexada. No se modifica
ninguna otra tabla ni columna existente (en particular, `simulacion` de la
migración 0012 no se toca). `downgrade` limpio: elimina la columna.
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analisis") as batch_op:
        batch_op.add_column(sa.Column("simulacion_validada_id", sa.String(36), nullable=True))
        batch_op.create_index(
            "ix_analisis_simulacion_validada_id", ["simulacion_validada_id"])
        batch_op.create_foreign_key(
            "fk_analisis_simulacion_validada_id", "simulacion",
            ["simulacion_validada_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("analisis") as batch_op:
        batch_op.drop_constraint("fk_analisis_simulacion_validada_id", type_="foreignkey")
        batch_op.drop_index("ix_analisis_simulacion_validada_id")
        batch_op.drop_column("simulacion_validada_id")

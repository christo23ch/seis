"""Fase 5F.1 — `Analisis.parametros_aplicados`: árbol T3 efectivo congelado
en el momento de crear el análisis (mismo snapshot que `Simulacion.parametros_aplicados`
desde la Fase 5D, aplicado ahora también a la configuración original).

Cierra parcialmente el hueco detectado en la auditoría 5F.0: los análisis
creados A PARTIR de esta migración conservan el árbol T3 exacto que recibió
el motor (incluida la fusión de `PerfilInversion`), en vez de depender de
`version_parametros` (ya demostrado insuficiente por sí solo).

Los análisis anteriores a esta migración quedan con `parametros_aplicados =
NULL` — deliberado, no reconstruible (auditoría 5F.0: ni `parametros_vigentes`
admite resolver "como estaba en el pasado", ni `PerfilInversion` conserva
historial). Sin `server_default` ni backfill: rellenar con `{}` o con
parámetros actuales falsificaría el snapshot histórico, y es exactamente lo
que esta migración evita.

Aditiva: una sola columna nueva sobre `analisis`, nullable, sin índice (no
hay necesidad de consultar por su contenido). No se modifica ninguna otra
tabla ni columna existente. `downgrade` limpio: elimina la columna.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_PORTABLE_JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("analisis", sa.Column("parametros_aplicados", _PORTABLE_JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("analisis", "parametros_aplicados")

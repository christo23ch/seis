"""Fase 5D — tabla `simulacion`: configuración alternativa de parámetros
aplicada a un `Analisis` ya existente, sin sobrescribirlo (P1).

`Analisis` 1:N `Simulacion` mediante `simulacion.analisis_id -> analisis.id`,
indexada. No se toca ninguna tabla existente — en particular NO se añade
`Analisis.simulacion_validada_id` (eso es Fase 5E, fuera de alcance).

`overrides`: solo los cambios introducidos por el usuario. `parametros_aplicados`:
el árbol COMPLETO de `Parametros.raw()` tras fusionar todas las capas reales
de `conocimiento_service.cargar_conocimiento()` y aplicar `overrides` — la
auditoría PRE-5D demostró que `version_parametros_base` por sí solo no basta
para reconstruir históricamente qué valores usó el motor (no refleja los
overrides de `PerfilInversion`), así que ambas columnas de versión quedan
como NULL-able y son solo contexto, nunca la fuente de reconstrucción.
`resultado`: el `AnalisisResult` íntegro, mismo contrato que `Analisis.resultado`.

`estado` es `String`, no un tipo `Enum` de base de datos — mismo patrón que
`Notificacion.estado` (`0005_esquema_base`): las transiciones válidas
(pendiente→descartada, pendiente→validada) las exige `simulacion_service`,
no el esquema.

Aditiva y con `downgrade` real. No modifica ninguna tabla existente.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_PORTABLE_JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "simulacion",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analisis_id", sa.String(36),
                  sa.ForeignKey("analisis.id"), nullable=False, index=True),
        sa.Column("estado", sa.String(12), nullable=False,
                  server_default="pendiente", index=True),
        sa.Column("overrides", _PORTABLE_JSON, nullable=False),
        sa.Column("parametros_aplicados", _PORTABLE_JSON, nullable=False),
        sa.Column("resultado", _PORTABLE_JSON, nullable=False),
        sa.Column("version_parametros_base", sa.String(16), nullable=True),
        sa.Column("version_reglas", sa.String(16), nullable=True),
        sa.Column("usuario", sa.String(120), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("fecha_validacion", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("simulacion")

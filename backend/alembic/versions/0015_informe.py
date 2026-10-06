"""Fase 5F.3 — tabla `informe`: snapshot histórico e inmutable de la
configuración que se convirtió en documento oficial.

`Analisis` 0..N `Informe`. El contenido (`entrada_snapshot`,
`parametros_aplicados`, `overrides`, `resultado`) se copia POR VALOR: un
informe no depende en lectura de `Analisis` ni de `Simulacion`, que son
mutables en su selección. El Markdown oficial viaja dentro de
`resultado["informe_markdown"]`, sin columna propia, para que no puedan
existir dos copias divergentes del mismo texto.

Dos decisiones de clave foránea, ambas deliberadas:

- `analisis_id` -> FK con `ondelete="RESTRICT"`. Nunca CASCADE: borrar un
  análisis no puede destruir documentos oficiales en silencio. Es seguro
  porque `Analisis` no se borra en ningún punto del código y la purga RGPD
  ya lo protege explícitamente (`purga_service`, condición `~hay_analisis`).

- `simulacion_id` -> SIN clave foránea, `String(36)` por valor, mismo patrón
  que `auditoria.entidad_id`. Con `ondelete="SET NULL"` el borrado futuro de
  una simulación no dejaría el dato ausente: lo reescribiría en una
  afirmación histórica FALSA, porque `NULL` ya significa «informe generado
  desde la configuración original». Sin FK, nada puede reescribirlo.

`parametros_aplicados` es nullable a propósito, con el mismo significado
estrecho que en `analisis`: `NULL` = el análisis de origen es anterior a la
migración 0014 y no tiene snapshot de parámetros (auditoría 5F.0). Nunca se
rellena con los parámetros actuales.

Sin `UniqueConstraint`: reemitir un informe sobre la misma configuración
meses después es un caso de uso legítimo, y una restricción lo impediría.
Sin columna de PDF: es un artefacto derivado, regenerable de forma
determinista desde el Markdown congelado.

Aditiva: una sola tabla nueva. No modifica ninguna tabla existente.
`downgrade` limpio.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_PORTABLE_JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "informe",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analisis_id", sa.String(36),
                  sa.ForeignKey("analisis.id", ondelete="RESTRICT"),
                  nullable=False, index=True),
        sa.Column("simulacion_id", sa.String(36), nullable=True, index=True),
        sa.Column("entrada_snapshot", _PORTABLE_JSON, nullable=False),
        sa.Column("parametros_aplicados", _PORTABLE_JSON, nullable=True),
        sa.Column("overrides", _PORTABLE_JSON, nullable=False),
        sa.Column("resultado", _PORTABLE_JSON, nullable=False),
        sa.Column("generado_por", sa.String(36), nullable=True),
        sa.Column("generado_en", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("informe")

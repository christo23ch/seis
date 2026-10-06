"""Fase 5J-1 — datos del procedimiento de subasta (ADR-0022).

Lo que el alta declara sobre el procedimiento, para los resultados informativos de
`app/engine/procedimiento.py`:

- `subasta.procedimiento`: judicial | aeat | tgss | notarial | extrajudicial |
  concursal | no_aplica.
- `subasta.regimen_judicial`: posterior | anterior | no_se (respecto del 3-4-2025,
  efectos de la LO 1/2025).
- `subasta.cantidad_reclamada`: importe que reclama el ejecutante, opcional.
- `activo.vivienda_habitual_ejecutado`: si | no | no_consta.

Aditiva: cuatro columnas anulables, sin `server_default` ni backfill. `NULL`
significa «fila anterior a esta migración» (o subasta captada sin ese dato), y así
debe seguir: rellenar con «no_consta» o con «no_se» afirmaría que el alta respondió
algo que nunca se preguntó. El motor ya trata la ausencia como dato ausente (P4).
La entrada completa de cada análisis sigue guardada en `analisis.entrada`.

`downgrade` limpio: elimina las cuatro columnas. `batch_alter_table` porque SQLite
no admite `DROP COLUMN` en todas las versiones (CLAUDE.md §6.11).
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("subasta") as tabla:
        tabla.add_column(sa.Column("procedimiento", sa.String(16), nullable=True))
        tabla.add_column(sa.Column("regimen_judicial", sa.String(10), nullable=True))
        tabla.add_column(sa.Column("cantidad_reclamada", sa.Numeric(14, 2), nullable=True))
    with op.batch_alter_table("activo") as tabla:
        tabla.add_column(sa.Column("vivienda_habitual_ejecutado", sa.String(10), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("activo") as tabla:
        tabla.drop_column("vivienda_habitual_ejecutado")
    with op.batch_alter_table("subasta") as tabla:
        tabla.drop_column("cantidad_reclamada")
        tabla.drop_column("regimen_judicial")
        tabla.drop_column("procedimiento")

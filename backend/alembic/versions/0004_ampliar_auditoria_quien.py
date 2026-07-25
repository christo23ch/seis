"""Cierre Fase 12 (P0.4) — Ampliar auditoria.quien a String(120).

`auditoria.quien` se creó como String(36) (pensada originalmente para un UUID),
pero desde el principio se le escriben emails (`usuario.email` es String(120)).
En PostgreSQL, un email de más de 36 caracteres aborta la transacción con
`22001 string_data_right_truncation`. Esta migración amplía la columna para
que coincida con la longitud real del dato que recibe.

Nota sobre el downgrade: reducir 120→36 es seguro solo si ninguna fila supera
36 caracteres. Con datos reales de producción eso puede no cumplirse; el
downgrade no trunca datos por seguridad — si existen valores más largos que
36 caracteres, PostgreSQL rechazará el ALTER y el operador deberá decidir
manualmente cómo tratar esas filas antes de revertir.
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("auditoria", "quien",
                    existing_type=sa.String(36), type_=sa.String(120))


def downgrade() -> None:
    op.alter_column("auditoria", "quien",
                    existing_type=sa.String(120), type_=sa.String(36))

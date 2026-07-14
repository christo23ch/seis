"""Esquema inicial SEIS (Fases 1–2): todas las tablas del §5.2 + usuario.

Revisión fundacional: crea el esquema completo desde los modelos declarativos.
Las revisiones posteriores se generan con `alembic revision --autogenerate`.
"""
from alembic import op

from app.core.db import Base
import app.models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

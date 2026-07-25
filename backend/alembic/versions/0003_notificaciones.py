"""Fase 12 — Notificaciones multicanal y scoring exprés.

Crea las tablas del subsistema de notificaciones:
- `preferencias_notificacion` (1:1 usuario): canales, modo, digest, silencio, telegram.
- `codigo_telegram`: códigos efímeros de vinculación (10 min, un solo uso).
- `alerta`: alertas de captación privadas por usuario (criterios JSON, incl. score_min).
- `notificacion`: cola de notificaciones (pendiente | enviada | error).

Idempotente por diseño (mismo criterio que 0002): tests e init_db crean el esquema
con `Base.metadata.create_all`, por lo que cada paso comprueba el estado real antes
de actuar. `downgrade` elimina las cuatro tablas.
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_TABLAS = ("notificacion", "alerta", "codigo_telegram", "preferencias_notificacion")


def _tiene_tabla(inspector, tabla: str) -> bool:
    return tabla in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _tiene_tabla(inspector, "preferencias_notificacion"):
        op.create_table(
            "preferencias_notificacion",
            sa.Column("usuario_id", sa.String(36),
                      sa.ForeignKey("usuario.id"), primary_key=True),
            sa.Column("canales", sa.JSON, nullable=False, default=list),
            sa.Column("modo", sa.String(16), nullable=False, server_default="instantaneo"),
            sa.Column("hora_digest", sa.SmallInteger, nullable=False, server_default="8"),
            sa.Column("silencio_inicio", sa.SmallInteger, nullable=True),
            sa.Column("silencio_fin", sa.SmallInteger, nullable=True),
            sa.Column("telegram_chat_id", sa.String(32), nullable=True),
            sa.Column("comunicaciones_activas", sa.Boolean,
                      nullable=False, server_default=sa.true()),
        )

    if not _tiene_tabla(inspector, "codigo_telegram"):
        op.create_table(
            "codigo_telegram",
            sa.Column("codigo", sa.String(6), primary_key=True),
            sa.Column("usuario_id", sa.String(36),
                      sa.ForeignKey("usuario.id"), nullable=False),
            sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
            sa.Column("usado", sa.Boolean, nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_codigo_telegram_usuario_id", "codigo_telegram", ["usuario_id"])

    if not _tiene_tabla(inspector, "alerta"):
        op.create_table(
            "alerta",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("usuario_id", sa.String(36),
                      sa.ForeignKey("usuario.id"), nullable=False),
            sa.Column("nombre", sa.String(120), nullable=False),
            sa.Column("criterios", sa.JSON, nullable=False, default=dict),
            sa.Column("activa", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("creado_en", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )
        op.create_index("ix_alerta_usuario_id", "alerta", ["usuario_id"])

    if not _tiene_tabla(inspector, "notificacion"):
        op.create_table(
            "notificacion",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("usuario_id", sa.String(36),
                      sa.ForeignKey("usuario.id"), nullable=False),
            sa.Column("alerta_id", sa.String(36), sa.ForeignKey("alerta.id"), nullable=True),
            sa.Column("asunto", sa.String(200), nullable=False),
            sa.Column("cuerpo", sa.Text, nullable=False),
            sa.Column("estado", sa.String(12), nullable=False, server_default="pendiente"),
            sa.Column("creado_en", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
            sa.Column("enviado_en", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_notificacion_usuario_id", "notificacion", ["usuario_id"])
        op.create_index("ix_notificacion_estado", "notificacion", ["estado"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for tabla in _TABLAS:
        if _tiene_tabla(inspector, tabla):
            op.drop_table(tabla)

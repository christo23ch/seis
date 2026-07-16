"""Fase 9 — Multi-tenancy por organización.

Introduce la tabla `organizacion` y el aislamiento por tenant:
- `usuario` += organizacion_id, rol_org, es_superadmin
- `analisis` += organizacion_id

Backfill reversible: crea una organización «por defecto», asigna a ella todos
los usuarios y análisis históricos, y promociona a los usuarios con rol=admin a
propietario + superadmin de plataforma (el admin bootstrap conserva su gobierno T2/T3).

Idempotente por diseño: la revisión fundacional 0001 crea el esquema con
`Base.metadata.create_all`, de modo que en una BD nueva las columnas/tablas ya
existen cuando corre esta migración. Por eso cada paso comprueba el estado real
del esquema (inspector) antes de actuar. Tests e init_db usan create_all directo,
no Alembic: esta migración es la vía de actualización de BD de producción.
"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _tiene_columna(inspector, tabla: str, columna: str) -> bool:
    return columna in {c["name"] for c in inspector.get_columns(tabla)}


def _tiene_tabla(inspector, tabla: str) -> bool:
    return tabla in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Tabla organizacion (solo si falta)
    if not _tiene_tabla(inspector, "organizacion"):
        op.create_table(
            "organizacion",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("nombre", sa.String(120), nullable=False),
            sa.Column("creado_en", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 2) Columnas nuevas en usuario
    if not _tiene_columna(inspector, "usuario", "organizacion_id"):
        op.add_column("usuario", sa.Column("organizacion_id", sa.String(36), nullable=True))
        op.create_index("ix_usuario_organizacion_id", "usuario", ["organizacion_id"])
    if not _tiene_columna(inspector, "usuario", "rol_org"):
        op.add_column("usuario", sa.Column("rol_org", sa.String(16),
                                           nullable=False, server_default="miembro"))
    if not _tiene_columna(inspector, "usuario", "es_superadmin"):
        op.add_column("usuario", sa.Column("es_superadmin", sa.Boolean,
                                           nullable=False, server_default=sa.false()))

    # 3) Columna nueva en analisis
    if not _tiene_columna(inspector, "analisis", "organizacion_id"):
        op.add_column("analisis", sa.Column("organizacion_id", sa.String(36), nullable=True))
        op.create_index("ix_analisis_organizacion_id", "analisis", ["organizacion_id"])

    # 4) Backfill: organización por defecto para todo lo histórico
    org_id = str(uuid.uuid4())
    org_default = bind.execute(
        sa.text("SELECT id FROM organizacion ORDER BY creado_en LIMIT 1")).first()
    if org_default is None:
        # `creado_en` es NOT NULL en el esquema real (Mapped[datetime] sin Optional,
        # y 0001 crea el esquema con Base.metadata.create_all de los modelos
        # actuales, no un snapshot congelado) — el server_default de la columna no
        # se aplica en un INSERT crudo por sa.text(), así que hay que darlo explícito.
        bind.execute(
            sa.text("INSERT INTO organizacion (id, nombre, creado_en) VALUES (:id, :nombre, :ahora)"),
            {"id": org_id, "nombre": "Organización por defecto",
             "ahora": datetime.now(timezone.utc)})
    else:
        org_id = org_default[0]

    bind.execute(sa.text(
        "UPDATE usuario SET organizacion_id = :org WHERE organizacion_id IS NULL"),
        {"org": org_id})
    bind.execute(sa.text(
        "UPDATE analisis SET organizacion_id = :org WHERE organizacion_id IS NULL"),
        {"org": org_id})

    # Los admin históricos gobiernan la plataforma y son propietarios de la org por defecto
    bind.execute(sa.text(
        "UPDATE usuario SET es_superadmin = :t, rol_org = 'propietario' WHERE rol = 'admin'"),
        {"t": True})


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _tiene_columna(inspector, "analisis", "organizacion_id"):
        op.drop_index("ix_analisis_organizacion_id", table_name="analisis")
        op.drop_column("analisis", "organizacion_id")

    for col, idx in (("organizacion_id", "ix_usuario_organizacion_id"),
                     ("rol_org", None), ("es_superadmin", None)):
        if _tiene_columna(inspector, "usuario", col):
            if idx:
                op.drop_index(idx, table_name="usuario")
            op.drop_column("usuario", col)

    if _tiene_tabla(inspector, "organizacion"):
        op.drop_table("organizacion")

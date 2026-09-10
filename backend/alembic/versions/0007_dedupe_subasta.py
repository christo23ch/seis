"""Fase 17-A — Unicidad de subasta por (fuente, identificador externo).

`docs/PENDIENTES.md` daba por hecho que «ya hay dedupe». No lo había:
`UniqueConstraint` estaba importado en `app/models.py` y no aplicado a ninguna
tabla. Sin esta restricción, reingerir el listado del BOE —que es lo que hará
una tarea diaria— duplicaría cada subasta en cada pasada.

Los NULL no colisionan entre sí en SQL, así que las altas manuales sin
identificador externo siguen siendo posibles y no se estorban. Es deliberado:
inventar una clave por aproximación (valor + fecha) uniría subastas
legítimamente distintas.

NO BORRA NADA. Si encuentra duplicados preexistentes, aborta listándolos: cuáles
son y qué hacer. Una migración que decide por su cuenta qué fila sobra es
exactamente lo que uno no quiere descubrir después.
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

NOMBRE = "uq_subasta_fuente_identificador"


def _duplicados(bind):
    return bind.execute(sa.text("""
        SELECT fuente_codigo, identificador_externo, COUNT(*) AS n
          FROM subasta
         WHERE identificador_externo IS NOT NULL
      GROUP BY fuente_codigo, identificador_externo
        HAVING COUNT(*) > 1
      ORDER BY n DESC
    """)).fetchall()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    ya_esta = any(c["name"] == NOMBRE
                  for c in inspector.get_unique_constraints("subasta"))
    if ya_esta:
        return

    filas = _duplicados(bind)
    if filas:
        detalle = "\n".join(
            f"  · fuente={f[0]!r} identificador={f[1]!r} → {f[2]} filas" for f in filas[:20])
        mas = f"\n  … y {len(filas) - 20} combinaciones más" if len(filas) > 20 else ""
        raise RuntimeError(
            "Migración 0007 abortada: hay subastas duplicadas y no voy a elegir yo "
            "cuál sobra.\n\n"
            f"{detalle}{mas}\n\n"
            "Revíselas y decida antes de reintentar. Para ver cada grupo entero:\n"
            "  SELECT id, creado_en, valor_subasta FROM subasta\n"
            "   WHERE fuente_codigo = '<fuente>' AND identificador_externo = '<id>'\n"
            "   ORDER BY creado_en;\n\n"
            "Lo habitual es conservar la más antigua, porque los análisis ya hechos "
            "cuelgan de ella. Compruébelo antes: borrar una subasta con análisis "
            "asociados rompe esa referencia.")

    # batch_alter_table: SQLite no admite ADD CONSTRAINT y necesita recrear la
    # tabla. En PostgreSQL emite el ALTER TABLE de siempre.
    with op.batch_alter_table("subasta") as batch:
        batch.create_unique_constraint(NOMBRE, ["fuente_codigo", "identificador_externo"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if any(c["name"] == NOMBRE for c in inspector.get_unique_constraints("subasta")):
        with op.batch_alter_table("subasta") as batch:
            batch.drop_constraint(NOMBRE, type_="unique")

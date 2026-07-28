"""Batería de tests de migraciones de Alembic — Fase 9.5.

Instrumento de medida de toda la fase: se calibró antes de usarse. Nació en
ROJO a propósito en el Bloque A, documentando dos bugs reales y verificados:
`alembic upgrade head` desde una base vacía fallaba en la revisión 0002
(INSERT crudo que omite `creado_en`, viola NOT NULL), y la 0004 tenía un bug
independiente (SQLite no soporta `ALTER TABLE ... ALTER COLUMN`).

El Bloque D retiró esa cadena y la sustituyó por la revisión fundacional
única 0005. T1, T2, T3 y T6 pasaron a verde **por reparación real**: no se
tocó ninguna aserción. Los mensajes de fallo siguen citando «Bloque A», la
0002 y la 0004 a propósito — el criterio de cierre del Bloque E congela el
texto de las aserciones de T1-T6 frente al commit `33bb28a` precisamente para
impedir que se ablanden mientras se repara la cadena. Ese anacronismo es la
prueba de que no se ablandaron.

T4 sigue en rojo por un defecto propio, no por deriva de esquema: compara el
resultado de `upgrade head` con el de `create_all` sin excluir
`alembic_version`. Su reparación corresponde al Bloque G.

Diseño (D-A, decidido): cada invocación de Alembic corre en un SUBPROCESO
propio, con `DATABASE_URL` fijada solo en el entorno de ese subproceso. Así
ni la caché de `get_settings()` ni el `engine` module-level de
`app.core.db` del proceso de pytest se ven afectados nunca — es la garantía
principal frente al riesgo destructivo (un `downgrade base` fuera de
control podría vaciar una base real).

Gate retirado (Bloque E): mientras la 0002 siguió rota, un
`pytestmark = pytest.mark.skipif(...)` sobre `SEIS_CALIBRAR_MIGRACIONES`
excluía este fichero de la invocación normal de `pytest`, para que unos
tests deliberadamente rojos no se confundieran con una regresión. Reparada
la cadena, esa línea se eliminó: la batería forma parte de la ejecución por
defecto de la suite.

T5 (verificación contra PostgreSQL real) se escribe en este bloque pero
queda en *skipped*: el plan canónico sitúa su primera ejecución real en el
Bloque F, no en el A — no es que falte infraestructura (Docker Desktop ya
está disponible), es una cuestión de secuenciación de fases.
"""
import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Inspector

from app.core.config import Settings

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------

RUTA_BACKEND = Path(__file__).resolve().parents[1]
RUTA_SEIS_DEV_DB = RUTA_BACKEND / "seis_dev.db"  # fichero compartido de la fixture `api`

POSTGRES_ENV_VAR = "SEIS_TEST_POSTGRES_URL"  # dedicada: nunca DATABASE_URL

# Tabla de contabilidad interna de Alembic: la crea el runtime al aplicar una
# revisión, nunca `Base.metadata.create_all`, de modo que su presencia en un
# lado y no en el otro es estructural y no es deriva. Coincide con el valor por
# defecto de `version_table`, que `alembic/env.py` no sobrescribe: si algún día
# lo hiciera, este nombre debe seguirlo. Es la ÚNICA exclusión de T4 (Bloque G).
TABLA_VERSION_ALEMBIC = "alembic_version"

# Mensajes exactos documentados por el Release Committee.
MENSAJE_ERROR_0002_INTEGRIDAD = "NOT NULL constraint failed: organizacion.creado_en"
MENSAJE_ERROR_0002_EXCEPCION = "IntegrityError"
MENSAJE_ERROR_0004_EXCEPCION = "OperationalError"
MENSAJE_ERROR_0004_SINTAXIS = 'near "ALTER"'

_URLS_SQLITE_PROHIBIDAS = frozenset({
    "sqlite:///./seis_dev.db",
    "sqlite:///seis_dev.db",
})


# --------------------------------------------------------------------------
# Descubrimiento de la cadena de revisiones
#
# T3 NO cita identificadores literales de revisión: los descubre en tiempo de
# recolección leyendo el directorio de scripts de Alembic. Es deliberado. La
# Fase 9.5 retira las revisiones 0001-0004 y las sustituye por una fundacional
# única (Bloque D); un T3 que las nombrara quedaría irreparable después, y el
# Bloque E exige que la batería se ponga verde SIN editar aserciones.
# --------------------------------------------------------------------------

def _cadena_de_revisiones() -> tuple[list[str], str | None]:
    """Cadena vigente de la más antigua a la cabeza, y motivo si no se pudo leer.

    **Nunca lanza.** Es deliberado y no es defensivo por costumbre: esta
    función se evalúa al IMPORTAR el módulo, de modo que ninguna marca de
    omisión puede protegerla —tampoco el gate que hubo hasta el Bloque E—, y
    una excepción aquí **abortaría la recolección de toda la suite**, no solo
    la de este fichero, porque pytest interrumpe la sesión entera ante un
    error de recolección. Cualquier problema degrada a cadena vacía con un
    motivo legible, y los tests de T3 se omiten explicándolo.

    Los dos escenarios que lo harían saltar son propios del Bloque D, que es
    justo el que esta batería debe sobrevivir: un instante con el directorio
    de revisiones vacío (borrar las cuatro antes de crear la fundacional) y
    un fichero de migración a medio editar, porque `walk_revisions()`
    **importa como módulo** cada fichero de `versions/`.

    Efecto lateral conocido: `ScriptDirectory.from_config()` aplica el
    `prepend_sys_path` de `alembic.ini` e inserta esa ruta en `sys.path`. No
    abre ninguna base de datos ni ejecuta `env.py`.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        configuracion = Config(str(RUTA_BACKEND / "alembic.ini"))
        configuracion.set_main_option("script_location", str(RUTA_BACKEND / "alembic"))
        guiones = ScriptDirectory.from_config(configuracion)

        cabezas = guiones.get_heads()
        if len(cabezas) > 1:
            # `walk_revisions()` no lanza ante una bifurcación: intercala las
            # ramas en una lista plana. Emparejarlas con `zip` produciría
            # pares que cruzan ramas sin relación real de `down_revision`.
            return [], (
                f"la cadena está bifurcada ({len(cabezas)} cabezas: "
                f"{', '.join(sorted(cabezas))}); T3 exige una cadena lineal"
            )

        cadena = [guion.revision for guion in reversed(list(guiones.walk_revisions()))]
        if not cadena:
            return [], "el directorio de revisiones está vacío"
        return cadena, None
    except Exception as error:  # degradar, jamás abortar la recolección global
        return [], f"{type(error).__name__}: {error}"


CADENA_REVISIONES, MOTIVO_SIN_CADENA = _cadena_de_revisiones()
REVISION_MAS_ANTIGUA = CADENA_REVISIONES[0] if CADENA_REVISIONES else None

# Pares (predecesora, revisión): solo las revisiones que tienen una anterior.
# Hoy son tres; tras el Bloque D, con una única revisión fundacional, la lista
# queda vacía y los tests parametrizados se saltan de forma explícita.
PARES_CONSECUTIVOS = list(zip(CADENA_REVISIONES, CADENA_REVISIONES[1:]))


def _motivo_de_omision() -> str:
    """Distingue «no hay nada que recorrer» de «no se pudo descubrir nada»."""
    if MOTIVO_SIN_CADENA:
        return (
            f"No se pudo descubrir la cadena de revisiones: {MOTIVO_SIN_CADENA}. "
            "T3 se omite en vez de abortar la recolección de la suite."
        )
    return (
        "La cadena vigente tiene una sola revisión (la fundacional): no hay "
        "pares consecutivos que recorrer. Estado esperado tras el Bloque D."
    )
_PARES_PARAM = PARES_CONSECUTIVOS or [(None, None)]
_PARES_IDS = [
    f"{anterior}-a-{posterior}" if anterior else "cadena-sin-pares"
    for anterior, posterior in _PARES_PARAM
]


# --------------------------------------------------------------------------
# Estructura de soporte
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EntornoMigraciones:
    """Entorno aislado para una invocación de Alembic en subproceso."""

    url: str
    env: dict[str, str]
    ruta_db: Path | None
    ruta_backend: Path


def _verificar_url_aislada(url: str, directorio_permitido: Path | None) -> None:
    """Guarda de aislamiento: aborta ANTES de tocar nada si `url` no es
    verificablemente desechable.

    No pretende ser una lista exhaustiva de todo lo peligroso: combina una
    lista de negación explícita (el fichero compartido con la fixture `api`,
    el valor por defecto de `Settings`) con una comprobación de contención
    real en el directorio desechable de la sesión de pytest en curso.
    """
    if not url:
        raise RuntimeError("Guarda de aislamiento: URL vacía.")

    if url in _URLS_SQLITE_PROHIBIDAS:
        raise RuntimeError(
            f"Guarda de aislamiento: {url!r} es el fichero compartido con la "
            "fixture `api` (conftest.py). Prohibido usarlo en tests de "
            "migraciones."
        )

    url_por_defecto = Settings.model_fields["database_url"].default
    if url == url_por_defecto:
        raise RuntimeError(
            f"Guarda de aislamiento: {url!r} coincide con el valor por "
            "defecto de Settings.database_url."
        )

    if url.startswith("sqlite:///"):
        if directorio_permitido is None:
            raise RuntimeError(
                "Guarda de aislamiento: URL sqlite sin directorio permitido "
                "con el que verificar la contención."
            )
        ruta = Path(url.removeprefix("sqlite:///")).resolve()
        directorio = directorio_permitido.resolve()
        try:
            ruta.relative_to(directorio)
        except ValueError as exc:
            raise RuntimeError(
                f"Guarda de aislamiento: {url!r} no cuelga del directorio "
                f"desechable esperado ({directorio})."
            ) from exc
        return

    if url.startswith("postgresql"):
        minusculas = url.lower()
        if "prod" in minusculas:
            raise RuntimeError(
                f"Guarda de aislamiento: {url!r} contiene «prod»: parece "
                "una base de producción, se rechaza."
            )
        if "test" not in minusculas:
            raise RuntimeError(
                f"Guarda de aislamiento: {url!r} no contiene un marcador de "
                "test reconocible en el nombre de la base."
            )
        return

    raise RuntimeError(f"Guarda de aislamiento: esquema de URL no soportado: {url!r}.")


def _ruta_db_desechable(directorio: Path) -> Path:
    """Ruta única, dentro de `directorio`, para un fichero SQLite desechable."""
    return directorio / f"mig_{uuid.uuid4().hex}.db"


def _url_desde_ruta(ruta_db: Path) -> str:
    return f"sqlite:///{ruta_db.as_posix()}"


def _estado_fichero(ruta: Path) -> tuple[int, int] | None:
    """Tamaño y mtime del fichero, o `None` si no existe. Base de la
    comprobación pasiva de que el fichero compartido no se tocó."""
    if not ruta.exists():
        return None
    estadisticas = ruta.stat()
    return (estadisticas.st_size, estadisticas.st_mtime_ns)


def _base_declarativa():
    """Importación perezosa de `Base` + modelos — mismo patrón que la
    fixture `api` de conftest.py: se difiere hasta que hace falta de verdad,
    en vez de forzarla al recolectar el módulo."""
    from app.core.db import Base
    import app.models  # noqa: F401  (registra todas las tablas)

    return Base


def _crear_esquema_via_create_all(entorno: EntornoMigraciones) -> None:
    """Crea el esquema completo directamente desde los modelos declarativos,
    sin pasar por Alembic. Bypass deliberado para alcanzar la 0004 sin la 0002
    (criterio de aceptación 4) y para la comparación de deriva de T4."""
    base = _base_declarativa()
    motor = sa.create_engine(entorno.url)
    try:
        base.metadata.create_all(motor)
    finally:
        motor.dispose()


def _describir_esquema(inspector: Inspector) -> dict[str, dict[str, list]]:
    """Descripción comparable de un esquema: tablas, columnas (nombre, tipo,
    nulabilidad) e índices, todo ordenado para que la comparación sea estable.

    Excluye `alembic_version` y **solo** esa tabla (Bloque G). No es un
    ablandamiento: la crea el runtime de Alembic al aplicar una revisión y
    `create_all` no la crea nunca, de modo que sin excluirla los dos lados
    difieren siempre y T4 no puede pasar jamás — una barrera que no puede
    ponerse verde no vigila nada. Excluida, la comparación sigue cubriendo el
    100 % del esquema de SEIS: 21 tablas, 171 columnas y 22 índices (medido).
    La prueba de mutación del Bloque G es la evidencia de que sigue detectando
    deriva en tablas, columnas, tipos, nulabilidad e índices.
    """
    descripcion: dict[str, dict[str, list]] = {}
    for tabla in sorted(inspector.get_table_names()):
        if tabla == TABLA_VERSION_ALEMBIC:
            continue
        columnas = sorted(
            (columna["name"], str(columna["type"]), bool(columna["nullable"]))
            for columna in inspector.get_columns(tabla)
        )
        indices = sorted(indice["name"] for indice in inspector.get_indexes(tabla))
        descripcion[tabla] = {"columnas": columnas, "indices": indices}
    return descripcion


def _cola(texto: str, n_lineas: int = 40) -> str:
    lineas = texto.splitlines()
    return "\n".join(lineas[-n_lineas:])


def _diagnostico(resultado: "subprocess.CompletedProcess[str]", etiqueta: str) -> str:
    """Mensaje autoexplicativo para incrustar en un `assert` fallido."""
    return (
        f"{etiqueta}\n"
        f"  returncode={resultado.returncode}\n"
        f"  stdout (últimas líneas):\n{_cola(resultado.stdout)}\n"
        f"  stderr (últimas líneas):\n{_cola(resultado.stderr)}"
    )


def _ejecutar_alembic(
    entorno: EntornoMigraciones, *args: str, tiempo_limite: int = 60
) -> "subprocess.CompletedProcess[str]":
    """Ejecuta `alembic <args>` en un subproceso aislado, contra `entorno.url`.

    Aislamiento total (D-A): proceso nuevo, sin la caché de `get_settings()`
    ni el `engine` module-level del proceso de pytest — `DATABASE_URL` solo
    existe en el entorno de este subproceso.
    """
    comando = [sys.executable, "-m", "alembic", "-c", "alembic.ini", *args]
    return subprocess.run(
        comando,
        cwd=entorno.ruta_backend,
        env=entorno.env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=tiempo_limite,
    )


@pytest.fixture
def entorno_migraciones(tmp_path: Path) -> Iterator[EntornoMigraciones]:
    """Entorno aislado por test: fichero SQLite desechable único bajo
    `tmp_path`, validado por la guarda de aislamiento.

    Comprobación pasiva FIRME (no opcional): captura el estado
    (existencia/tamaño/mtime) del fichero compartido `seis_dev.db` antes y
    después del test, y falla si cambió — es la evidencia de que el
    aislamiento se cumplió de hecho, no solo de que la URL parecía correcta.
    """
    ruta_db = _ruta_db_desechable(tmp_path)
    url = _url_desde_ruta(ruta_db)
    _verificar_url_aislada(url, tmp_path)

    estado_previo = _estado_fichero(RUTA_SEIS_DEV_DB)

    entorno_proceso = dict(os.environ)
    entorno_proceso["DATABASE_URL"] = url
    entorno_proceso["SEIS_ENV"] = "test"

    yield EntornoMigraciones(url=url, env=entorno_proceso, ruta_db=ruta_db, ruta_backend=RUTA_BACKEND)

    estado_posterior = _estado_fichero(RUTA_SEIS_DEV_DB)
    assert estado_posterior == estado_previo, (
        f"El fichero compartido {RUTA_SEIS_DEV_DB} cambió durante un test de "
        f"migraciones (antes={estado_previo}, después={estado_posterior}): "
        "el aislamiento no se cumplió de hecho."
    )


# --------------------------------------------------------------------------
# TG — guarda de aislamiento (criterio de aceptación 3)
# --------------------------------------------------------------------------

def test_tg_guarda_rechaza_url_del_fichero_compartido(tmp_path: Path) -> None:
    """La guarda debe saltar ante la URL del fichero que usa la fixture `api`."""
    with pytest.raises(RuntimeError):
        _verificar_url_aislada("sqlite:///./seis_dev.db", tmp_path)


def test_tg_guarda_rechaza_url_por_defecto_de_settings(tmp_path: Path) -> None:
    """La guarda debe saltar ante el valor por defecto de `Settings.database_url`."""
    url_por_defecto = Settings.model_fields["database_url"].default
    with pytest.raises(RuntimeError):
        _verificar_url_aislada(url_por_defecto, tmp_path)


def test_tg_guarda_rechaza_url_fuera_del_directorio_permitido(tmp_path: Path) -> None:
    """Una URL sqlite bien formada pero fuera del `tmp_path` esperado debe rechazarse."""
    otro_directorio = tmp_path / "fuera"
    otro_directorio.mkdir()
    url_fuera = _url_desde_ruta(tmp_path / "no_permitido.db")
    with pytest.raises(RuntimeError):
        _verificar_url_aislada(url_fuera, otro_directorio)


def test_tg_guarda_acepta_url_bien_formada_dentro_del_directorio(tmp_path: Path) -> None:
    """Caso positivo: una URL correctamente contenida no debe lanzar."""
    url_valida = _url_desde_ruta(_ruta_db_desechable(tmp_path))
    _verificar_url_aislada(url_valida, tmp_path)  # no debe lanzar


def test_tg_guarda_rechaza_url_postgres_que_parece_produccion(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        _verificar_url_aislada("postgresql://user:pass@prod-host/seis_prod", tmp_path)


def test_tg_guarda_acepta_url_postgres_con_marcador_de_test(tmp_path: Path) -> None:
    _verificar_url_aislada("postgresql://user:pass@localhost/seis_test", tmp_path)  # no debe lanzar


# --------------------------------------------------------------------------
# T1 — upgrade head desde base vacía
# --------------------------------------------------------------------------

def test_t1_upgrade_head_desde_base_vacia_termina_en_exito(
    entorno_migraciones: EntornoMigraciones,
) -> None:
    """T1 — `upgrade head` desde una base vacía debe terminar en éxito.

    Afirma el comportamiento CORRECTO, no el bug — esta es la aserción
    «final» del plan aprobado, no un estado intermedio a invertir más
    adelante. HOY (Bloque A) falla de verdad, porque el bug documentado de
    la 0002 es real: un `INSERT` crudo que omite `creado_en` viola
    `NOT NULL`. Cuando el Bloque E repare la migración, este test se pone en
    verde solo, sin tocar ni una línea aquí.
    """
    resultado = _ejecutar_alembic(entorno_migraciones, "upgrade", "head")
    diagnostico = _diagnostico(resultado, "T1 — upgrade head")

    assert resultado.returncode == 0, (
        "`upgrade head` desde una base vacía debería terminar en éxito. "
        f"Hoy (Bloque A) se espera que falle con: {MENSAJE_ERROR_0002_INTEGRIDAD!r} "
        f"({MENSAJE_ERROR_0002_EXCEPCION}) — el bug documentado de la 0002. "
        "Si el error no es ese, revisa si el arnés de pruebas está roto en "
        f"vez del código de producción.\n{diagnostico}"
    )


# --------------------------------------------------------------------------
# T2 — downgrade base tras T1
# --------------------------------------------------------------------------

def test_t2_downgrade_base_tras_upgrade_head(entorno_migraciones: EntornoMigraciones) -> None:
    """T2 — reversibilidad completa: `downgrade base` tras un `upgrade head`
    exitoso. Depende de que la fase previa tenga éxito; hoy no lo tiene, y se
    reporta como tal en vez de como una regresión distinta."""
    resultado_up = _ejecutar_alembic(entorno_migraciones, "upgrade", "head")
    if resultado_up.returncode != 0:
        pytest.fail(
            "T2 no puede evaluar la reversibilidad completa: el `upgrade "
            "head` de partida ya falló (ver T1) por el bug de la 0002.\n"
            + _diagnostico(resultado_up, "T2 — upgrade head (fase previa)")
        )

    resultado_down = _ejecutar_alembic(entorno_migraciones, "downgrade", "base")
    assert resultado_down.returncode == 0, _diagnostico(resultado_down, "T2 — downgrade base")

    motor = sa.create_engine(entorno_migraciones.url)
    try:
        tablas_restantes = set(sa.inspect(motor).get_table_names()) - {"alembic_version"}
        assert not tablas_restantes, (
            f"Tras `downgrade base` quedan tablas de aplicación: {tablas_restantes}"
        )
    finally:
        motor.dispose()


# --------------------------------------------------------------------------
# T3 — ida y vuelta por revisión, par a par
# --------------------------------------------------------------------------

def test_t3_control_del_arnes_sobre_la_revision_mas_antigua(
    entorno_migraciones: EntornoMigraciones,
) -> None:
    """T3 (1/3) — control del arnés (criterio de aceptación 5).

    Aplica y revierte **la revisión más antigua de la cadena**, descubierta
    en tiempo de recolección: hoy la que crea el esquema desde cero, cuyo
    `downgrade` lo destruye. No puede fallar por el bug de la 0002, que vive
    en una revisión posterior, así que DEBE salir en VERDE ya en el Bloque A
    usando la MISMA maquinaria de subproceso que T1. Si este test no sale
    verde, el problema está en el arnés (cwd, PYTHONPATH, DATABASE_URL,
    encoding) y no en las migraciones — y eso invalidaría a T1 como evidencia.

    Tras el Bloque D la cadena tendrá una sola revisión, la fundacional, y
    este test seguirá siendo válido sin tocar una línea.
    """
    if REVISION_MAS_ANTIGUA is None:
        pytest.skip(_motivo_de_omision())

    resultado_up = _ejecutar_alembic(entorno_migraciones, "upgrade", REVISION_MAS_ANTIGUA)
    assert resultado_up.returncode == 0, _diagnostico(
        resultado_up, f"T3 control — upgrade {REVISION_MAS_ANTIGUA}"
    )

    resultado_down = _ejecutar_alembic(entorno_migraciones, "downgrade", "base")
    assert resultado_down.returncode == 0, _diagnostico(
        resultado_down, "T3 control — downgrade base"
    )


@pytest.mark.parametrize(("predecesora", "revision"), _PARES_PARAM, ids=_PARES_IDS)
def test_t3_par_consecutivo_por_la_cadena_natural(
    predecesora: str | None,
    revision: str | None,
    entorno_migraciones: EntornoMigraciones,
) -> None:
    """T3 (2/3) — cada salto de la cadena, recorrido por su vía natural.

    Para cada par consecutivo, aplica primero la predecesora y después la
    revisión bajo prueba. Afirma el comportamiento CORRECTO de cada salto, no
    el bug. Hoy (Bloque A) falla en el salto que introduce el defecto
    documentado, lo que localiza el fallo en una revisión concreta y no en la
    cadena entera.

    Los identificadores se descubren de la cadena vigente: tras el Bloque D
    no habrá pares consecutivos y el test se saltará de forma explícita.
    """
    if revision is None or predecesora is None:
        pytest.skip(_motivo_de_omision())

    resultado_previo = _ejecutar_alembic(entorno_migraciones, "upgrade", predecesora)
    assert resultado_previo.returncode == 0, _diagnostico(
        resultado_previo, f"T3 par({revision}) — upgrade {predecesora} previo"
    )

    resultado = _ejecutar_alembic(entorno_migraciones, "upgrade", revision)
    diagnostico = _diagnostico(resultado, f"T3 par({revision}) — upgrade {revision}")
    assert resultado.returncode == 0, (
        f"`upgrade {revision}` (sobre una base ya en {predecesora}) debería "
        "terminar en éxito. Hoy (Bloque A) se espera que uno de estos saltos "
        f"falle con: {MENSAJE_ERROR_0002_INTEGRIDAD!r} "
        f"({MENSAJE_ERROR_0002_EXCEPCION}).\n{diagnostico}"
    )


@pytest.mark.parametrize(("predecesora", "revision"), _PARES_PARAM, ids=_PARES_IDS)
def test_t3_revision_aislada_via_stamp(
    predecesora: str | None,
    revision: str | None,
    entorno_migraciones: EntornoMigraciones,
) -> None:
    """T3 (3/3) — cada revisión aislada de las anteriores (criterio 4).

    Aísla estructuralmente cada revisión: crea el esquema con
    `Base.metadata.create_all` (bypass total de Alembic), marca la
    predecesora con `alembic stamp` —que escribe `alembic_version` sin
    ejecutar DDL alguna— y solo entonces aplica la revisión bajo prueba. El
    código Python de las revisiones anteriores **no llega a ejecutarse
    nunca**, de modo que un fallo aquí es atribuible ÚNICAMENTE a la revisión
    parametrizada.

    Esto es lo que demuestra que las causas son ortogonales y no
    consecutivas: hoy (Bloque A) fallan dos revisiones distintas por dos
    motivos de motor distintos, cada una alcanzada sin pasar por la otra.

    Los identificadores se descubren de la cadena vigente: tras el Bloque D
    no habrá revisiones con predecesora y el test se saltará de forma
    explícita.
    """
    if revision is None or predecesora is None:
        pytest.skip(_motivo_de_omision())

    _crear_esquema_via_create_all(entorno_migraciones)

    resultado_stamp = _ejecutar_alembic(entorno_migraciones, "stamp", predecesora)
    assert resultado_stamp.returncode == 0, _diagnostico(
        resultado_stamp, f"T3 aislada({revision}) — stamp {predecesora}"
    )

    resultado = _ejecutar_alembic(entorno_migraciones, "upgrade", revision)
    diagnostico = _diagnostico(resultado, f"T3 aislada({revision}) — upgrade {revision}")
    assert resultado.returncode == 0, (
        f"`upgrade {revision}` (alcanzada vía `stamp {predecesora}` sobre un "
        "esquema creado con `create_all`, sin ejecutar el código Python de "
        "ninguna revisión anterior) debería terminar en éxito. Su fallo es "
        "atribuible ÚNICAMENTE a esta revisión. Hoy (Bloque A) se esperan dos "
        f"fallos en esta familia, por causas ortogonales entre sí: "
        f"{MENSAJE_ERROR_0002_INTEGRIDAD!r} ({MENSAJE_ERROR_0002_EXCEPCION}) y "
        f"{MENSAJE_ERROR_0004_SINTAXIS!r} ({MENSAJE_ERROR_0004_EXCEPCION})."
        f"\n{diagnostico}"
    )


# --------------------------------------------------------------------------
# T4 — deriva de esquema (barrera anti-recurrencia)
# --------------------------------------------------------------------------

def test_t4_deriva_de_esquema_upgrade_head_vs_create_all(
    entorno_migraciones: EntornoMigraciones, tmp_path: Path
) -> None:
    """T4 — compara el esquema de `upgrade head` con el de
    `Base.metadata.create_all` (tablas, columnas, tipos, nulabilidad,
    índices). Si difieren, hay deriva entre migraciones y modelos.

    Si la fase previa (`upgrade head`) falla, se reporta como tal sin intentar
    comparar nada, para no generar un segundo mensaje desconectado del real.
    El texto de esa llamada a `pytest.fail` sigue citando el bug de la 0002
    porque el criterio de cierre del Bloque E congela el texto de las
    aserciones de T1-T6; el Bloque G corrigió la comparación sin tocar una
    sola línea de aserción.

    Alcance del motor: ambos lados son SQLite desechables, así que aquí no
    aparece ningún objeto de extensión (medido: cero). El ruido de PostGIS que
    sí afecta a `alembic check` es otra barrera distinta y otro bloque.
    """
    resultado_up = _ejecutar_alembic(entorno_migraciones, "upgrade", "head")
    if resultado_up.returncode != 0:
        pytest.fail(
            "T4 no puede comparar esquemas: `upgrade head` ya falló (ver "
            "T1) por el bug de la 0002.\n"
            + _diagnostico(resultado_up, "T4 — upgrade head (fase previa)")
        )

    url_create_all = _url_desde_ruta(_ruta_db_desechable(tmp_path))
    _verificar_url_aislada(url_create_all, tmp_path)
    entorno_create_all = EntornoMigraciones(
        url=url_create_all, env={}, ruta_db=None, ruta_backend=RUTA_BACKEND
    )

    motor_create_all = sa.create_engine(url_create_all)
    try:
        _crear_esquema_via_create_all(entorno_create_all)
        esquema_create_all = _describir_esquema(sa.inspect(motor_create_all))
    finally:
        motor_create_all.dispose()

    motor_alembic = sa.create_engine(entorno_migraciones.url)
    try:
        esquema_alembic = _describir_esquema(sa.inspect(motor_alembic))
    finally:
        motor_alembic.dispose()

    assert esquema_alembic == esquema_create_all, (
        "Deriva detectada entre el esquema de `upgrade head` y el de "
        "`Base.metadata.create_all`:\n"
        f"  solo en upgrade head: {esquema_alembic.keys() - esquema_create_all.keys()}\n"
        f"  solo en create_all:   {esquema_create_all.keys() - esquema_alembic.keys()}"
    )


# --------------------------------------------------------------------------
# T5 — contra PostgreSQL real (Bloque F, no Bloque A)
# --------------------------------------------------------------------------

@pytest.mark.postgres
@pytest.mark.skipif(
    not os.environ.get(POSTGRES_ENV_VAR),
    reason=(
        "T5 exige un PostgreSQL real. Se ejecutó y pasó en el Bloque F contra "
        "postgis/postgis:16-3.4 (PostgreSQL 16.4); aquí se omite únicamente "
        f"porque {POSTGRES_ENV_VAR} no está definida. Definirla apuntando a "
        "una base desechable cuyo nombre contenga «test» para volver a "
        "ejecutarla."
    ),
)
def test_t5_upgrade_head_y_downgrade_base_contra_postgres_real() -> None:
    """T5 — réplica de T1+T2 contra PostgreSQL real.

    La URL se toma de una variable de entorno DEDICADA
    (`SEIS_TEST_POSTGRES_URL`), nunca de `DATABASE_URL`, para que un valor
    de producción exportado por accidente en el shell del desarrollador no
    pueda colarse aquí jamás.

    Nota de alcance: la comparación de deriva completa (equivalente a T4)
    contra Postgres requiere poder crear una segunda base de datos
    desechable en el mismo servidor; esa infraestructura se añade en el
    Bloque F, cuando el test se ejecute por primera vez de verdad — construir
    ahora ese mecanismo sin poder ejecutarlo sería código no verificado.
    """
    url = os.environ[POSTGRES_ENV_VAR]
    _verificar_url_aislada(url, directorio_permitido=None)

    entorno_proceso = dict(os.environ)
    entorno_proceso["DATABASE_URL"] = url
    entorno_proceso["SEIS_ENV"] = "test"
    entorno = EntornoMigraciones(url=url, env=entorno_proceso, ruta_db=None, ruta_backend=RUTA_BACKEND)

    resultado_up = _ejecutar_alembic(entorno, "upgrade", "head")
    assert resultado_up.returncode == 0, _diagnostico(resultado_up, "T5 — upgrade head (Postgres)")

    motor = sa.create_engine(url)
    try:
        assert "organizacion" in sa.inspect(motor).get_table_names()
    finally:
        motor.dispose()

    resultado_down = _ejecutar_alembic(entorno, "downgrade", "base")
    assert resultado_down.returncode == 0, _diagnostico(resultado_down, "T5 — downgrade base (Postgres)")


# --------------------------------------------------------------------------
# T6 — idempotencia
# --------------------------------------------------------------------------

def test_t6_upgrade_head_dos_veces_es_idempotente(
    entorno_migraciones: EntornoMigraciones,
) -> None:
    """T6 — idempotencia: aplicar `upgrade head` dos veces sobre el mismo
    fichero debe terminar en éxito las dos veces (la segunda es un no-op).

    Afirma el objetivo final siempre, no el estado actual — sin rama
    condicional que se adapte a si la migración ya está reparada o no. Hoy
    (Bloque A) la primera aplicación ya falla por el bug de la 0002 (ver
    T1), así que la primera aserción es la que falla aquí. Cuando el
    Bloque E repare la cadena, este test confirma además que repetir
    `upgrade head` sobre una base que ya está en `head` no revienta.
    """
    primero = _ejecutar_alembic(entorno_migraciones, "upgrade", "head")
    segundo = _ejecutar_alembic(entorno_migraciones, "upgrade", "head")

    diagnostico_primero = _diagnostico(primero, "T6 — primera upgrade head")
    assert primero.returncode == 0, (
        "La primera `upgrade head` debería terminar en éxito. Hoy "
        f"(Bloque A) se espera que falle con: {MENSAJE_ERROR_0002_INTEGRIDAD!r} "
        f"({MENSAJE_ERROR_0002_EXCEPCION}) — el bug documentado de la "
        f"0002.\n{diagnostico_primero}"
    )

    diagnostico_segundo = _diagnostico(segundo, "T6 — segunda upgrade head")
    assert segundo.returncode == 0, (
        "La segunda `upgrade head` (sobre un fichero que ya está en head) "
        f"debería ser un no-op exitoso.\n{diagnostico_segundo}"
    )

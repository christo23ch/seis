"""Fase 5D — servicio de simulaciones: configuraciones alternativas aplicadas
a un `Analisis` ya existente, sin sobrescribirlo (P1).

Flujo de `crear_simulacion`:

    Analisis.entrada
        → AnalisisInput (lossless, verificado en la auditoría PRE-5D)
        → conocimiento_service.cargar_conocimiento(db)   (UNA sola vez)
        → validación de overrides contra el catálogo (autoridad de editabilidad)
        → Parametros.con_overrides(overrides)             (aislado, no muta nada global)
        → ejecutar_analisis(...)                           (pipeline M01-M14 completo)
        → Simulacion (snapshot íntegro de lo aplicado + resultado)

No hay recalculo parcial ni una versión alternativa del motor: se reutiliza
`ejecutar_analisis` exactamente como lo hace `analisis_service.simular`.

Fase 5E — añade la CONFIGURACIÓN ACTUAL (`Analisis.simulacion_validada_id`):

    NULL  -> configuración actual = Analisis.entrada / Analisis.resultado
    UUID  -> configuración actual = Analisis.entrada / Simulacion.resultado

`Analisis.entrada` NUNCA cambia de fuente: el inmueble sigue siendo el del
análisis original, se seleccione la configuración que se seleccione — solo
cambia de dónde sale `resultado` (M01-M14 no se re-ejecuta al seleccionar).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import models
from app.engine.contracts import AnalisisInput
from app.engine.pipeline import ejecutar_analisis
from app.parametros import catalogo
from app.services import auditoria_service, conocimiento_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json(obj) -> dict:
    return json.loads(obj.model_dump_json())


# ─────────────────────────── errores explícitos ───────────────────────────

class SimulacionError(Exception):
    """Base de los errores del servicio de simulación (Fase 5D)."""


class AnalisisNoEncontradoError(SimulacionError):
    def __init__(self, analisis_id: str):
        super().__init__(f"Análisis no encontrado: {analisis_id}")
        self.analisis_id = analisis_id


class SimulacionNoEncontradaError(SimulacionError):
    def __init__(self, simulacion_id: str):
        super().__init__(f"Simulación no encontrada: {simulacion_id}")
        self.simulacion_id = simulacion_id


class PertenenciaCruzadaError(SimulacionError):
    """La simulación existe pero no pertenece al `analisis_id` indicado."""

    def __init__(self, simulacion_id: str, analisis_id: str):
        super().__init__(
            f"La simulación {simulacion_id} no pertenece al análisis {analisis_id}")
        self.simulacion_id = simulacion_id
        self.analisis_id = analisis_id


class ReconstruccionInvalidaError(SimulacionError):
    """`Analisis.entrada` no reconstruye un `AnalisisInput` válido."""


class OverrideInvalidoError(SimulacionError):
    def __init__(self, clave: str, motivo: str):
        super().__init__(f"Override inválido para '{clave}': {motivo}")
        self.clave = clave
        self.motivo = motivo


class TransicionInvalidaError(SimulacionError):
    def __init__(self, estado_actual: str, estado_destino: str):
        super().__init__(f"Transición no permitida: {estado_actual} → {estado_destino}")
        self.estado_actual = estado_actual
        self.estado_destino = estado_destino


# ─────────────────────────── reconstrucción (Paso 3) ───────────────────────────

def _reconstruir_input(analisis: models.Analisis) -> AnalisisInput:
    """`AnalisisInput(**analisis.entrada)` — verificado lossless en la
    auditoría PRE-5D (fechas, opcionales, listas, anidados, negativos, ceros).
    Sin tratamiento especial: si el snapshot histórico es inválido, falla
    explícito en vez de intentar corregirlo o crear una simulación falsa.
    """
    try:
        return AnalisisInput(**analisis.entrada)
    except ValidationError as exc:
        raise ReconstruccionInvalidaError(
            f"Analisis.entrada de '{analisis.id}' no reconstruye un AnalisisInput "
            f"válido: {exc}"
        ) from exc


# ─────────────────────────── validación de overrides (Paso 4) ───────────────────────────

def _validar_overrides(overrides: dict[str, object], params_base) -> None:
    """El catálogo es la única autoridad de editabilidad (Fase 5C/5C.1).

    Acepta: claves T1 fijas editables, o instancias YA resueltas de una
    plantilla contra `params_base` (p.ej. 'perfiles.flip_ligero.rvc_veto').
    Rechaza, con el mismo mecanismo — sin código especial por caso — los
    hardcodes (TIPO 2), los cálculos derivados (TIPO 3, no tienen clave T3),
    los datos de entrada (TIPO 4, nunca catalogados), las claves inexistentes
    y los patrones sin resolver ('perfiles.{perfil}.rvc_veto' literal, que no
    coincide con ninguna instancia real).

    Fase 5F.7.1: aceptada la clave, se comprueba además la FORMA del valor
    contra el valor de referencia del mismo árbol (`_discrepancia_de_forma`).
    Sin esto, un valor mal formado llegaba al motor y reventaba con
    `TypeError` (HTTP 500) o se aceptaba en silencio.
    """
    hardcodes = {p.clave for p in catalogo.CONSTANTES_HARDCODE}
    editables_fijos = {p.clave for p in catalogo.obtener_parametros_editables()}
    resueltos = {r.clave for r in catalogo.resolver_plantillas(params_base)}

    for clave, valor in overrides.items():
        if clave in hardcodes:
            raise OverrideInvalidoError(
                clave, "es una constante hardcodeada (TIPO 2, catalogo.py), no editable")
        if clave not in editables_fijos and clave not in resueltos:
            raise OverrideInvalidoError(
                clave,
                "no está catalogado como parámetro T3 editable — no existe, es un "
                "cálculo derivado, un dato de entrada, o un patrón de plantilla "
                "sin resolver contra una instancia real")
        motivo = _discrepancia_de_forma(valor, params_base.get(clave))
        if motivo is not None:
            raise OverrideInvalidoError(clave, motivo)


def _es_numero(v: object) -> bool:
    # `bool` es subclase de `int` en Python: sin excluirlo, `true` pasaría por número.
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nombre_forma(v: object) -> str:
    if v is None:
        return "nulo"
    if isinstance(v, bool):
        return "un booleano"
    if _es_numero(v):
        return "un número"
    if isinstance(v, str):
        return "un texto"
    if isinstance(v, list):
        return "una lista"
    if isinstance(v, dict):
        return "un objeto"
    return type(v).__name__


def _discrepancia_de_forma(valor: object, referencia: object, ruta: str = "") -> str | None:
    """`None` si `valor` tiene la misma FORMA que `referencia`; si no, el motivo.

    Solo forma, nunca validez de negocio: ni rangos, ni sumas, ni orden de
    tramos, ni longitud de listas, ni coherencia entre parámetros. Un `int`
    vale donde la referencia es `float` y viceversa; un número debe ser finito
    (el parser JSON de Python acepta `NaN` e `Infinity`). Una lista se compara
    elemento a elemento con la forma de `referencia[0]` (cualquier lista si la
    referencia está vacía); un objeto, con EXACTAMENTE las mismas claves.
    `ruta` localiza el fallo dentro de una estructura, p. ej. `[0].max`.
    """
    donde = f"en '{ruta}': " if ruta else ""

    if isinstance(referencia, list):
        if not isinstance(valor, list):
            return f"{donde}se esperaba una lista y se recibió {_nombre_forma(valor)}"
        if referencia:
            for i, elemento in enumerate(valor):
                motivo = _discrepancia_de_forma(elemento, referencia[0], f"{ruta}[{i}]")
                if motivo is not None:
                    return motivo
        return None

    if isinstance(referencia, dict):
        if not isinstance(valor, dict):
            return f"{donde}se esperaba un objeto y se recibió {_nombre_forma(valor)}"
        faltan = sorted(str(k) for k in referencia.keys() - valor.keys())
        sobran = sorted(str(k) for k in valor.keys() - referencia.keys())
        if faltan or sobran:
            return (f"{donde}el objeto debe tener exactamente las claves "
                    f"{sorted(str(k) for k in referencia)} (faltan {faltan}, sobran {sobran})")
        for k, sub_referencia in referencia.items():
            motivo = _discrepancia_de_forma(valor[k], sub_referencia,
                                            f"{ruta}.{k}" if ruta else str(k))
            if motivo is not None:
                return motivo
        return None

    if _es_numero(referencia):
        if not _es_numero(valor):
            return f"{donde}se esperaba un número y se recibió {_nombre_forma(valor)}"
        if not math.isfinite(valor):
            return f"{donde}el número debe ser finito y se recibió {valor!r}"
        return None

    if isinstance(referencia, bool):
        coincide = isinstance(valor, bool)
    elif referencia is None:
        coincide = valor is None
    else:
        coincide = isinstance(valor, type(referencia))
    if coincide:
        return None
    return f"{donde}se esperaba {_nombre_forma(referencia)} y se recibió {_nombre_forma(valor)}"


# ─────────────────────────── API del servicio (Paso 11) ───────────────────────────
#
# Fase 5F.6 — auditoría. Cada escritura es UNA SOLA transacción:
#
#     try:
#         modificación de negocio
#         auditoria_service.auditar(...)
#         db.commit()                      # el único commit
#     except Exception:
#         db.rollback()                    # deshace modificación Y auditoría
#         raise
#
# Mismo patrón que `informe_service.generar_informe_oficial`. Sin el
# `rollback` explícito, un fallo de `auditar` dejaría la modificación
# pendiente en una sesión abierta que un `commit` posterior del llamador
# confirmaría sin su evento (defecto B-1, Fase 5F.3.1). `delta` lleva solo
# identificadores técnicos: `auditar` veta cualquier dato con forma de correo
# ahí, y el actor tiene su sitio en `quien`.

def crear_simulacion(db: Session, analisis_id: str,
                     overrides: dict[str, object] | None = None,
                     usuario: str | None = None, *,
                     quien: str | None = None) -> models.Simulacion:
    """Crea y ejecuta una simulación completa sobre un `Analisis` existente.

    Atómico: toda la reconstrucción/validación/ejecución ocurre en memoria
    antes de tocar la sesión; solo se hace `db.add` cuando ya hay un
    resultado completo que persistir, así que un fallo en cualquier paso
    anterior no deja fila alguna a medio crear ni toca `Analisis`.

    Fase 5F.6: la simulación y su auditoría (`quien` = actor legible) se
    confirman juntas. En `delta` va el NÚMERO de overrides, nunca sus valores:
    los escribe el usuario y podrían tener forma de correo.
    """
    analisis = db.get(models.Analisis, analisis_id)
    if analisis is None:
        raise AnalisisNoEncontradoError(analisis_id)

    overrides = dict(overrides or {})

    inp = _reconstruir_input(analisis)

    params_base, reglas, version_reglas = conocimiento_service.cargar_conocimiento(db)
    _validar_overrides(overrides, params_base)

    params_aplicados = params_base.con_overrides(overrides)

    resultado = ejecutar_analisis(inp, params=params_aplicados, reglas=reglas,
                                  version_reglas=version_reglas)

    sim = models.Simulacion(
        analisis_id=analisis.id,
        estado="pendiente",
        overrides=overrides,
        parametros_aplicados=params_aplicados.raw(),
        resultado=_json(resultado),
        version_parametros_base=params_aplicados.version,
        version_reglas=version_reglas,
        usuario=usuario,
    )
    try:
        db.add(sim)
        db.flush()      # asigna el id sin confirmar, para referenciarlo desde la auditoría
        auditoria_service.auditar(
            db, quien=quien, entidad="simulacion", entidad_id=sim.id, accion="crear",
            delta={"analisis_id": analisis.id, "n_overrides": len(overrides)})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sim)
    return sim


def _verificar_pertenencia(sim: models.Simulacion, analisis_id: str) -> None:
    if sim.analisis_id != analisis_id:
        raise PertenenciaCruzadaError(sim.id, analisis_id)


def _obtener_simulacion_de_analisis(db: Session, analisis_id: str,
                                    simulacion_id: str) -> models.Simulacion:
    if db.get(models.Analisis, analisis_id) is None:
        raise AnalisisNoEncontradoError(analisis_id)
    sim = db.get(models.Simulacion, simulacion_id)
    if sim is None:
        raise SimulacionNoEncontradaError(simulacion_id)
    _verificar_pertenencia(sim, analisis_id)
    return sim


# ─────────────────────────── lectura (Fase 5F.6) ───────────────────────────

def listar_simulaciones(db: Session, analisis_id: str) -> list[models.Simulacion]:
    """Simulaciones de un análisis, de la más reciente a la más antigua.

    Consulta directa sobre la tabla: no ejecuta el motor, no lee parámetros
    vigentes y no modifica nada. Filtra estrictamente por `analisis_id`, así
    que nunca puede colarse una simulación de otro análisis. Sin paginación,
    mismo criterio que `informe_service.listar_informes`: están acotadas a un
    análisis. El aislamiento por organización lo aplica el llamador.
    """
    return (db.query(models.Simulacion)
            .filter(models.Simulacion.analisis_id == analisis_id)
            .order_by(models.Simulacion.creado_en.desc())
            .all())


def obtener_simulacion(db: Session, analisis_id: str,
                       simulacion_id: str) -> models.Simulacion:
    """Una simulación concreta, comprobando que pertenece a ese análisis.

    Inexistente y ajena lanzan el MISMO `SimulacionNoEncontradaError`, a
    diferencia de las escrituras (`PertenenciaCruzadaError`): en una lectura,
    distinguirlas permitiría confirmar la existencia de una simulación de otro
    análisis. Mismo criterio que `informe_service.obtener_informe`.
    """
    try:
        return _obtener_simulacion_de_analisis(db, analisis_id, simulacion_id)
    except PertenenciaCruzadaError:
        raise SimulacionNoEncontradaError(simulacion_id) from None


def _analisis_bloqueado(db: Session, analisis_id: str) -> models.Analisis:
    """Carga `Analisis` con bloqueo pesimista (`with_for_update`), mismo
    patrón ya usado en `cuenta_service.py`/`purga_service.py` — sin
    `skip_locked` (a diferencia de esos dos, aquí sí queremos ESPERAR el
    bloqueo, no saltarnos la fila): dos operaciones concurrentes que
    seleccionan configuración para el mismo análisis deben serializarse, no
    competir. Ignorado por SQLite (tests/dev), efectivo en PostgreSQL.
    """
    analisis = (db.query(models.Analisis)
               .filter(models.Analisis.id == analisis_id)
               .with_for_update()
               .one_or_none())
    if analisis is None:
        raise AnalisisNoEncontradoError(analisis_id)
    return analisis


def validar_simulacion(db: Session, analisis_id: str, simulacion_id: str, *,
                       quien: str | None = None) -> models.Simulacion:
    """pendiente → validada, Y la fija como configuración actual — ambos
    cambios en la MISMA transacción (un único `db.commit()`), mismo patrón
    de unidad-de-trabajo que ya usa `analisis_service.crear_analisis` con
    sus siete tipos de filas hijas. Nunca puede quedar `Simulacion.estado
    == "validada"` sin que `Analisis.simulacion_validada_id` apunte a ella
    como consecuencia de esta llamada.

    No toca `Analisis.entrada` ni `Analisis.resultado` ni `Simulacion.resultado`.
    No implica ningún juicio sobre la decisión del motor (P6): una
    configuración `rojo` puede validarse exactamente igual que una `verde`.
    """
    analisis = _analisis_bloqueado(db, analisis_id)
    sim = db.get(models.Simulacion, simulacion_id)
    if sim is None:
        raise SimulacionNoEncontradaError(simulacion_id)
    _verificar_pertenencia(sim, analisis_id)
    if sim.estado != "pendiente":
        raise TransicionInvalidaError(sim.estado, "validada")

    try:
        sim.estado = "validada"
        sim.fecha_validacion = _now()
        analisis.simulacion_validada_id = sim.id
        auditoria_service.auditar(db, quien=quien, entidad="simulacion", entidad_id=sim.id,
                                  accion="validar", delta={"analisis_id": analisis_id})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sim)
    return sim


def descartar_simulacion(db: Session, analisis_id: str, simulacion_id: str, *,
                         quien: str | None = None) -> models.Simulacion:
    """pendiente → descartada. No borra ni modifica ningún dato de la fila.

    No toca `Analisis` — descartar una simulación que no era la
    seleccionada no tiene efecto sobre `simulacion_validada_id`; si SÍ lo
    era (caso límite: se valida, y solo después se intenta descartar), la
    transición de estado ya se rechaza más abajo antes de llegar a tocar
    nada, porque una `validada` nunca puede pasar a `descartada`.
    """
    sim = _obtener_simulacion_de_analisis(db, analisis_id, simulacion_id)
    if sim.estado != "pendiente":
        raise TransicionInvalidaError(sim.estado, "descartada")
    try:
        sim.estado = "descartada"
        auditoria_service.auditar(db, quien=quien, entidad="simulacion", entidad_id=sim.id,
                                  accion="descartar", delta={"analisis_id": analisis_id})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sim)
    return sim


def volver_a_configuracion_original(db: Session, analisis_id: str, *,
                                    quien: str | None = None) -> models.Analisis:
    """`Analisis.simulacion_validada_id = NULL` — configuración actual
    vuelve a ser la original. No descarta, borra ni modifica ninguna
    `Simulacion`; ninguna cambia de estado. Operación idempotente: si ya
    era `NULL`, no hay nada que hacer y se persiste igual sin error.
    """
    analisis = _analisis_bloqueado(db, analisis_id)
    try:
        analisis.simulacion_validada_id = None
        auditoria_service.auditar(db, quien=quien, entidad="analisis", entidad_id=analisis.id,
                                  accion="volver_configuracion_original", delta={})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analisis)
    return analisis


def seleccionar_simulacion_validada(db: Session, analisis_id: str,
                                    simulacion_id: str, *,
                                    quien: str | None = None) -> models.Analisis:
    """Fase 5E.1 — reselecciona una `Simulacion` que YA está `validada` como
    configuración actual, sin tocar su estado histórico ni el de ninguna
    otra simulación, y sin ejecutar el motor.

    Distinta a propósito de `validar_simulacion`: esa exige `estado ==
    "pendiente"` y hace la transición de estado `pendiente → validada` (más
    fijar el puntero, la primera vez); esta exige `estado == "validada"` y
    SOLO mueve `Analisis.simulacion_validada_id` — nunca cambia `estado`,
    `fecha_validacion`, `overrides`, `parametros_aplicados` ni `resultado`
    de la simulación. `Sim A = validada, Sim B = validada` con el puntero
    moviéndose libremente entre A y B (o a NULL, vía
    `volver_a_configuracion_original`) es exactamente el caso que esta
    función existe para cubrir.

    Mismo mecanismo de bloqueo que `validar_simulacion`/
    `volver_a_configuracion_original` (`_analisis_bloqueado`, pesimista
    sobre `Analisis`) y misma comprobación de pertenencia
    (`_verificar_pertenencia`) — sin duplicar ninguna de las dos.
    """
    analisis = _analisis_bloqueado(db, analisis_id)
    sim = db.get(models.Simulacion, simulacion_id)
    if sim is None:
        raise SimulacionNoEncontradaError(simulacion_id)
    _verificar_pertenencia(sim, analisis_id)
    if sim.estado != "validada":
        raise TransicionInvalidaError(sim.estado, "seleccionada")

    try:
        analisis.simulacion_validada_id = sim.id
        auditoria_service.auditar(db, quien=quien, entidad="analisis", entidad_id=analisis.id,
                                  accion="seleccionar_configuracion",
                                  delta={"simulacion_id": sim.id})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analisis)
    return analisis


# ─────────────────────────── configuración actual (Fase 5E) ───────────────────────────

@dataclass(frozen=True)
class ConfiguracionActual:
    """Qué snapshot persistido representa la configuración actual de un
    análisis — nunca recalcula nada, solo resuelve qué fila leer.

    `entrada` es SIEMPRE la del `Analisis` original: el inmueble no se
    simula (ver docstring del módulo). `resultado` es el de la `Simulacion`
    seleccionada, o el del propio `Analisis` si no hay ninguna.
    `simulacion_id` es `None` cuando la configuración activa es la original
    — distíngase de "no hay simulaciones": puede haberlas y no estar
    ninguna seleccionada.
    """
    entrada: dict
    resultado: dict
    simulacion_id: str | None


def obtener_configuracion_actual(db: Session, analisis_id: str) -> ConfiguracionActual:
    """Resuelve, sin ejecutar M01-M14, qué `resultado` debe mostrarse hoy.

        simulacion_validada_id is None  → resultado = Analisis.resultado
        simulacion_validada_id is UUID  → resultado = Simulacion.resultado

    Si el puntero apuntara a una `Simulacion` inexistente (no debería
    ocurrir en producción gracias al `ondelete="SET NULL"` de la FK, pero
    SQLite —tests/dev— no aplica esa acción porque el proyecto no activa
    `PRAGMA foreign_keys`), se degrada de forma segura a la configuración
    original en vez de fallar la lectura.
    """
    analisis = db.get(models.Analisis, analisis_id)
    if analisis is None:
        raise AnalisisNoEncontradoError(analisis_id)

    if analisis.simulacion_validada_id is not None:
        sim = db.get(models.Simulacion, analisis.simulacion_validada_id)
        if sim is not None:
            return ConfiguracionActual(entrada=analisis.entrada, resultado=sim.resultado,
                                       simulacion_id=sim.id)

    return ConfiguracionActual(entrada=analisis.entrada, resultado=analisis.resultado,
                               simulacion_id=None)

"""Fase 5F.3 — generación de informes OFICIALES: snapshots históricos e
inmutables de la configuración vigente en el instante de emitirlos.

    Analisis (+ configuración actual)
        → obtener_configuracion_actual(db, analisis_id)   [reutilizada, no duplicada]
        → guardián de pertenencia
        → snapshot POR VALOR (entrada, parámetros, overrides, resultado)
        → Informe + una fila de Auditoria
        → un único commit

Lo que este servicio NO hace, y es la razón de que exista:

- NO ejecuta el motor. Ni M01-M14, ni M14 por separado. El `informe_markdown`
  ya está calculado dentro del `resultado` de la configuración de origen y se
  copia tal cual. Si M14 cambiara mañana, un informe histórico no debe cambiar
  de texto: esa es la garantía que se perdería al regenerarlo.
- NO modifica `Analisis` (tampoco `simulacion_validada_id`) ni `Simulacion`
  (ni `estado`, ni `fecha_validacion`, ni sus snapshots). Emitir un informe no
  es validar, ni seleccionar, ni decidir: solo inserta filas nuevas.
- NO reconstruye parámetros ausentes. Si el análisis es anterior a la
  migración 0014, `parametros_aplicados` queda en `NULL` y así se persiste.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import models
from app.services import auditoria_service, simulacion_service
# Se reutilizan las excepciones de `simulacion_service` en vez de declarar una
# jerarquía paralela: son exactamente las dos mismas condiciones («no existe el
# análisis», «esa simulación no es de este análisis») con el mismo significado,
# y duplicarlas obligaría a los llamadores a capturar dos tipos por concepto.
from app.services.simulacion_service import (AnalisisNoEncontradoError,
                                             PertenenciaCruzadaError,
                                             SimulacionError)

__all__ = ["generar_informe_oficial", "listar_informes", "obtener_informe",
           "AnalisisNoEncontradoError", "PertenenciaCruzadaError",
           "ConfiguracionInconsistenteError", "InformeNoEncontradoError"]


class ConfiguracionInconsistenteError(SimulacionError):
    """El análisis tiene una simulación seleccionada que no se puede resolver.

    `obtener_configuracion_actual` degrada a la configuración original en ese
    caso (Fase 5E), y para una LECTURA eso sigue siendo correcto. Pero emitir
    un informe oficial sobre esa degradación produciría un documento que
    afirma «generado desde la configuración original» cuando en realidad
    había una selección: una afirmación histórica falsa. La emisión se rechaza
    en vez de ocultarlo. La ruta lo traduce a HTTP 409.
    """

    def __init__(self, analisis_id: str, simulacion_id: str):
        super().__init__(
            f"La configuración validada del análisis {analisis_id} es inconsistente: "
            f"apunta a la simulación {simulacion_id}, que no se puede resolver")
        self.analisis_id = analisis_id
        self.simulacion_id = simulacion_id


class InformeNoEncontradoError(SimulacionError):
    """El informe no existe, o existe pero pertenece a otro análisis.

    Un solo error para ambos casos a propósito: distinguirlos permitiría
    confirmar la existencia de un informe ajeno. La ruta lo traduce a 404,
    mismo criterio que ya aplica el proyecto al acceso entre organizaciones.
    """

    def __init__(self, informe_id: str):
        super().__init__(f"Informe no encontrado: {informe_id}")
        self.informe_id = informe_id


def generar_informe_oficial(db: Session, analisis_id: str, *,
                            usuario_id: str | None = None,
                            quien: str | None = None) -> models.Informe:
    """Congela la configuración actual del análisis como informe oficial.

    `usuario_id` es el identificador técnico del usuario y va a
    `Informe.generado_por`; `quien` es el actor legible (correo) y va a
    `Auditoria.quien`. Son dos campos porque cumplen fines distintos: el
    informe es inmutable y no debe contener datos personales que el derecho de
    supresión obligaría a mutar, mientras que la auditoría sí guarda el actor
    y la infraestructura RGPD existente lo seudonimiza allí
    (`borrado_service.anonimizar_auditoria`, que actúa sobre `auditoria.quien`).

    Dos llamadas concurrentes producen dos informes, y es correcto: son dos
    documentos verdaderos con identidad propia. No hay bloqueo ni restricción
    única, porque no hay estado compartido que proteger: lo único mutable que
    se lee es el puntero de configuración, y se lee una sola vez.
    """
    analisis = db.get(models.Analisis, analisis_id)
    if analisis is None:
        raise AnalisisNoEncontradoError(analisis_id)

    # Fuente única de la procedencia y de la degradación defensiva ante un
    # puntero roto (Fase 5E): si `simulacion_validada_id` apunta a una fila
    # inexistente, devuelve la configuración original en vez de fallar.
    config = simulacion_service.obtener_configuracion_actual(db, analisis_id)

    # Fase 5F.4: la degradación defensiva de `obtener_configuracion_actual`
    # es correcta para leer, pero no para emitir. Si el análisis SÍ tenía una
    # simulación seleccionada y la configuración resuelta no la trae, el
    # informe declararía procedencia original siendo falso. Se detecta aquí,
    # comparando ambos valores, sin tocar `obtener_configuracion_actual`,
    # cuyo comportamiento siguen necesitando los endpoints de configuración.
    if analisis.simulacion_validada_id is not None and config.simulacion_id is None:
        raise ConfiguracionInconsistenteError(analisis_id, analisis.simulacion_validada_id)

    simulacion: models.Simulacion | None = None
    if config.simulacion_id is not None:
        simulacion = db.get(models.Simulacion, config.simulacion_id)
        # `obtener_configuracion_actual` resuelve el puntero por id y NO
        # comprueba que la simulación pertenezca a este análisis. Un puntero
        # corrompido hacia una simulación de otro análisis produciría un
        # informe con contenido ajeno, así que se verifica aquí antes de
        # persistir nada. No se confía en la FK de `analisis_id`: esa protege
        # el enlace del informe, no la coherencia de la procedencia.
        if simulacion is not None and simulacion.analisis_id != analisis_id:
            raise PertenenciaCruzadaError(simulacion.id, analisis_id)

    if simulacion is not None:
        parametros_aplicados = simulacion.parametros_aplicados
        overrides = simulacion.overrides
    else:
        # Configuración original. `parametros_aplicados` puede ser `NULL` si el
        # análisis es anterior a 0014: se persiste tal cual, declarando la
        # carencia. Nunca se sustituye por los parámetros vigentes hoy, que no
        # son los que produjeron este resultado (auditoría 5F.0).
        parametros_aplicados = analisis.parametros_aplicados
        overrides = {}

    informe = models.Informe(
        analisis_id=analisis.id,
        simulacion_id=config.simulacion_id,
        entrada_snapshot=config.entrada,
        parametros_aplicados=parametros_aplicados,
        overrides=overrides,
        resultado=config.resultado,
        generado_por=usuario_id,
    )
    # Informe y auditoría son UNA SOLA unidad de trabajo, mismo patrón que
    # `simulacion_service.crear_simulacion`. Sin el `rollback` explícito, un
    # fallo de `auditar` dejaba el INSERT ya volcado por el `flush` dentro de
    # una transacción abierta: la excepción se propagaba, pero si el llamador
    # confirmaba esa sesión por cualquier otro motivo, el informe quedaba
    # persistido SIN su evento de auditoría (defecto B-1, Fase 5F.3.1).
    try:
        db.add(informe)
        db.flush()      # asigna el id antes de referenciarlo desde la auditoría
        # Solo identificadores técnicos en `delta`: el servicio de auditoría veta
        # cualquier dato con forma de correo ahí (`DatoPersonalEnAuditoria`), y el
        # actor tiene su sitio en `quien`.
        auditoria_service.auditar(
            db, quien=quien, entidad="informe", entidad_id=informe.id,
            accion="generar_oficial",
            delta={"analisis_id": analisis.id, "simulacion_id": config.simulacion_id})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(informe)
    return informe


# ─────────────────────────── lectura histórica (Fase 5F.4) ───────────────────────────

def listar_informes(db: Session, analisis_id: str) -> list[models.Informe]:
    """Informes históricos de un análisis, del más reciente al más antiguo.

    Consulta directa sobre la tabla: no resuelve configuración actual, no
    ejecuta el motor y no lee parámetros vigentes. Filtra estrictamente por
    `analisis_id`, de modo que nunca puede colarse el informe de otro
    análisis. Sin paginación: los informes están acotados a un análisis y su
    número esperado es de unidades, a diferencia del listado global de
    análisis, que sí tiene `limit`.
    """
    return (db.query(models.Informe)
            .filter(models.Informe.analisis_id == analisis_id)
            .order_by(models.Informe.generado_en.desc())
            .all())


def obtener_informe(db: Session, analisis_id: str, informe_id: str) -> models.Informe:
    """Un informe concreto, comprobando que pertenece a ese análisis.

    El guardián de pertenencia no es opcional: sin él,
    `GET /analisis/A/informes/{informe-de-B}` devolvería el documento de B
    (IDOR entre análisis), porque el identificador del informe es global.
    `db.get` por sí solo no basta.
    """
    informe = db.get(models.Informe, informe_id)
    if informe is None or informe.analisis_id != analisis_id:
        raise InformeNoEncontradoError(informe_id)
    return informe

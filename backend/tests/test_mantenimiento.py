"""Fase 11 · Bloque I — deudas heredadas con propietario «Fase 11».

Dos defectos que no se manifiestan en ninguna petición HTTP y que, por tanto,
nadie descubre mirando la aplicación funcionar:

- **Deuda 7** — el limitador anti-abuso cacheaba «no hay Redis» de forma
  PERMANENTE al primer fallo. Una caída de Redis degradaba la protección a
  memoria de proceso para el resto de la vida del worker, y recuperar Redis no
  servía de nada hasta reiniciar. Con `--workers 2`, el límite efectivo quedaba
  multiplicado por el número de workers, en silencio y para siempre.
- **Deuda 2** — `token_consumido` solo crecía. Y el plazo de purga no es un
  número libre: el `jti` es lo único que impide reutilizar un enlace, así que
  borrarlo antes de que el token caduque devuelve el uso único.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core import rate_limit


# ───────────────── Deuda 7 · el limitador reintenta Redis ─────────────────

@pytest.fixture(autouse=True)
def _conexion_limpia():
    """Cada test parte sin cliente ni ventana de espera, y no deja estado."""
    rate_limit.reiniciar_conexion()
    yield
    rate_limit.reiniciar_conexion()


def test_un_fallo_de_redis_no_se_cachea_para_siempre(monkeypatch):
    """Test capital de la deuda 7.

    Antes, `_cliente_redis` se fijaba a `False` al primer fallo y `_redis()` no
    volvía a intentarlo **en toda la vida del proceso**. Aquí se simula que Redis
    está caído, se agota la ventana de espera y se comprueba que el siguiente
    intento **sí** reconecta: recuperar Redis vuelve a tener efecto sin reiniciar.
    """
    intentos = {"n": 0}

    class _ClienteFalso:
        def ping(self):
            intentos["n"] += 1
            if intentos["n"] == 1:
                raise ConnectionError("Redis caído")
            return True

    monkeypatch.setattr(rate_limit, "_construir_cliente", lambda: _ClienteFalso())

    assert rate_limit._redis() is None, "el primer intento debe fallar"
    assert intentos["n"] == 1

    # Sin agotar la espera no se reintenta: es lo que evita pagar el timeout de
    # conexión en cada petición mientras Redis sigue caído.
    assert rate_limit._redis() is None
    assert intentos["n"] == 1, "no debe reintentar dentro de la ventana de espera"

    # Vencida la ventana, reconecta.
    monkeypatch.setattr(rate_limit, "_reloj_backoff",
                        lambda: rate_limit._proximo_reintento + 0.01)

    assert rate_limit._redis() is not None, (
        "tras la ventana de espera debe reintentar; si no, una caída de Redis "
        "degrada la protección de forma permanente")
    assert intentos["n"] == 2


def test_la_espera_entre_reintentos_crece_y_esta_acotada(monkeypatch):
    """Retroceso exponencial con techo: ni machaca a un Redis caído ni se duerme.

    Sin techo, unas horas de caída llevarían la espera a días y la recuperación
    dejaría de detectarse en un plazo útil.
    """
    monkeypatch.setattr(rate_limit, "_construir_cliente",
                        lambda: (_ for _ in ()).throw(ConnectionError("caído")))

    esperas = []
    for _ in range(10):
        monkeypatch.setattr(rate_limit, "_reloj_backoff",
                            lambda: rate_limit._proximo_reintento + 0.01)
        rate_limit._redis()
        esperas.append(rate_limit._espera_actual)

    assert esperas[1] > esperas[0], "la espera debe crecer entre reintentos"
    # Techo ABSOLUTO, no `_ESPERA_MAXIMA_SEG`: comparar la implementación consigo
    # misma es una tautología que pasaría igual con la constante puesta a un día,
    # y entonces la recuperación de Redis dejaría de detectarse en un plazo útil
    # — exactamente el riesgo que este test dice vigilar.
    assert max(esperas) <= 60, (
        f"la espera entre reintentos llegó a {max(esperas)} s; por encima de un "
        "minuto, recuperar Redis tarda demasiado en notarse")


def test_un_fallo_en_plena_operacion_suelta_el_cliente(monkeypatch):
    """La otra cara de la deuda 7, que `PENDIENTES.md` no recogía.

    Si Redis muere a mitad de vida del proceso, el cliente cacheado sigue
    apuntando a un servidor que no responde y **cada** petición pagaría su
    timeout antes de degradar a memoria. Soltarlo hace que la ventana de espera
    entre en juego y el coste por petición vuelva a ser cero.
    """
    class _ClienteQueMuere:
        def pipeline(self):
            raise ConnectionError("Redis se cayó a mitad")

    rate_limit._cliente_redis = _ClienteQueMuere()

    rate_limit.registrar_intento("clave-cualquiera")

    assert rate_limit._cliente_redis is None, (
        "tras un fallo de operación el cliente debe soltarse, o cada petición "
        "seguirá pagando el timeout de un servidor muerto")
    assert rate_limit._proximo_reintento > 0


def test_el_limitador_sigue_contando_sin_redis(monkeypatch):
    """Degradar no es dejar de proteger: el respaldo en memoria debe funcionar."""
    monkeypatch.setattr(rate_limit, "_construir_cliente",
                        lambda: (_ for _ in ()).throw(ConnectionError("caído")))

    for _ in range(rate_limit._maximo()):
        rate_limit.registrar_intento("victima@example.com")

    assert rate_limit.bloqueado("victima@example.com") is True


def test_una_caida_de_redis_no_levanta_un_bloqueo_vigente(monkeypatch):
    """Test capital de la deuda 7, segunda parte.

    Los dos almacenes no se sincronizan jamás. Si cada intento se anotara solo en
    el que estuviera disponible, el instante en que Redis cae —o vuelve— pondría
    a cero el contador de la víctima, y un atacante solo tendría que espaciar sus
    intentos alrededor de cada parpadeo para no llegar nunca al límite. Con el
    retroceso de esta misma fase, esos parpadeos pasaron de ocurrir una vez a
    poder ocurrir cada pocos segundos.

    Se anota con Redis «arriba» y se comprueba que, al caerse, el bloqueo sigue.
    """
    class _RedisFalso:
        def pipeline(self):
            return self

        def zremrangebyscore(self, *_a, **_k):
            return self

        def zadd(self, *_a, **_k):
            return self

        def expire(self, *_a, **_k):
            return self

        def execute(self):
            return []

    monkeypatch.setattr(rate_limit, "_construir_cliente", lambda: _RedisFalso())
    rate_limit._cliente_redis = _RedisFalso()

    for _ in range(rate_limit._maximo()):
        rate_limit.registrar_intento("victima@example.com")

    # Redis desaparece de golpe.
    rate_limit._cliente_redis = None
    monkeypatch.setattr(rate_limit, "_construir_cliente",
                        lambda: (_ for _ in ()).throw(ConnectionError("caído")))

    assert rate_limit.bloqueado("victima@example.com") is True, (
        "una caída de Redis no puede levantar un bloqueo ya ganado")


def test_un_acceso_correcto_reinicia_el_contador_aunque_haya_varios_workers(monkeypatch):
    """Regresión de la escritura dual, y de una garantía que fijó la Fase 10.

    `limpiar()` borra la clave en Redis —global— pero de la memoria solo la del
    proceso que atiende la petición, y el backend corre con `--workers 2`. Si la
    memoria se consultara SIEMPRE, un acceso correcto atendido por el worker B no
    limpiaría el contador que el worker A guarda en la suya, y la víctima
    seguiría bloqueada: «N intentos por worker que un acceso correcto no
    reinicia», más duro que lo documentado.

    Aquí se simula justo eso: Redis sano, el contador global limpio, y la
    memoria local todavía con los intentos. Debe mandar Redis.
    """
    contador = {"n": 0}

    class _RedisSano:
        def ping(self):
            return True

        def pipeline(self):
            return self

        def zremrangebyscore(self, *_a, **_k):
            return self

        def zadd(self, *_a, **_k):
            contador["n"] += 1
            return self

        def expire(self, *_a, **_k):
            return self

        def execute(self):
            return []

        def zcard(self, *_a, **_k):
            return contador["n"]

        def delete(self, *_a, **_k):
            contador["n"] = 0

    monkeypatch.setattr(rate_limit, "_construir_cliente", lambda: _RedisSano())

    for _ in range(rate_limit._maximo()):
        rate_limit.registrar_intento("alicia@example.com")
    assert rate_limit.bloqueado("alicia@example.com") is True

    # Otro worker atiende el acceso correcto: limpia Redis, pero NO esta memoria.
    contador["n"] = 0

    assert rate_limit.bloqueado("alicia@example.com") is False, (
        "con Redis sano y sin caídas recientes manda Redis; si no, `limpiar()` "
        "deja de funcionar entre workers y un acceso correcto no desbloquea")


def test_al_recuperarse_redis_el_bloqueo_ganado_durante_la_caida_sigue_en_pie(monkeypatch):
    """La **mitad lectora** de la escritura dual, que no estaba cubierta.

    Los otros dos tests del par ejercitan el camino «sin cliente» y el camino
    «Redis sano sin caídas recientes». Ninguno ejecuta la consulta en OR, de modo
    que **borrarla dejaba la suite en verde** — y esa consulta es justo lo que
    impide que la recuperación de Redis le regale al atacante los intentos
    anotados mientras estuvo caído: los del respaldo en memoria nunca llegaron a
    Redis, así que el `zcard` recién recuperado los desconoce.
    """
    class _RedisRecuperado:
        def ping(self):
            return True

        def zremrangebyscore(self, *_a, **_k):
            return 0

        def zcard(self, *_a, **_k):
            return 0            # Redis no vio nada: estuvo caído

    # Fase 1: Redis caído. Los intentos solo se anotan en memoria.
    monkeypatch.setattr(rate_limit, "_construir_cliente",
                        lambda: (_ for _ in ()).throw(ConnectionError("caído")))
    for _ in range(rate_limit._maximo()):
        rate_limit.registrar_intento("victima@example.com")
    assert rate_limit.bloqueado("victima@example.com") is True

    # Fase 2: Redis vuelve, con el contador a cero y la caída aún reciente.
    monkeypatch.setattr(rate_limit, "_construir_cliente", lambda: _RedisRecuperado())
    monkeypatch.setattr(rate_limit, "_reloj_backoff",
                        lambda: rate_limit._proximo_reintento + 0.01)

    assert rate_limit.bloqueado("victima@example.com") is True, (
        "al recuperarse Redis, el bloqueo ganado durante la caída debe seguir en "
        "pie: si no, provocar un parpadeo bastaría para reiniciar el contador")


def test_el_retroceso_crece_aunque_redis_conteste_al_ping_pero_falle_al_operar(monkeypatch):
    """El modo de fallo más probable de Redis no es morir, es dejar de escribir.

    Memoria agotada con `noeviction`, réplica en solo lectura, `MISCONF`: el
    `PING` responde y las escrituras fallan. Si el retroceso se reiniciara al
    conectar, el ciclo sería de un segundo indefinidamente —fallo, aviso,
    reconexión, «recuperado», fallo—, con un cliente nuevo y dos líneas de log
    por vuelta. Por eso se reinicia tras una OPERACIÓN correcta, no tras el ping.
    """
    class _PingSiEscrituraNo:
        def ping(self):
            return True

        def pipeline(self):
            raise ConnectionError("MISCONF: no se puede escribir")

    monkeypatch.setattr(rate_limit, "_construir_cliente",
                        lambda: _PingSiEscrituraNo())

    esperas = []
    for _ in range(4):
        monkeypatch.setattr(rate_limit, "_reloj_backoff",
                            lambda: rate_limit._proximo_reintento + 0.01)
        rate_limit.registrar_intento("clave")
        esperas.append(rate_limit._espera_actual)

    assert esperas[-1] > esperas[0], (
        f"el retroceso no creció ({esperas}): con Redis respondiendo al ping "
        "pero rechazando escrituras, el proceso entraría en un ciclo de un "
        "segundo indefinido")


def test_consultar_una_clave_inexistente_no_crea_entrada_en_memoria(monkeypatch):
    """Leer no puede hacer crecer la estructura.

    Las claves las controla quien llama —y en `/recuperar` van por email—, así
    que si cada consulta dejara una entrada, mandar una dirección distinta en
    cada petición haría crecer el diccionario sin límite durante cualquier
    ventana de degradación.
    """
    monkeypatch.setattr(rate_limit, "_construir_cliente",
                        lambda: (_ for _ in ()).throw(ConnectionError("caído")))

    for i in range(50):
        rate_limit.bloqueado(f"inexistente-{i}@example.com")

    assert len(rate_limit._memoria) == 0


def test_limpiar_todo_no_reinicia_la_ventana_de_espera(monkeypatch):
    """`limpiar_todo` es autouse en la suite: si reiniciara la conexión, cada
    test pagaría un intento de conexión con su timeout."""
    monkeypatch.setattr(rate_limit, "_construir_cliente",
                        lambda: (_ for _ in ()).throw(ConnectionError("caído")))
    rate_limit._redis()
    espera_antes = rate_limit._proximo_reintento

    rate_limit.limpiar_todo()

    assert rate_limit._proximo_reintento == espera_antes


# ───────────── Deuda 2 · purga de `token_consumido` ─────────────

def _sembrar_token(db, jti: str, dias_de_antiguedad: int) -> str:
    """Siembra un `jti` **único por ejecución** y devuelve el usado.

    El `jti` es clave primaria, así que un literal fijo convierte cualquier
    ejecución que muera antes de su limpieza en dos rojos de la siguiente, cuyo
    origen no está en el código bajo prueba: `IntegrityError` al resembrar y un
    recuento inesperado en el test de la tabla vacía. Ya ha ocurrido en esta
    máquina con procesos huérfanos bloqueando el fichero SQLite.
    """
    from app import models

    unico = f"{jti}-{uuid.uuid4().hex[:8]}"
    db.add(models.TokenConsumido(
        jti=unico, proposito="verificar",
        consumido_en=datetime.now(timezone.utc) - timedelta(days=dias_de_antiguedad)))
    db.commit()
    return unico


def test_la_purga_borra_los_tokens_antiguos_y_respeta_los_recientes(api):
    """La tabla deja de crecer sin fin, pero solo por su cola."""
    from app import models
    from app.core.config import get_settings
    from app.core.db import SessionLocal
    from app.tasks.mantenimiento_tasks import purgar_tokens_consumidos

    dias = get_settings().purga_tokens_dias
    db = SessionLocal()
    try:
        antiguo = _sembrar_token(db, "jti-antiguo", dias + 5)
        reciente = _sembrar_token(db, "jti-reciente", 1)

        borrados = purgar_tokens_consumidos()

        assert borrados >= 1
        # Consulta real, no `db.get`: la purga borra con
        # `delete(synchronize_session=False)` y la sesión conservaría el objeto
        # en su mapa de identidad, de modo que una aserción con `get` pasaría en
        # verde con la purga rota. Que hoy funcionara dependía de que el objeto
        # no tuviera referencia fuerte local, que es un accidente, no un diseño.
        db.expunge_all()
        assert db.query(models.TokenConsumido).filter_by(jti=antiguo).count() == 0
        assert db.query(models.TokenConsumido).filter_by(jti=reciente).count() == 1
    finally:
        db.query(models.TokenConsumido).delete()
        db.commit()
        db.close()


def test_la_constante_de_ttl_maximo_sigue_el_ttl_real_del_codigo():
    """Guardia contra una justificación de seguridad que se quede obsoleta.

    `config.TTL_MAXIMO_JTI_HORAS` no puede importarse de `registro_service` —hay
    ciclo—, así que es un número escrito a mano. Lo que impide que mienta es este
    test, que lo **deriva del código real**: si alguien alarga el enlace de
    verificación, aquí se entera.

    Solo cuentan los propósitos que reclaman `jti`. El token de baja dura 30 días
    pero `/notificaciones/baja` no llama a `marcar_jti`, de modo que nunca entra
    en `token_consumido` y no manda sobre la retención. Confundir eso fue el
    error de la primera versión de este bloque.
    """
    from app.core.config import TTL_MAXIMO_JTI_HORAS
    from app.services.registro_service import HORAS_RESETEO, HORAS_VERIFICACION

    ttl_real = max(HORAS_VERIFICACION, HORAS_RESETEO)

    assert TTL_MAXIMO_JTI_HORAS >= ttl_real, (
        f"Un token de un solo uso vive {ttl_real} h, más de las "
        f"{TTL_MAXIMO_JTI_HORAS} h que la configuración asume. La purga podría "
        "borrar el jti de un enlace todavía válido y devolverle un uso.")


def test_la_retencion_de_tokens_supera_el_ttl_asumido():
    """La retención debe superar ESTRICTAMENTE el TTL, no igualarlo."""
    from app.core.config import TTL_MAXIMO_JTI_HORAS, get_settings

    assert get_settings().purga_tokens_dias > TTL_MAXIMO_JTI_HORAS / 24


@pytest.mark.parametrize("ajuste,valor", [
    ("purga_cuentas_dias", 3),      # errata plausible: se cae el cero de 30
    ("purga_cuentas_dias", 0),      # el corte pasa a ser «ahora»
    ("purga_tokens_dias", 0),       # reabre el uso único de los enlaces
    ("purga_tokens_dias", 1),       # igual al TTL: margen cero
])
def test_un_plazo_de_purga_peligroso_aborta_el_arranque(ajuste, valor, monkeypatch):
    """Test capital de configuración: una errata numérica NO puede borrar.

    El módulo de purga blindaba el modo —un valor desconocido cae en «informar»—
    pero no los números, que son el otro parámetro que decide a quién alcanza el
    borrado. `PURGA_CUENTAS_DIAS=3` es un entero válido para Pydantic, no llama
    la atención en ningún log, y la ejecución nocturna borraría de forma
    irreversible todas las altas de más de tres días.
    """
    from app.core.config import ConfiguracionInseguraError, get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setenv(ajuste.upper(), str(valor))

        with pytest.raises(ConfiguracionInseguraError):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_la_tarea_de_purga_ejecuta_las_dos_purgas_y_devuelve_su_resumen(api):
    """Ejercita `purgar()`, que es lo que `beat` encola y el worker ejecuta.

    Los demás tests llaman a `purgar_tokens_consumidos()` directamente, así que
    el cuerpo de la tarea no lo ejecutaba nadie: una deriva de firma entre ella y
    `purgar_cuentas_sin_verificar()` habría salido a la luz en producción a las
    04:30, no aquí. Es la misma tesis del bloque — código correcto que nadie
    invoca no cierra ninguna deuda.
    """
    from app.tasks.mantenimiento_tasks import purgar

    resumen = purgar()

    assert {"tokens_borrados", "modo", "candidatas", "cuentas_borradas",
            "organizaciones_borradas", "omitidas", "fallidas",
            "huerfanas"} <= resumen.keys()
    assert resumen["modo"] == "informar", (
        "el modo por defecto debe seguir siendo el que NO borra")


def test_la_purga_no_rompe_si_la_tabla_esta_vacia(api):
    """Una tarea de mantenimiento que revienta se lleva por delante al planificador."""
    from app.tasks.mantenimiento_tasks import purgar_tokens_consumidos

    assert purgar_tokens_consumidos() == 0


def test_la_purga_esta_programada_en_el_planificador():
    """Sin entrada en `beat_schedule`, la tarea existe y no se ejecuta jamás.

    Es el mismo modo de fallo que motivó separar `beat` del worker: código
    correcto que nadie invoca no arregla ninguna deuda.
    """
    from app.tasks.celery_app import celery

    tareas = {e["task"] for e in celery.conf.beat_schedule.values()}

    assert "seis.purgar" in tareas


def test_la_purga_se_programa_con_horario_y_no_con_un_intervalo():
    """Un intervalo de 86400 s no sobrevive a la recreación del contenedor.

    `beat` no persiste su `celerybeat-schedule`: vive en la capa efímera. Con un
    intervalo, cada recreación reinicia la cuenta de 24 horas, de modo que en un
    despliegue con recreaciones frecuentes la purga **podría no ejecutarse
    jamás** — un fallo mudo idéntico al que este bloque viene a cerrar. Un
    horario `crontab` está anclado al reloj y no tiene ese problema.
    """
    from celery.schedules import crontab

    from app.tasks.celery_app import celery

    entrada = next(e for e in celery.conf.beat_schedule.values()
                   if e["task"] == "seis.purgar")

    assert isinstance(entrada["schedule"], crontab), (
        "la purga debe programarse con crontab, no con un intervalo en segundos")


def test_la_tarea_de_purga_queda_registrada_en_la_aplicacion_celery():
    """Test capital de infraestructura: sin registro, `beat` encola y nadie ejecuta.

    `autodiscover_tasks` recibe **un solo** `related_name`, así que un módulo de
    tareas nuevo no se importa salvo que se declare explícitamente. Si falta, el
    planificador encola `seis.purgar` y el worker responde «Received unregistered
    task» en su log: la tarea parece programada, la deuda parece cerrada, y no se
    ejecuta nunca.

    Se fuerza el descubrimiento igual que hace el worker al arrancar, porque
    `autodiscover_tasks` es perezoso y en tiempo de importación no ha corrido.
    """
    from app.tasks.celery_app import celery

    celery.loader.import_default_modules()

    assert "seis.purgar" in celery.tasks

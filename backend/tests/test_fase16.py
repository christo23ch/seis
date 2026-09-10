"""Correcciones de la auditoría de seguridad (Fase 16, parte 2).

Un test por hallazgo de severidad alta y media, cada uno comprobado por mutación
—la demostración está en el PR—. Los hallazgos bajos que se corrigieron de paso
(B-1/B-2, cachear la política) no llevan test propio: su efecto es de
rendimiento, y un test de µs sería frágil sin proteger nada.
"""
from __future__ import annotations

import pytest

from app.core.config import get_settings

API = "/api/v1"

SECRETOS_ESTRICTOS = {
    "JWT_SECRET": "S7uP2rq-xK9vLm4Tz1Wc8YbNd6Fg0HjQ3aEoI5RtUvXyZpMk",
    "ADMIN_PASSWORD": "Xk4-Rq9tLm2Zv7Bn",
    "PROXIES_DE_CONFIANZA": "ninguno",
}


def _arrancar(monkeypatch, **variables):
    get_settings.cache_clear()
    for clave, valor in {**SECRETOS_ESTRICTOS, **variables}.items():
        monkeypatch.setenv(clave, valor)
    try:
        return get_settings()
    finally:
        get_settings.cache_clear()


# ═══════════════════ A-1 · guardia de CORS ═══════════════════

@pytest.mark.parametrize("origenes,fragmento", [
    ("*", "«*»"),
    ("https://ok.example,*", "«*»"),
    ("http://ejemplo.com", "no es «https://»"),
    ("", "está vacío"),
])
def test_cors_peligroso_aborta_el_arranque_en_entorno_estricto(
        monkeypatch, origenes, fragmento):
    """El comodín con credenciales es la configuración MENOS sintomática y la más
    peligrosa: Starlette no emite `*` —que el navegador rechazaría, avisando—
    sino que refleja el origen de quien pregunta.

    La guardia existe porque `config.py` ya aborta por secretos débiles, por
    proxies sin declarar y por purgas mal configuradas. Que CORS fuera la
    excepción era la incoherencia, no el riesgo teórico.
    """
    from app.core.config import ConfiguracionInseguraError

    with pytest.raises(ConfiguracionInseguraError) as e:
        _arrancar(monkeypatch, SEIS_ENV="staging", SEIS_CORS_ORIGINS=origenes)
    assert fragmento in str(e.value)


def test_cors_con_https_declarado_arranca(monkeypatch):
    ajustes = _arrancar(monkeypatch, SEIS_ENV="production",
                        SEIS_CORS_ORIGINS="https://seis.example,https://www.seis.example")
    assert ajustes.cors_origins == ["https://seis.example", "https://www.seis.example"]


def test_declarar_ninguno_permite_una_api_sin_navegador(monkeypatch):
    """Hermano del centinela de los proxies: distinguir «no hay frontend» de «se
    me olvidó». Sin él, la única forma de arrancar sería inventarse un origen.

    Y produce lista VACÍA, no `["ninguno"]`: montar el middleware con un origen
    literal llamado «ninguno» no autorizaría a nadie, pero por accidente.
    """
    assert _arrancar(monkeypatch, SEIS_ENV="production",
                     SEIS_CORS_ORIGINS="ninguno").cors_origins == []


def test_en_desarrollo_el_localhost_de_siempre_sigue_valiendo(monkeypatch):
    """La guardia no puede romper el flujo local: ahí el frontend es http."""
    assert _arrancar(monkeypatch, SEIS_ENV="development",
                     SEIS_CORS_ORIGINS="http://localhost:3000").cors_origins == \
        ["http://localhost:3000"]


# ═══════════════════ A-2 · la degradación deja de ser muda ═══════════════════

def test_cada_caida_al_par_tcp_queda_contada_con_su_motivo():
    """El defecto que este módulo cerró volvía por una omisión de configuración
    y **sin un solo síntoma**: `red.py` no emitía un registro en 262 líneas."""
    from app.core import red

    politica = red.PoliticaProxy(redes=red.parsear_redes("10.0.0.0/24"),
                                 cabecera="x-forwarded-for", saltos=1)
    red.reiniciar_recuento()

    assert red.resolver_ip("10.0.0.5", ["203.0.113.9"], politica) == "203.0.113.9"
    assert red.resolver_ip("10.0.0.5", [], politica) == "10.0.0.5"
    assert red.resolver_ip("8.8.8.8", ["203.0.113.9"], politica) == "8.8.8.8"
    demasiadas = ", ".join(f"203.0.113.{i}" for i in range(20))
    assert red.resolver_ip("10.0.0.5", [demasiadas], politica) == "10.0.0.5"

    recuento = red.recuento_resoluciones()
    assert recuento[red.MOTIVO_RESUELTA] == 1
    assert recuento[red.MOTIVO_SIN_CABECERA] == 1
    assert recuento[red.MOTIVO_PAR_NO_CONFIABLE] == 1
    assert recuento[red.MOTIVO_CABECERA_DESMESURADA] == 1
    # Tres de cuatro no se resolvieron: es la cifra que delata la avería.
    assert red.proporcion_sin_resolver() == pytest.approx(0.75)


def test_la_proporcion_es_cero_cuando_todo_se_resuelve():
    from app.core import red

    politica = red.PoliticaProxy(redes=red.parsear_redes("10.0.0.0/24"),
                                 cabecera="x-forwarded-for", saltos=1)
    red.reiniciar_recuento()
    for i in range(5):
        red.resolver_ip("10.0.0.5", [f"203.0.113.{i}"], politica)
    assert red.proporcion_sin_resolver() == 0.0


def test_la_primera_caida_se_registra_en_el_log(caplog):
    """A la primera, no a la centésima: una avería real no debe esperar turno."""
    from app.core import red

    politica = red.PoliticaProxy(redes=red.parsear_redes("10.0.0.0/24"),
                                 cabecera="x-forwarded-for", saltos=1)
    red.reiniciar_recuento()
    with caplog.at_level("WARNING", logger="seis.red"):
        red.resolver_ip("10.0.0.5", [], politica)
    assert any("no se pudo resolver la IP" in r.message for r in caplog.records)


def test_el_detalle_publica_la_proporcion_sin_resolver(api, headers, monkeypatch):
    """Se expone donde alguien ya mira, no en un panel que nadie ha montado."""
    from app.api import salud

    monkeypatch.setattr(salud, "_comprobar_bd", lambda db: (True, 1.0))
    monkeypatch.setattr(salud, "_comprobar_redis", lambda: (True, 1.0))
    salud.reiniciar_cache_sonda()

    resolucion = api.get(f"{API}/health/detalle", headers=headers).json()["red"]["resolucion_ip"]
    assert set(resolucion) == {"politica_activa", "sin_resolver", "por_motivo"}


# ═══════════ 1.3 · datos personales en `auditoria.delta` ═══════════

def test_un_correo_en_el_delta_no_llega_a_la_base(api):
    """El borrado por RGPD limpia `quien` y `entidad_id` POR NOMBRE DE COLUMNA.
    `delta` no puede estar en esa lista —su contenido es arbitrario—, así que un
    correo ahí sobreviviría a un borrado que el sistema declara completo. Y el
    test que deriva las tablas hijas del esquema no lo vería nunca: `auditoria`
    no tiene clave foránea a `usuario`.
    """
    from app import models
    from app.core.datos_personales import DatoPersonalEnAuditoria
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        db.add(models.Auditoria(quien="sistema", entidad="x", entidad_id="y",
                                accion="prueba", delta={"correo": "juan@ejemplo.com"}))
        with pytest.raises(DatoPersonalEnAuditoria):
            db.flush()
    finally:
        db.rollback()
        db.close()


def test_la_barrera_esta_en_el_MODELO_y_no_en_el_servicio(api):
    """Lo que hace que esto sea una barrera y no una convención.

    Un embudo que hay que acordarse de usar no cubre la construcción número 24.
    Colgado de `before_insert`, cubre toda inserción por el ORM venga de donde
    venga — incluido el worker de Celery, que no importa `main.py`.
    """
    from sqlalchemy import event

    from app import models

    assert event.contains(models.Auditoria, "before_insert",
                          models._vetar_datos_personales_en_delta)


@pytest.mark.parametrize("delta,detectado", [
    ({"organizacion_id": "abc-123"}, False),
    ({"n": 3, "ok": True, "lista": [1, 2]}, False),
    ({"email": "juan@ejemplo.com"}, True),
    ({"a": {"b": ["x", "ana@dominio.es"]}}, True),          # anidado
    ({"juan@ejemplo.com": "activo"}, True),                  # en la CLAVE
    ({"nota": "escribir a pepe@dominio.org"}, True),         # dentro de una frase
])
def test_el_detector_encuentra_el_correo_donde_este(delta, detectado):
    from app.core.datos_personales import buscar_correo

    assert (buscar_correo(delta) is not None) is detectado


def test_auditar_falla_al_construir_y_no_al_volcar(api):
    """`auditar()` no es la barrera, pero sí falla antes y con mejor mensaje."""
    from app.core.datos_personales import DatoPersonalEnAuditoria
    from app.core.db import SessionLocal
    from app.services import auditoria_service

    db = SessionLocal()
    try:
        with pytest.raises(DatoPersonalEnAuditoria) as e:
            auditoria_service.auditar(db, quien="sistema", entidad="x",
                                      entidad_id="y", accion="prueba",
                                      delta={"a": "juan@ejemplo.com"})
        assert "delta.a" in str(e.value)
    finally:
        db.rollback()
        db.close()


# ═══════════ 1.5 · la red de guardia falla en vez de pasar en vacío ═══════════

def test_la_red_del_esquema_falla_si_el_metadata_esta_vacio():
    """Una red que no encuentra nada porque no puede ver nada tiene que ponerse
    roja. Antes devolvía el conjunto vacío y el `assert not sin_cubrir` de quien
    la llamaba pasaba sin comprobar nada."""
    from sqlalchemy import MetaData

    from tests.escenario_rgpd import tablas_hijas_de

    with pytest.raises(AssertionError, match="ha importado"):
        tablas_hijas_de(MetaData(), "usuario")


def test_la_red_del_esquema_falla_si_el_padre_no_existe():
    """El otro modo de pasar en vacío: una errata en el nombre de la tabla.
    `tablas_hijas_de(metadata, "usuarios")` —en plural— no encontraría hijas."""
    from app.core.db import Base

    from tests.escenario_rgpd import tablas_hijas_de

    with pytest.raises(AssertionError, match="no existen en el esquema"):
        tablas_hijas_de(Base.metadata, "usuarios")


# ═══════════════════ M-1 · cabeceras de seguridad ═══════════════════

@pytest.mark.parametrize("cabecera,esperado", [
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "DENY"),
    ("referrer-policy", "no-referrer"),
])
def test_las_respuestas_llevan_las_cabeceras_de_seguridad(api, cabecera, esperado):
    r = api.get(f"{API}/legal/terminos")
    assert r.headers.get(cabecera) == esperado


def test_la_csp_de_la_api_no_permite_cargar_nada(api):
    """`default-src 'none'` vale porque una respuesta de API no carga recursos.
    NO protege al frontend, que es otro despliegue y necesita la suya."""
    csp = api.get(f"{API}/legal/terminos").headers.get("content-security-policy")
    assert "default-src 'none'" in csp and "frame-ancestors 'none'" in csp


def test_el_informe_en_texto_plano_tambien_lleva_nosniff(api, headers):
    """El endpoint donde `nosniff` de verdad importa: sin él el navegador puede
    decidir por su cuenta que un texto plano es HTML."""
    r = api.get(f"{API}/analisis/no-existe/informe", headers=headers)
    assert r.headers.get("x-content-type-options") == "nosniff"


# ═══════════════════ M-2 · cota de trabajo de la sonda ═══════════════════

def test_la_sonda_publica_no_consulta_la_base_en_cada_peticion(api, monkeypatch):
    """Era el amplificador más barato del sistema: público, sin autenticar, y un
    `SELECT 1` más un `PING` por llamada.

    Se acota el TRABAJO y no las peticiones a propósito: un 429 o un 503 en una
    sonda de readiness lo lee el orquestador como «no está lista», y como la
    configuración sería idéntica en todas las réplicas, sacaría de rotación a
    réplicas sanas.
    """
    from app.api import salud

    veces = {"bd": 0, "redis": 0}

    def bd(_db):
        veces["bd"] += 1
        return True, 1.0

    def redis():
        veces["redis"] += 1
        return True, 1.0

    monkeypatch.setattr(salud, "_comprobar_bd", bd)
    monkeypatch.setattr(salud, "_comprobar_redis", redis)
    salud.reiniciar_cache_sonda()

    for _ in range(25):
        assert api.get(f"{API}/health/listo").status_code == 200

    assert veces["bd"] == 1, f"25 peticiones produjeron {veces['bd']} consultas"
    assert veces["redis"] == 1


def test_la_sonda_sigue_diciendo_la_verdad_cuando_algo_cae(api, monkeypatch):
    """La caché no puede convertir una caída real en un 200."""
    from app.api import salud

    monkeypatch.setattr(salud, "_comprobar_bd", lambda _db: (False, 1.0))
    monkeypatch.setattr(salud, "_comprobar_redis", lambda: (True, 1.0))
    salud.reiniciar_cache_sonda()

    r = api.get(f"{API}/health/listo")
    assert r.status_code == 503
    assert r.json()["componentes"]["bd"] != r.json()["componentes"]["redis"]


# ═══════════════════ M-4 · normalización del correo ═══════════════════

def test_crear_usuario_normaliza_el_correo(api):
    """`obtener_por_email` recortaba y `crear_usuario` no: un correo con un
    espacio pegado se guardaba con él y quedaba imposible de encontrar, de modo
    que la cuenta existía y su titular no podía entrar, ni verificar, ni
    recuperar la clave.

    No era alcanzable desde el alta pública —`EmailStr` recorta antes— pero sí
    desde `scripts/sembrar.py`, que lee ADMIN_EMAIL del entorno sin tocarlo.
    """
    import uuid

    from app.core.db import SessionLocal
    from app.services import usuario_service

    sufijo = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        org = usuario_service.crear_organizacion(db, f"Org {sufijo}")
        u = usuario_service.crear_usuario(
            db, f"  ESPACIOS-{sufijo}@Ejemplo.com  ", "unaClaveLarga1", "X",
            "analista", organizacion_id=org.id)
        assert u.email == f"espacios-{sufijo}@ejemplo.com"
        # Y lo que de verdad importa: se puede volver a encontrar.
        assert usuario_service.obtener_por_email(
            db, f"espacios-{sufijo}@ejemplo.com") is not None
    finally:
        db.close()


# ═══════════════════ M-5 · vida del enlace de baja ═══════════════════

def test_el_enlace_de_baja_dura_una_semana_y_no_un_mes():
    """Era un portador válido 30 días que nombra a una persona. Quien lo
    obtuviera podía mantenerla dada de baja indefinidamente.

    No se le añade uso único a propósito: con el `jti` consumido, el segundo clic
    desde el mismo correo —un reenvío, el prefetch del cliente— devolvería un
    error a quien solo quería confirmar que ya estaba dado de baja.
    """
    from app.services.notificaciones_service import HORAS_ENLACE_BAJA

    assert HORAS_ENLACE_BAJA == 24 * 7


def test_el_jti_se_conserva_mas_que_el_token_mas_largo():
    """Invariante que M-5 podría haber roto por el otro lado: si la purga de
    `token_consumido` borrara el `jti` antes de que el token caduque, el uso
    único desaparecería."""
    from app.core.config import TTL_MAXIMO_JTI_HORAS, get_settings

    assert get_settings().purga_tokens_dias * 24 > TTL_MAXIMO_JTI_HORAS


def test_la_cache_de_la_sonda_caduca(api, monkeypatch):
    """UNA MUTACIÓN SOBREVIVIÓ AQUÍ y este test es la respuesta.

    Con `SEGUNDOS_DE_CACHE_SONDA` puesto a infinito, la suite entera seguía
    verde: nada comprobaba que la caché llegara a caducar. Y una caché eterna es
    peor que no tener caché — convierte una caída real de la base en un 200
    permanente, y la sonda pasa a mentir en el único momento en que importa.
    """
    from app.api import salud

    llamadas = {"n": 0}

    def bd(_db):
        llamadas["n"] += 1
        return True, 1.0

    monkeypatch.setattr(salud, "_comprobar_bd", bd)
    monkeypatch.setattr(salud, "_comprobar_redis", lambda: (True, 1.0))
    salud.reiniciar_cache_sonda()

    reloj = {"t": 1000.0}
    monkeypatch.setattr(salud, "_reloj_sonda", lambda: reloj["t"])

    api.get(f"{API}/health/listo")
    api.get(f"{API}/health/listo")
    assert llamadas["n"] == 1, "dentro de la ventana debe reutilizarse"

    # Se envejece el reloj una cantidad FIJA, no derivada de la constante.
    #
    # La primera versión de este test hacía `reloj["t"] += SEGUNDOS_DE_CACHE_SONDA
    # + 0.01`, y la mutación seguía sobreviviendo: con la constante puesta a
    # infinito, el avance también era infinito y la caché caducaba igual. El test
    # LEÍA SU VALOR ESPERADO DE LO QUE ESTABA PROBANDO, que es la misma trampa
    # que este proyecto lleva cinco veces encontrando (ADR-0014).
    reloj["t"] += 5.0
    api.get(f"{API}/health/listo")
    assert llamadas["n"] == 2, (
        "la caché no caducó: una caída real quedaría enmascarada para siempre")


def test_la_ventana_de_cache_de_la_sonda_es_corta_y_finita():
    """Segunda aserción, independiente de la anterior y a propósito.

    El test de caducidad usa un avance fijo, así que solo demuestra que la caché
    caduca ANTES de cinco segundos. Este fija el otro extremo: que la ventana sea
    un valor finito y del orden de un segundo. Entre los dos no queda hueco para
    que la constante se vuelva absurda sin que nadie lo vea.
    """
    import math

    from app.api import salud

    assert math.isfinite(salud.SEGUNDOS_DE_CACHE_SONDA)
    assert 0 < salud.SEGUNDOS_DE_CACHE_SONDA <= 2.0

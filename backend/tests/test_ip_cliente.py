"""Fase 11 · Bloque H — la IP real del cliente tras proxy.

Cierra la puerta de despliegue heredada de la Fase 10. Casi todos los casos son
unitarios sobre `resolver_ip`, que es pura: recibe los valores crudos de la
cabecera en vez de la petición, precisamente para que la parte delicada se pueda
comprobar sin montar HTTP.
"""
from __future__ import annotations

import uuid

import pytest

from app.core import red

CLIENTE = "203.0.113.7"
PROXY = "10.0.0.5"
CLOUDFLARE = "198.51.100.9"
FALSA = "6.6.6.6"


def _politica(csv=f"{PROXY}/32", cabecera="x-forwarded-for", saltos=1):
    return red.PoliticaProxy(redes=red.parsear_redes(csv), cabecera=cabecera,
                             saltos=saltos)


# ─────────── Sin política declarada: el defecto seguro ───────────

def test_sin_proxies_declarados_se_usa_el_par_tcp():
    assert red.resolver_ip(PROXY, [CLIENTE], _politica(csv="")) == PROXY


def test_sin_proxies_declarados_una_cabecera_falsificada_se_ignora():
    """El agujero que este bloque existe para cerrar."""
    assert red.resolver_ip(PROXY, [FALSA], _politica(csv="")) == PROXY


def test_el_centinela_ninguno_equivale_a_no_leer_cabeceras():
    assert red.resolver_ip(PROXY, [FALSA], _politica(csv="ninguno")) == PROXY


def test_un_par_no_declarado_no_puede_usar_cabeceras():
    """Quien nos habla no es uno de nuestros proxies: su cabecera no vale nada."""
    assert red.resolver_ip("192.0.2.99", [CLIENTE], _politica()) == "192.0.2.99"


# ─────────── Tras proxy: de dónde se lee y por qué ───────────

def test_tras_un_proxy_declarado_se_toma_el_ultimo_valor():
    assert red.resolver_ip(PROXY, [CLIENTE], _politica()) == CLIENTE


def test_el_prefijo_falsificado_de_x_forwarded_for_se_descarta():
    """Cada intermediario AÑADE por la derecha; el prefijo izquierdo lo escribe
    el cliente. Tomar el primer valor sería fiarse justo del que miente."""
    assert red.resolver_ip(PROXY, [f"{FALSA}, {CLIENTE}"], _politica()) == CLIENTE


def test_con_dos_saltos_se_toma_el_penultimo_valor():
    """Cloudflare + proxy inverso.

    Con dos saltos hay que declarar de confianza **los dos** intermediarios: el
    proxy que nos habla y el que está por delante. Ver el test siguiente para el
    motivo, que no es burocrático.
    """
    politica = _politica(csv=f"{PROXY}/32,{CLOUDFLARE}/32", saltos=2)
    cadena = f"{CLIENTE}, {CLOUDFLARE}"

    assert red.resolver_ip(PROXY, [cadena], politica) == CLIENTE


def test_con_dos_saltos_un_prefijo_falsificado_sigue_sin_colarse():
    """La clave del diseño: se cuentan POSICIONES, no se miran valores.

    Un prefijo inyectado empuja la cadena hacia la izquierda, nunca hacia la
    posición leída. Es lo que hace inmune a este método frente al de saltar los
    saltos «de confianza» por pertenencia, que se rompe inyectando una IP de la
    propia lista — trivial con Cloudflare, cuyos rangos son públicos.
    """
    politica = _politica(csv=f"{PROXY}/32,{CLOUDFLARE}/32", saltos=2)
    cadena = f"{FALSA}, {CLIENTE}, {CLOUDFLARE}"

    assert red.resolver_ip(PROXY, [cadena], politica) == CLIENTE


def test_con_dos_saltos_una_cola_no_declarada_cae_al_par():
    """Cierra el caso en que contar posiciones, por sí solo, no basta.

    Topología `Cloudflare → nginx → uvicorn` con saltos=2. Un atacante que
    descubra la IP de origen y conecte **directamente a nginx** manda
    `XFF: 6.6.6.6, 1.2.3.4`; nginx añade la suya y la posición -2 pasa a ser un
    valor que el atacante eligió. Exigir que las posiciones a la derecha de la
    leída sean proxies declarados lo impide, sin renunciar a la inmunidad frente
    a inyectar una IP de la lista: no se decide QUÉ leer mirando valores, solo se
    valida lo ya leído.
    """
    politica = _politica(csv=f"{PROXY}/32,{CLOUDFLARE}/32", saltos=2)
    cadena = f"{FALSA}, {CLIENTE}"        # la cola sería CLIENTE, que no es proxy

    assert red.resolver_ip(PROXY, [cadena], politica) == PROXY


def test_una_cadena_mas_corta_que_los_saltos_declarados_cae_al_par():
    assert red.resolver_ip(PROXY, [CLIENTE], _politica(saltos=3)) == PROXY


def test_tras_cloudflare_se_toma_cf_connecting_ip():
    politica = _politica(cabecera="cf-connecting-ip")

    assert red.resolver_ip(PROXY, [CLIENTE], politica) == CLIENTE


def test_cf_connecting_ip_se_ignora_si_el_par_no_es_de_confianza():
    """Quien llegue directo al origen saltándose Cloudflare no dicta su IP."""
    politica = _politica(cabecera="cf-connecting-ip")

    assert red.resolver_ip("192.0.2.99", [FALSA], politica) == "192.0.2.99"


def test_una_cabecera_de_valor_unico_con_varios_valores_se_descarta():
    politica = _politica(cabecera="cf-connecting-ip")

    assert red.resolver_ip(PROXY, [f"{FALSA}, {CLIENTE}"], politica) == PROXY


def test_la_cabecera_repetida_se_concatena_en_orden():
    """RFC 7230 §3.2.2: varias cabeceras del mismo nombre son una lista."""
    assert red.resolver_ip(PROXY, [FALSA, CLIENTE], _politica()) == CLIENTE


def test_con_tres_saltos_una_cola_parcialmente_declarada_cae_al_par():
    """Mata la mutación «comprobar solo el último salto».

    Con `saltos=2` la cola tiene un único elemento, de modo que una
    implementación que solo mirase `valores[-1]` pasaría todos los demás tests.
    Con tres saltos la cola son dos, y basta con que **uno** no sea proxy
    declarado para que la posición leída deje de ser fiable.
    """
    politica = _politica(csv=f"{PROXY}/32,{CLOUDFLARE}/32", saltos=3)
    cadena = f"{CLIENTE}, {FALSA}, {CLOUDFLARE}"     # cola = [FALSA, CLOUDFLARE]

    assert red.resolver_ip(PROXY, [cadena], politica) == PROXY


def test_con_tres_saltos_y_cola_integra_se_resuelve():
    """Contraparte positiva del anterior, con la cola entera declarada."""
    politica = _politica(csv=f"{PROXY}/32,{CLOUDFLARE}/32", saltos=3)
    cadena = f"{CLIENTE}, {CLOUDFLARE}, {PROXY}"

    assert red.resolver_ip(PROXY, [cadena], politica) == CLIENTE


def test_la_cola_se_normaliza_antes_de_comprobarse():
    """Un salto con puerto sigue siendo el mismo proxy.

    Sin normalizar la cola, `10.0.0.5:443` no casaría con la red declarada y la
    resolución caería al par TCP en silencio.
    """
    politica = _politica(csv=f"{PROXY}/32,{CLOUDFLARE}/32", saltos=2)

    assert red.resolver_ip(PROXY, [f"{CLIENTE}, {CLOUDFLARE}:443"], politica) == CLIENTE


def test_demasiados_elementos_se_descartan_aunque_la_cabecera_sea_corta():
    """Aísla el tope de elementos del tope de longitud.

    El caso de la cabecera desmesurada sale por el límite de bytes y nunca llega
    a esta rama, así que sin este test subir `MAX_ELEMENTOS` no rompería nada.
    """
    cadena = ", ".join(["1.1.1.1"] * (red.MAX_ELEMENTOS + 1))
    assert len(cadena) < red.MAX_LONGITUD_CABECERA

    assert red.resolver_ip(PROXY, [cadena], _politica()) == PROXY


# ─────────── El adaptador configuración → política ───────────

def _politica_desde_entorno(monkeypatch, **variables):
    from app.core.config import get_settings

    get_settings.cache_clear()
    for clave, valor in variables.items():
        monkeypatch.setenv(clave, valor)
    try:
        return red.politica_actual()
    finally:
        get_settings.cache_clear()


def test_politica_actual_ignora_una_cabecera_no_admitida(monkeypatch):
    """Defensa en profundidad: la lista blanca no puede vivir solo en la guardia.

    Aquella únicamente corre en entornos estrictos, así que una errata en
    desarrollo dejaría leyendo una cabecera arbitraria.
    """
    politica = _politica_desde_entorno(monkeypatch,
                                       PROXIES_DE_CONFIANZA="10.0.0.5/32",
                                       CABECERA_IP_CLIENTE="cf-connecting_ip")

    assert politica.cabecera == ""
    assert politica.activa is False


@pytest.mark.parametrize("valor,esperado", [("0", 1), ("99", red.MAX_ELEMENTOS)])
def test_politica_actual_acota_los_saltos_al_rango(valor, esperado, monkeypatch):
    politica = _politica_desde_entorno(monkeypatch, SALTOS_DE_PROXY=valor)

    assert politica.saltos == esperado


def test_una_politica_con_cero_saltos_es_inconstruible():
    """La invariante viaja con el tipo: `valores[-0]` es el PRIMER elemento, o
    sea el que escribe el cliente."""
    with pytest.raises(ValueError):
        red.PoliticaProxy(redes=(), cabecera="x-forwarded-for", saltos=0)


# ─────────── IPv4 mapeada en IPv6 ───────────

def test_un_proxy_declarado_se_reconoce_en_forma_ipv4_mapeada():
    """Un socket dual-stack entrega `::ffff:a.b.c.d`; sin normalizar, el proxy
    declarado deja de reconocerse y se vuelve al cupo global en silencio."""
    assert red.es_par_de_confianza(f"::ffff:{PROXY}", _politica()) is True


def test_una_ipv4_mapeada_no_colapsa_en_un_unico_contador():
    """Sin normalizar, TODAS las IPv4 mapeadas daban la clave `::/64` y todos los
    clientes compartían un solo contador — el cupo global que este bloque cierra."""
    assert red.clave_de_origen(f"::ffff:{CLIENTE}") == CLIENTE
    assert red.clave_de_origen("::ffff:9.9.9.9") != red.clave_de_origen(f"::ffff:{CLIENTE}")


def test_dos_prefijos_ipv6_distintos_no_comparten_clave():
    """La agregación a /64 no puede degenerar en una constante."""
    assert red.clave_de_origen("2001:db8:1::1") != red.clave_de_origen("2001:db8:2::1")


# ─────────── Entradas anómalas: todas caen al par ───────────

@pytest.mark.parametrize("valor", ["no-es-una-ip", "", "999.999.999.999", "::gg"])
def test_un_valor_que_no_es_una_ip_se_descarta(valor):
    assert red.resolver_ip(PROXY, [valor], _politica()) == PROXY


@pytest.mark.parametrize("crudo,esperado", [
    ("192.0.2.1:1234", "192.0.2.1"),
    ("[2001:db8::1]:443", "2001:db8::1"),
])
def test_se_normaliza_el_puerto_y_los_corchetes(crudo, esperado):
    assert red.resolver_ip(PROXY, [crudo], _politica()) == esperado


def test_una_cabecera_desmesurada_se_descarta():
    assert red.resolver_ip(PROXY, [", ".join([CLIENTE] * 100)], _politica()) == PROXY


def test_un_par_no_numerico_no_rompe_la_comprobacion():
    """`testclient` es el par de toda la suite: no es una IP y nunca es de confianza."""
    assert red.es_par_de_confianza("testclient", _politica()) is False
    assert red.resolver_ip("testclient", [CLIENTE], _politica()) == "testclient"


def test_un_cidr_de_confianza_incluye_a_sus_miembros_y_excluye_al_resto():
    politica = _politica(csv="172.18.0.0/16")

    assert red.resolver_ip("172.18.0.1", [CLIENTE], politica) == CLIENTE
    assert red.resolver_ip("172.19.0.1", [CLIENTE], politica) == "172.19.0.1"


def test_una_red_mal_escrita_se_descarta_en_vez_de_ampliarse():
    """El error cae del lado de leer menos cabeceras, nunca del de confiar más."""
    assert red.parsear_redes("no-es-una-red, 10.0.0.5/32") == red.parsear_redes("10.0.0.5/32")


# ─────────── Agregación por /64 en IPv6 ───────────

def test_la_clave_de_origen_agrupa_ipv6_por_prefijo_de_64():
    """Un cliente doméstico dispone del /64 entero: contar por dirección exacta
    equivaldría a no contar."""
    a = red.clave_de_origen("2001:db8:1:2::1")
    b = red.clave_de_origen("2001:db8:1:2::ffff")

    assert a == b


def test_la_clave_de_origen_deja_intactas_las_ipv4_y_los_valores_no_ip():
    assert red.clave_de_origen(CLIENTE) == CLIENTE
    assert red.clave_de_origen("testclient") == "testclient"


# ─────────── Guardia de arranque ───────────

SECRETOS = {"JWT_SECRET": "kJ7pQz2Xv9RtNw4bYm6HcE8sLdA3fUgW1oPiZxTq",
            "ADMIN_PASSWORD": "Zq8Rm2Vt6Yx4Bn7Kw"}


def _arrancar(monkeypatch, **variables):
    from app.core.config import get_settings

    get_settings.cache_clear()
    for clave, valor in {**SECRETOS, **variables}.items():
        monkeypatch.setenv(clave, valor)
    try:
        return get_settings()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("variables,fragmento", [
    ({}, "está vacío"),
    ({"PROXIES_DE_CONFIANZA": "0.0.0.0/0", "CABECERA_IP_CLIENTE": "x-forwarded-for"},
     "demasiado amplia"),
    ({"PROXIES_DE_CONFIANZA": "0.0.0.0/1", "CABECERA_IP_CLIENTE": "x-forwarded-for"},
     "demasiado amplia"),      # rechazar solo /0 no basta: /1 cubre media internet
    ({"PROXIES_DE_CONFIANZA": "10.0.0.5/32"}, "CABECERA_IP_CLIENTE está vacía"),
    ({"PROXIES_DE_CONFIANZA": "ninguno", "CABECERA_IP_CLIENTE": "cf-connecting_ip"},
     "no está admitida"),
    ({"PROXIES_DE_CONFIANZA": "10.0.0.5/32, 203.0.113.999",
      "CABECERA_IP_CLIENTE": "x-forwarded-for"}, "ilegibles"),
    ({"PROXIES_DE_CONFIANZA": "ninguno", "SALTOS_DE_PROXY": "0"}, "fuera de rango"),
    ({"PROXIES_DE_CONFIANZA": "ninguno", "SALTOS_DE_PROXY": "99"}, "fuera de rango"),
])
def test_una_politica_de_proxy_incoherente_aborta_el_arranque(variables, fragmento,
                                                              monkeypatch):
    """El modo de fallo más caro no es la falsificación: es el olvido.

    Desplegar tras un proxy sin declararlo deja el límite por origen como cupo
    global, todo funciona, nadie nota nada — y la deuda que este bloque cierra
    reaparece ya en internet y sin nadie mirando. Un arranque abortado cuesta
    medio minuto; ese silencio no se detecta nunca.
    """
    from app.core.config import ConfiguracionInseguraError

    # `match=` y no solo el tipo: `ConfiguracionInseguraError` es la clase BASE de
    # los errores de secretos, de entorno y de purgas, así que sin el fragmento
    # estos casos quedarían verdes con un aborto disparado por cualquier otra
    # guardia — el parámetro `motivo` era decorativo.
    for clave in variables:
        monkeypatch.delenv(clave, raising=False)
    with pytest.raises(ConfiguracionInseguraError, match=fragmento):
        _arrancar(monkeypatch, SEIS_ENV="production", **variables)


def test_declarar_ninguno_es_una_salida_legitima(monkeypatch):
    """Distinguir «no hay proxy» de «se me olvidó» es justo lo que da valor a la
    guardia: sin el centinela, la única forma de arrancar sería mentir."""
    ajustes = _arrancar(monkeypatch, SEIS_ENV="production",
                        PROXIES_DE_CONFIANZA="ninguno")

    assert ajustes.proxies_de_confianza == "ninguno"


def test_en_desarrollo_no_se_exige_declarar_nada(monkeypatch):
    """La suite y el flujo local no cambian."""
    assert _arrancar(monkeypatch, SEIS_ENV="development").proxies_de_confianza == ""


# ─────────── Integración con el limitador ───────────

def _cliente(par: str):
    """TestClient con un par TCP concreto, que es lo que decide la confianza."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, client=(par, 1234))


def test_una_ip_falsificada_no_elude_el_bloqueo_por_fuerza_bruta(api, monkeypatch):
    """TEST CAPITAL DEL BLOQUE.

    Sin proxies declarados, seis intentos fallidos con un `X-Forwarded-For`
    **distinto en cada uno** deben acabar en 429. Si alguien decidiera algún día
    fiarse de la cabecera a ciegas, este test se pondría rojo — y sin él, el
    anti-fuerza-bruta de la Fase 10 pasaría de existir a ser decorativo sin que
    nada lo delatase.
    """
    from app.core import rate_limit

    rate_limit.limpiar_todo()
    monkeypatch.setattr(red, "politica_actual", lambda: _politica(csv=""))

    codigos = []
    for i in range(6):
        r = api.post("/api/v1/auth/login",
                     data={"username": "victima@example.com", "password": "mala"},
                     headers={"X-Forwarded-For": f"{i + 1}.{i + 1}.{i + 1}.{i + 1}"})
        codigos.append(r.status_code)

    assert codigos[-1] == 429, (
        f"rotando la IP falsificada se eludió el bloqueo: {codigos}")
    rate_limit.limpiar_todo()


def test_tras_un_proxy_declarado_dos_clientes_no_comparten_cupo(api, monkeypatch):
    """Demuestra que la deuda queda CERRADA, no solo que no se puede falsificar.

    Bajo `docker compose` todas las peticiones llegaban con la IP de la pasarela,
    de modo que el límite de `/registro` era un cupo global —5 altas cada 15
    minutos en TODO el sitio— y un solo atacante podía negar el alta pública.
    Con la política activa, cada cliente gasta el suyo.
    """
    from app.core import rate_limit

    rate_limit.limpiar_todo()
    monkeypatch.setattr(red, "politica_actual", lambda: _politica())
    cliente = _cliente(PROXY)

    def _registrar(ip_real: str):
        # `uuid4` y no `id(object())`: CPython reutiliza la dirección del objeto
        # recién liberado, así que aquello devolvía el MISMO valor en llamadas
        # seguidas y los seis registros usaban el mismo email. Pasaba
        # desapercibido solo porque /registro responde 201 exista o no la cuenta.
        return cliente.post("/api/v1/auth/registro",
                            json={"email": f"{uuid.uuid4().hex[:12]}@example.com",
                                  "password": "unaClaveLarga123", "nombre": "X"},
                            headers={"X-Forwarded-For": ip_real})

    codigos = [_registrar("203.0.113.10").status_code for _ in range(6)]
    # Sin afirmar que el PRIMER cliente se bloqueó, el test no distingue «cada
    # uno tiene su cupo» de «no hay cupo en absoluto»: con el limitador entero
    # desactivado también pasaría.
    assert codigos[-1] == 429, f"el primer cliente no llegó a bloquearse: {codigos}"

    otro = _registrar("203.0.113.20")

    # `== 201` y no `!= 429`: un 500 o un 422 también cumplen «no es 429», de
    # modo que el test podía quedarse verde midiendo otra cosa.
    assert otro.status_code == 201, (
        f"un cliente agotó el cupo de otro (o falló por otro motivo): "
        f"{otro.status_code}")
    rate_limit.limpiar_todo()

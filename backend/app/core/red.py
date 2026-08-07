"""Resolución de la IP real del cliente tras proxy (Fase 11, Bloque H).

Cierra la puerta de despliegue heredada de la Fase 10: bajo `docker compose` el
reenvío del puerto publicado no conserva la IP de origen —medido: todas las
peticiones externas llegan con la de la pasarela—, de modo que los límites por
origen de `/registro` y `/reenviar-verificacion` funcionan como **un cupo global**
y un solo atacante sin credenciales puede negar el alta pública a todo el sitio.

**El defecto de fábrica es el seguro.** Con `PROXIES_DE_CONFIANZA` vacío no se
lee ninguna cabecera, pase lo que pase con las otras dos variables: el
comportamiento es exactamente el de antes de este módulo. Es deliberado que haya
**una sola puerta** y no tres.

**Por qué no basta con `X-Forwarded-For`.** Esa cabecera la escribe cualquiera.
Sin proxy de confianza declarado, fiarse de ella permite eludir por completo el
anti-fuerza-bruta enviando una IP distinta en cada intento.

**Por qué no se salta por pertenencia.** Lo que hacen uvicorn moderno y varias
bibliotecas —recorrer XFF de derecha a izquierda descartando las IPs que estén
en la lista de confianza— es **vulnerable**: el atacante envía
`XFF: 6.6.6.6, <una IP de la lista>`, el recorrido descarta la inyectada y
devuelve la falsa. Con Cloudflare es trivial, porque **sus rangos son públicos**.
Aquí se toma el N-ésimo por la derecha con **N fijo declarado**: no se miran los
valores, solo se cuentan posiciones, así que no hay nada que inyectar. Un
prefijo falsificado empuja hacia la izquierda, nunca hacia la posición leída.
"""
from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network

from app.core.config import get_settings

IP_DESCONOCIDA = "desconocida"

# Centinela de `PROXIES_DE_CONFIANZA`: «no hay proxy delante, y lo declaro».
SIN_PROXY = "ninguno"

# Lista blanca de cabeceras admitidas. Que sea cerrada impide que una errata en
# el `.env` —`cf-connecting_ip` por `cf-connecting-ip`— desactive la resolución
# sin que nadie lo note.
CABECERAS_ADMITIDAS = ("x-forwarded-for", "cf-connecting-ip",
                       "true-client-ip", "x-real-ip")

# Solo `x-forwarded-for` es una lista de saltos; el resto son de valor único, y
# esa diferencia decide cómo se extrae el valor.
CABECERAS_DE_LISTA = ("x-forwarded-for",)

# Topes defensivos: una cabecera desmesurada se descarta entera en vez de
# recorrerse.
MAX_ELEMENTOS = 16
MAX_LONGITUD_CABECERA = 1024

# Prefijo al que se agrega IPv6 para contar. Un cliente doméstico con un /64
# rota direcciones a voluntad, de modo que limitar por dirección exacta
# equivaldría a no limitar.
PREFIJO_IPV6 = 64

# Prefijos mínimos exigidos a una red de confianza. Rechazar solo `/0` no basta:
# `0.0.0.0/1` más `128.0.0.0/1` cubren todo IPv4 y pasarían. Un proxy propio se
# declara con una IP o un bloque pequeño; una red enorme «de confianza» es casi
# siempre un error de configuración, no una topología.
PREFIJO_MINIMO_IPV4 = 16
PREFIJO_MINIMO_IPV6 = 32


@dataclass(frozen=True)
class PoliticaProxy:
    """Qué proxies son de confianza, de qué cabecera fiarse y a qué profundidad."""
    redes: tuple[IPv4Network | IPv6Network, ...]
    cabecera: str
    saltos: int

    def __post_init__(self) -> None:
        # La invariante viaja con el TIPO y no con una de sus fábricas: con
        # `saltos=0`, `valores[-0]` devuelve el PRIMER elemento, que es justo el
        # que escribe el cliente. Nadie debe poder construir esa política.
        if self.saltos < 1:
            raise ValueError("saltos_de_proxy debe ser >= 1")

    @property
    def activa(self) -> bool:
        """Sin redes declaradas o sin cabecera, no se lee nada. Falla en cerrado."""
        return bool(self.redes) and bool(self.cabecera)


def parsear_redes(csv: str) -> tuple[IPv4Network | IPv6Network, ...]:
    """Convierte el CSV de `PROXIES_DE_CONFIANZA` en redes. Ignora lo ilegible.

    Un valor mal escrito se descarta en lugar de ampliarse: el error cae del lado
    de leer menos cabeceras, nunca del de confiar en más proxies. Para saber
    **qué** se descartó —y abortar el arranque por ello— está `redes_invalidas`.
    """
    return tuple(red for red, _ in _analizar_redes(csv)[0])


def redes_invalidas(csv: str) -> list[str]:
    """Entradas de `PROXIES_DE_CONFIANZA` que no se pudieron interpretar.

    Descartarlas en silencio degradaba la confianza sin avisar: con
    `10.0.0.5/32, 203.0.113.999` el sistema arrancaba fiándose de un proxy de los
    dos, y todo el tráfico del segundo volvía a caer en el cupo global.
    """
    return _analizar_redes(csv)[1]


def _analizar_redes(csv: str):
    if not csv or csv.strip().lower() == SIN_PROXY:
        return [], []
    validas, invalidas = [], []
    for trozo in csv.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        try:
            validas.append((ip_network(trozo, strict=False), trozo))
        except ValueError:
            invalidas.append(trozo)
    return validas, invalidas


def politica_actual() -> PoliticaProxy:
    s = get_settings()
    cabecera = s.cabecera_ip_cliente.strip().lower()
    # La lista blanca se aplica también AQUÍ y no solo en la guardia de arranque:
    # aquella únicamente corre en entornos estrictos, así que sin esto una
    # cabecera arbitraria configurada en desarrollo sí se leería. Defensa en
    # profundidad: si el nombre no está admitido, la política queda inactiva.
    if cabecera not in CABECERAS_ADMITIDAS:
        cabecera = ""
    return PoliticaProxy(redes=parsear_redes(s.proxies_de_confianza),
                         cabecera=cabecera,
                         saltos=max(1, min(s.saltos_de_proxy, MAX_ELEMENTOS)))


def es_par_de_confianza(par: str, politica: PoliticaProxy) -> bool:
    """¿El extremo TCP que nos habla es uno de nuestros proxies declarados?"""
    try:
        direccion = ip_address(par)
    except ValueError:
        # `testclient`, `desconocida` o un nombre de host: nunca de confianza.
        return False
    # Un socket dual-stack o un proxy sobre uno (Envoy, HAProxy, Traefik) entrega
    # la forma `::ffff:a.b.c.d`. Sin normalizarla, el proxy declarado deja de
    # reconocerse y el sistema vuelve al cupo global en silencio.
    mapeada = getattr(direccion, "ipv4_mapped", None)
    if mapeada is not None:
        direccion = mapeada
    return any(direccion in red for red in politica.redes)


def _normalizar(valor: str) -> str:
    """Quita corchetes, puerto y zona de un valor de cabecera."""
    valor = valor.strip()
    if valor.startswith("["):                       # [2001:db8::1]:443
        valor = valor[1:].split("]")[0]
    elif valor.count(":") == 1:                     # 192.0.2.1:1234
        valor = valor.split(":")[0]
    return valor.split("%")[0]


def resolver_ip(par: str, crudos: list[str], politica: PoliticaProxy) -> str:
    """Devuelve la IP del cliente. Ante cualquier anomalía, el par TCP.

    Función pura: recibe los valores crudos de la cabecera, no la petición, para
    que la parte delicada sea comprobable sin montar HTTP.
    """
    if not politica.activa:
        return par
    if not es_par_de_confianza(par, politica):
        return par
    # RFC 7230 §3.2.2: varias cabeceras del mismo nombre equivalen a una lista.
    bruto = ",".join(crudos)
    if not bruto or len(bruto) > MAX_LONGITUD_CABECERA:
        return par
    valores = [v.strip() for v in bruto.split(",") if v.strip()]
    if not valores or len(valores) > MAX_ELEMENTOS:
        return par

    if politica.cabecera in CABECERAS_DE_LISTA:
        # Si la cadena es más corta que los saltos declarados, alguien la ha
        # acortado: se descarta en vez de leer una posición que no corresponde.
        if len(valores) < politica.saltos:
            return par
        # Y las posiciones que quedan A LA DERECHA de la leída deben ser todas
        # proxies de confianza. Sin esta comprobación, contar posiciones falla en
        # una topología real: con `Cloudflare → nginx → uvicorn` y saltos=2, un
        # atacante que alcance nginx **directamente** manda `XFF: 6.6.6.6, 1.2.3.4`,
        # nginx añade la suya, y la posición -2 pasa a ser un valor que el
        # atacante eligió. Exigir que la cola sean proxies conocidos conserva la
        # inmunidad a inyectar una IP de la lista —no se decide QUÉ leer mirando
        # valores, solo se valida lo ya leído— y cierra ese caso.
        cola = valores[len(valores) - politica.saltos + 1:]
        if any(not es_par_de_confianza(_normalizar(v), politica) for v in cola):
            return par
        candidato = valores[-politica.saltos]
    else:
        # Cabecera de valor único: más de un valor significa manipulación.
        if len(valores) != 1:
            return par
        candidato = valores[0]
        # ⚠️ ASIMETRÍA DELIBERADA, y es la parte frágil del módulo.
        #
        # Con `x-forwarded-for` el valor leído está protegido DOS veces: por
        # posición fija y por la validación de la cola. Aquí no hay nada de eso:
        # se acepta el valor íntegro con la única condición de que el par TCP sea
        # de confianza. Es decir, **el proxy es el único control que queda**.
        #
        # Consecuencia si el proxy no borra la cabecera en las peticiones que
        # entran de internet —y nginx, por defecto, NO la borra—: el cliente
        # elige su propia identidad en cada petición y elude por completo el
        # anti-fuerza-bruta del login y el cupo de alta pública. Es exactamente
        # el defecto que este módulo existe para cerrar, reintroducido por una
        # omisión de configuración que no da ningún síntoma.
        #
        # Por eso `cf-connecting-ip` y `true-client-ip` son cómodas (evitan
        # `SALTOS_DE_PROXY`) pero NO más seguras: trasladan la garantía entera
        # del código al proxy inverso. Quien las use debe borrar o reescribir la
        # cabecera en el borde. Requisito duro del despliegue (Fase 11-B).

    candidato = _normalizar(candidato)
    try:
        ip_address(candidato)
    except ValueError:
        return par
    return candidato


def ip_cliente(peticion) -> str:
    """IP del cliente para una petición de Starlette/FastAPI."""
    par = peticion.client.host if peticion.client else IP_DESCONOCIDA
    politica = politica_actual()
    if not politica.activa:
        return par
    crudos = peticion.headers.getlist(politica.cabecera)
    return resolver_ip(par, list(crudos), politica)


def clave_de_origen(ip: str) -> str:
    """Normaliza la IP para usarla como clave del limitador.

    IPv6 se agrega a su /64: un cliente doméstico dispone de ese bloque entero y
    puede cambiar de dirección en cada petición, de modo que contar por dirección
    exacta sería no contar. IPv4 y los valores que no son IP pasan tal cual —eso
    último mantiene intactas las claves `testclient` de la suite.
    """
    try:
        direccion = ip_address(ip)
    except ValueError:
        return ip
    # IPv4 mapeada a IPv6 (`::ffff:1.2.3.4`) ANTES de decidir por versión: si no,
    # todas ellas colapsan en `::/64` y **todos los clientes IPv4 comparten un
    # único contador**, que es exactamente el cupo global que este bloque cierra.
    # Ocurriría con un socket dual-stack (`--host ::`) o con un proxy que emita
    # esa forma en la cabecera, cosa habitual en balanceadores y proxies sobre
    # Node. Hoy el compose usa `--host 0.0.0.0` y no se dispara; es un pie armado.
    mapeada = getattr(direccion, "ipv4_mapped", None)
    if mapeada is not None:
        return str(mapeada)
    if direccion.version == 4:
        return ip
    return str(ip_network(f"{ip}/{PREFIJO_IPV6}", strict=False))

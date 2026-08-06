"""Configuración central de SEIS (T4: entorno explícito, sin sorpresas)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    app_name: str = "SEIS — Sistema Experto de Inversión en Subastas"
    api_v1_prefix: str = "/api/v1"
    seis_env: str = "development"          # development | test | staging | production
    database_url: str = "sqlite:///./seis_dev.db"      # en producción: postgresql+psycopg2://...
    redis_url: str = "redis://localhost:6379/0"
    seis_cors_origins: str = "http://localhost:3000"

    # Seguridad (Fase 2)
    jwt_secret: str = "cambia-este-secreto-en-produccion"
    jwt_exp_horas: int = 12
    admin_email: str = "admin@seis.local"
    admin_password: str = "admin"          # SOLO bootstrap; cambiar en el primer arranque

    # Anti-abuso (Fase 10): ventana deslizante del login y de los endpoints
    # públicos que envían correo. Ver app/core/rate_limit.py.
    login_max_intentos: int = 5
    login_ventana_min: int = 15

    # Mantenimiento (Fase 11, Bloque I): días que se conserva un `jti` gastado
    # antes de purgarlo. DEBE superar el TTL del token de un solo uso más largo
    # —ver `TTL_MAXIMO_JTI_HORAS` más abajo, que explica cuál es y por qué NO es
    # el que parece—, porque el `jti` es lo único que impide reutilizar un
    # enlace: borrarlo antes de tiempo devuelve el uso único.
    purga_tokens_dias: int = 45

    # Purga de cuentas registradas y nunca verificadas (deuda 10).
    # `informar` por defecto, a propósito: el mecanismo se entrega completo y
    # probado, pero un borrado irreversible no debe ser el comportamiento por
    # defecto de algo que aún no se ha visto correr contra datos reales. Pasar a
    # `borrar` es una variable de entorno, no un despliegue de código.
    purga_cuentas_modo: str = "informar"          # informar | borrar
    # 30 veces el TTL del enlace de verificación (24 h). Más corto castigaría a
    # quien se registra antes de un viaje; mucho más largo equivale a no purgar.
    purga_cuentas_dias: int = 30

    # Salud por componente (Fase 11): techo de espera de cada sonda de
    # /health/listo. Corto a propósito — una sonda que tarda más que el intervalo
    # de sondeo del balanceador es inútil. Ver app/api/salud.py.
    health_timeout_segundos: float = 2.0

    # Celery
    celery_task_always_eager: bool = False # True en tests: ejecuta tareas en proceso

    # Notificaciones (Fase 12)
    frontend_url: str = "http://localhost:3000"
    email_provider: str = ""               # postmark | ses | smtp | "" (sin proveedor: log + buffer)
    email_from: str = "noreply@seis.local"
    postmark_token: str = ""
    ses_region: str = ""
    ses_access_key: str = ""
    ses_secret_key: str = ""
    smtp_host: str = ""
    smtp_puerto: int = 587
    smtp_usuario: str = ""
    smtp_password: str = ""
    telegram_bot_token: str = ""
    telegram_bot_nombre: str = ""          # para el deep-link t.me/<bot>?start=CODIGO

    # Versiones activas del conocimiento (P1/P3: cada análisis las congela en su snapshot)
    version_reglas: str = "2026.07"
    version_parametros: str = "2026.07"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.seis_cors_origins.split(",") if o.strip()]


class ConfiguracionInseguraError(RuntimeError):
    """Base de los errores que abortan el arranque por configuración insegura."""


class EntornoNoSoportadoError(ConfiguracionInseguraError):
    """`SEIS_ENV` tiene un valor que el sistema no reconoce.

    Corrección del hallazgo P1-1: antes la validación se activaba solo con la
    grafía exacta `production`, de modo que cualquier otro valor —una errata
    plausible como `produccion` o `prod`— **desactivaba en silencio** todo el
    control de secretos. Un entorno desconocido ya no se ignora: se rechaza de
    forma explícita, porque no es posible decidir con qué rigor tratarlo.
    """


class SecretoInseguroError(ConfiguracionInseguraError):
    """El arranque en un entorno estricto se niega si algún secreto no es propio y fuerte.

    Corrección de raíz del hallazgo C1: la versión anterior comparaba contra una
    lista de cadenas concretas, de modo que cualquier placeholder distinto de las
    dos previstas —incluido el que el propio `.env.example` entregaba— pasaba el
    control y desplegaba en producción con secretos publicados en el repositorio.

    Ahora la validación es ESTRUCTURAL y no depende de conocer un valor concreto:
    se exige longitud, variedad de caracteres y ausencia de marcadores propios de
    una plantilla, y se compara contra el valor por defecto leído del propio
    modelo (no contra una cadena escrita a mano). Un secreto de ejemplo, de
    plantilla o trivialmente débil no puede arrancar en un entorno estricto, lo
    haya escrito el repositorio o una persona.

    Se llamaba `SecretoInseguroEnProduccionError` hasta la Fase 11. El nombre dejó
    de ser cierto al entrar `staging` en `ENTORNOS_ESTRICTOS`: la excepción ya no
    habla solo de producción, y un nombre que miente en una traza cuesta más de lo
    que ahorra no renombrarlo.
    """


# Entornos reconocidos. Cualquier otro valor aborta el arranque (P1-1): no se
# ignora en silencio, porque ignorarlo desactivaría la validación de secretos.
ENTORNOS_SOPORTADOS = ("development", "test", "staging", "production")

# Entornos que exigen secretos propios y fuertes.
#
# `staging` entra aquí junto a `production` (Fase 11, Bloque D) y no es una
# formalidad: un staging es una réplica del sistema real, alcanzable desde
# internet y a menudo poblada con una copia de los datos de producción. Admitirlo
# como entorno soportado pero laxo habría creado la peor combinación posible —una
# puerta con la misma superficie que producción y la guardia de secretos
# desactivada—, que es justo lo que el hallazgo P1-1 vino a cerrar. Si un entorno
# merece existir en internet, merece secretos propios.
ENTORNOS_ESTRICTOS = ("staging", "production")

# Campos que en producción deben ser secretos propios y fuertes.
_CAMPOS_SECRETOS = ("jwt_secret", "admin_password")

_LONGITUD_MINIMA = {"jwt_secret": 32, "admin_password": 12}
_VARIEDAD_MINIMA = 8          # nº de caracteres distintos exigidos

# Fragmentos propios de un valor de plantilla o de ejemplo. Se buscan como
# SUBCADENA (no por igualdad), de modo que la comprobación no depende de conocer
# el placeholder exacto: cubre los del repositorio y los que improvise cualquiera.
_MARCADORES_PLANTILLA = (
    "cambia", "cambiar", "change", "changeme", "reemplaza", "replace",
    "ejemplo", "example", "sample", "placeholder", "plantilla",
    "tu-", "tu_", "your-", "your_", "xxx", "todo", "default", "defecto",
    "secreto", "secret", "password", "passwd", "contrasena", "contraseña",
    "clave", "admin", "test", "demo", "prueba", "insegur", "aleatorio", "12345",
)


def _motivo_inseguro(campo: str, valor: str, valor_defecto: object) -> str | None:
    """Devuelve el motivo por el que el secreto es inaceptable, o None si es válido."""
    if not valor or not valor.strip():
        return "está vacío"
    if valor == valor_defecto:
        return "conserva el valor por defecto del código"
    minimo = _LONGITUD_MINIMA[campo]
    if len(valor) < minimo:
        return f"tiene {len(valor)} caracteres (mínimo {minimo})"
    if len(set(valor)) < _VARIEDAD_MINIMA:
        return (f"solo usa {len(set(valor))} caracteres distintos "
                f"(mínimo {_VARIEDAD_MINIMA}): es demasiado predecible")
    minusculas = valor.lower()
    for marcador in _MARCADORES_PLANTILLA:
        if marcador in minusculas:
            return f"contiene «{marcador}», propio de un valor de ejemplo o plantilla"
    return None


def entorno_normalizado(seis_env: str) -> str:
    """Normaliza y VALIDA `SEIS_ENV`; lanza si el entorno no está soportado.

    Corrección de P1-1: la seguridad no puede depender de que el operador escriba
    exactamente «production». Se aceptan mayúsculas y espacios, pero un valor
    desconocido (`produccion`, `prod`, `stagging`…) **no se ignora en silencio**:
    se rechaza el arranque, porque un entorno que el sistema no reconoce no
    permite decidir con qué rigor validar los secretos. Fallar en cerrado.

    Ojo con las erratas de `staging`: `stagging` o `stage` NO son el entorno
    staging, son entornos desconocidos, y por tanto abortan. Es deliberado —
    admitir grafías aproximadas reabriría por la puerta de atrás el agujero que
    P1-1 cerró.
    """
    entorno = (seis_env or "").strip().lower()
    if entorno not in ENTORNOS_SOPORTADOS:
        raise EntornoNoSoportadoError(
            f"Arranque abortado: SEIS_ENV={seis_env!r} no es un entorno soportado.\n"
            f"Valores admitidos: {', '.join(ENTORNOS_SOPORTADOS)}.\n"
            "Un valor desconocido dejaría sin aplicar la validación de secretos, "
            "así que el arranque se detiene en lugar de continuar sin protección. "
            "Si se refiere al entorno productivo, escriba exactamente «production».")
    return entorno


def _validar_seguridad_entorno(s: "Settings") -> None:
    """Aborta el arranque si el entorno no está soportado o los secretos son débiles.

    En los entornos de `ENTORNOS_ESTRICTOS` (`staging` y `production`) se exige
    que los secretos sean propios y fuertes; en `development` y `test` no se
    aplica (comportamiento intacto para la suite). Falla en cerrado a propósito —
    es preferible que un secreto legítimo sea rechazado por parecerse a una
    plantilla (y se regenere) a que uno de ejemplo llegue a internet.
    """
    entorno = entorno_normalizado(s.seis_env)
    if entorno not in ENTORNOS_ESTRICTOS:
        return
    problemas = []
    for campo in _CAMPOS_SECRETOS:
        # El valor por defecto se lee del propio modelo: la comprobación no
        # depende de que nadie recuerde actualizar una cadena escrita a mano.
        defecto = Settings.model_fields[campo].default
        motivo = _motivo_inseguro(campo, getattr(s, campo), defecto)
        if motivo:
            problemas.append(f"  · {campo.upper()}: {motivo}")
    if problemas:
        # El mensaje nombra el entorno REAL y no «production» a secas: con staging
        # ya en la lista, un texto que solo hablara de producción llevaría a quien
        # despliega a buscar el fallo en el sitio equivocado.
        raise SecretoInseguroError(
            f"Arranque abortado: SEIS_ENV={entorno} es un entorno estricto y exige "
            "secretos propios y fuertes, y estos no lo son:\n" + "\n".join(problemas) +
            "\n\nGenere valores únicos antes de desplegar, por ejemplo:\n"
            "  JWT_SECRET=$(openssl rand -base64 48)\n"
            "  ADMIN_PASSWORD=$(openssl rand -base64 18)\n"
            "Nunca reutilice los valores de .env.example ni de la documentación: "
            "son públicos.")


# TTL máximo, en horas, de un token que llega a reclamar su `jti`.
#
# NO es el token de vida más larga del proyecto. El de baja dura 30 días, pero
# `/notificaciones/baja` **no llama a `marcar_jti`** —darse de baja dos veces es
# inocuo—, así que nunca entra en `token_consumido`. Los únicos que sí entran son
# los de verificación (24 h) y reseteo (1 h), ambos por `_consumir_token` en
# `app/api/auth.py`, que es el único llamante de `marcar_jti`.
#
# El valor se declara aquí y no se importa de `registro_service` porque ese
# módulo importa esta configuración y habría ciclo. Lo que impide que se quede
# obsoleto es un test que lo deriva del código real: si alguien alarga el TTL de
# verificación por encima de esta cifra, ese test se pone rojo.
TTL_MAXIMO_JTI_HORAS = 24

# Suelo de la ventana de purga de cuentas. Por debajo, la purga deja de limpiar
# abandonos y empieza a castigar a usuarios legítimos: quien se registra un
# viernes y abre el correo el lunes.
PURGA_CUENTAS_DIAS_MINIMO = 7


def _validar_purgas(s: "Settings") -> None:
    """Aborta el arranque si los plazos de purga pueden destruir datos legítimos.

    El módulo de purga presume como principio que «una errata en la variable de
    entorno nunca borra», y lo cumple para `PURGA_CUENTAS_MODO`, que falla en
    cerrado ante un valor desconocido. **No lo cumplía para los números**, que son
    el otro parámetro que decide a quién alcanza el borrado: `PURGA_CUENTAS_DIAS=3`
    —una errata plausible, se cae el cero de 30— es un entero perfectamente
    válido para Pydantic, no llama la atención en ningún log, y la ejecución
    nocturna borra de forma irreversible todas las altas de más de tres días.

    Y `PURGA_TOKENS_DIAS` demasiado bajo es peor que un borrado: el `jti` es lo
    único que impide reutilizar un enlace de un solo uso, así que purgarlo antes
    de que el token caduque **reabre el uso único** que la Fase 10 cerró.
    """
    problemas = []
    if s.purga_cuentas_dias < PURGA_CUENTAS_DIAS_MINIMO:
        problemas.append(
            f"  · PURGA_CUENTAS_DIAS={s.purga_cuentas_dias}: el mínimo es "
            f"{PURGA_CUENTAS_DIAS_MINIMO} días. Por debajo, la purga borra altas "
            "de usuarios que todavía podían verificarse.")

    minimo_tokens = TTL_MAXIMO_JTI_HORAS / 24
    if s.purga_tokens_dias <= minimo_tokens:
        problemas.append(
            f"  · PURGA_TOKENS_DIAS={s.purga_tokens_dias}: debe superar "
            f"ESTRICTAMENTE los {minimo_tokens:g} días que vive el token de un "
            "solo uso más largo; si no, la purga puede devolverle un uso a un "
            "enlace ya consumido.")

    if problemas:
        raise ConfiguracionInseguraError(
            "Arranque abortado: los plazos de purga destruirían datos que aún no "
            "deben tocarse.\n" + "\n".join(problemas))


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    _validar_seguridad_entorno(s)
    # Se valida en TODOS los entornos, no solo en los estrictos: un borrado
    # irreversible mal configurado es igual de destructivo en desarrollo.
    _validar_purgas(s)
    return s

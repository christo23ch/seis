"""Configuración central de SEIS (T4: entorno explícito, sin sorpresas)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    app_name: str = "SEIS — Sistema Experto de Inversión en Subastas"
    api_v1_prefix: str = "/api/v1"
    seis_env: str = "development"                      # development | production | test
    database_url: str = "sqlite:///./seis_dev.db"      # en producción: postgresql+psycopg2://...
    redis_url: str = "redis://localhost:6379/0"
    seis_cors_origins: str = "http://localhost:3000"

    # Seguridad (Fase 2)
    jwt_secret: str = "cambia-este-secreto-en-produccion"
    jwt_exp_horas: int = 12
    admin_email: str = "admin@seis.local"
    admin_password: str = "admin"          # SOLO bootstrap; cambiar en el primer arranque

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


class SecretoInseguroEnProduccionError(ConfiguracionInseguraError):
    """El arranque en producción se niega si algún secreto no es propio y fuerte.

    Corrección de raíz del hallazgo C1: la versión anterior comparaba contra una
    lista de cadenas concretas, de modo que cualquier placeholder distinto de las
    dos previstas —incluido el que el propio `.env.example` entregaba— pasaba el
    control y desplegaba en producción con secretos publicados en el repositorio.

    Ahora la validación es ESTRUCTURAL y no depende de conocer un valor concreto:
    se exige longitud, variedad de caracteres y ausencia de marcadores propios de
    una plantilla, y se compara contra el valor por defecto leído del propio
    modelo (no contra una cadena escrita a mano). Un secreto de ejemplo, de
    plantilla o trivialmente débil no puede arrancar en producción, lo haya
    escrito el repositorio o una persona.
    """


# Entornos reconocidos. Cualquier otro valor aborta el arranque (P1-1): no se
# ignora en silencio, porque ignorarlo desactivaría la validación de secretos.
ENTORNOS_SOPORTADOS = ("development", "test", "production")
ENTORNOS_ESTRICTOS = ("production",)          # exigen secretos propios y fuertes

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
    desconocido (`produccion`, `prod`, `staging`…) **no se ignora en silencio**:
    se rechaza el arranque, porque un entorno que el sistema no reconoce no
    permite decidir con qué rigor validar los secretos. Fallar en cerrado.
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


def _validar_seguridad_produccion(s: "Settings") -> None:
    """Aborta el arranque si el entorno no está soportado o los secretos son débiles.

    En `production` se exige que los secretos sean propios y fuertes; en
    `development` y `test` no se aplica (comportamiento intacto para la suite).
    Falla en cerrado a propósito — es preferible que un secreto legítimo sea
    rechazado por parecerse a una plantilla (y se regenere) a que uno de ejemplo
    llegue a producción.
    """
    if entorno_normalizado(s.seis_env) not in ENTORNOS_ESTRICTOS:
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
        raise SecretoInseguroEnProduccionError(
            "Arranque abortado: SEIS_ENV=production exige secretos propios y "
            "fuertes, y estos no lo son:\n" + "\n".join(problemas) +
            "\n\nGenere valores únicos antes de desplegar, por ejemplo:\n"
            "  JWT_SECRET=$(openssl rand -base64 48)\n"
            "  ADMIN_PASSWORD=$(openssl rand -base64 18)\n"
            "Nunca reutilice los valores de .env.example ni de la documentación: "
            "son públicos.")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    _validar_seguridad_produccion(s)
    return s

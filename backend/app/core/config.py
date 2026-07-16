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

    # Versiones activas del conocimiento (P1/P3: cada análisis las congela en su snapshot)
    version_reglas: str = "2026.07"
    version_parametros: str = "2026.07"

    # Observabilidad (Fase 11)
    sentry_dsn: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.seis_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

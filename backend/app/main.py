"""Aplicación FastAPI de SEIS."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.conocimiento import router as conocimiento_router
from app.api.organizacion import router as organizacion_router
from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

# Validación fail-fast en producción (Fase 11)
if settings.seis_env == "production":
    peligros = [
        (settings.jwt_secret == "cambia-este-secreto-en-produccion", "JWT_SECRET es el de fábrica"),
        (settings.admin_password == "admin", "ADMIN_PASSWORD es el de fábrica"),
        (settings.database_url.startswith("sqlite://"), "DATABASE_URL apunta a SQLite, no PostgreSQL"),
    ]
    for es_peligro, mensaje in peligros:
        if es_peligro:
            raise RuntimeError(
                f"❌ CONFIGURACIÓN INVÁLIDA EN PRODUCCIÓN: {mensaje}\n"
                f"   Verifica las variables de entorno antes de desplegar."
            )

# Integración de Sentry (Fase 11, opcional si SENTRY_DSN existe)
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        environment=settings.seis_env,
        traces_sample_rate=0.1 if settings.seis_env == "production" else 1.0,
    )

app = FastAPI(
    title=settings.app_name,
    version="1.0.0-fase1",
    description="Sistema Experto de Inversión en Subastas — motor determinista, "
                "auditable y explicable según la especificación funcional y técnica v1.0.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(conocimiento_router, prefix=settings.api_v1_prefix)
app.include_router(organizacion_router, prefix=settings.api_v1_prefix)

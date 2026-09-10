"""Aplicación FastAPI de SEIS."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.captacion import router as captacion_router
from app.api.conocimiento import router as conocimiento_router
from app.api.cuenta import router as cuenta_router
from app.api.cuenta import router_legal as legal_router
from app.api.notificaciones import router as notificaciones_router
from app.api.notificaciones import router_alertas as alertas_router
from app.api.organizacion import router as organizacion_router
from app.api.routes import router
from app.api.salud import router as salud_router
from app.core.cabeceras import CabecerasDeSeguridad
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0-fase1",
    description="Sistema Experto de Inversión en Subastas — motor determinista, "
                "auditable y explicable según la especificación funcional y técnica v1.0.",
)
# El de seguridad se añade ANTES que el de CORS. Starlette ejecuta los
# middlewares en orden inverso al de registro, de modo que CORS envuelve a este y
# sus respuestas de preflight también salen con las cabeceras.
app.add_middleware(CabecerasDeSeguridad)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(conocimiento_router, prefix=settings.api_v1_prefix)
app.include_router(organizacion_router, prefix=settings.api_v1_prefix)
app.include_router(captacion_router, prefix=settings.api_v1_prefix)
app.include_router(notificaciones_router, prefix=settings.api_v1_prefix)
app.include_router(alertas_router, prefix=settings.api_v1_prefix)
app.include_router(cuenta_router, prefix=settings.api_v1_prefix)
app.include_router(legal_router, prefix=settings.api_v1_prefix)
app.include_router(salud_router, prefix=settings.api_v1_prefix)

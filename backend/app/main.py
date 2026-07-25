"""Aplicación FastAPI de SEIS."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.captacion import router as captacion_router
from app.api.conocimiento import router as conocimiento_router
from app.api.notificaciones import router as notificaciones_router
from app.api.notificaciones import router_alertas as alertas_router
from app.api.organizacion import router as organizacion_router
from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

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
app.include_router(captacion_router, prefix=settings.api_v1_prefix)
app.include_router(notificaciones_router, prefix=settings.api_v1_prefix)
app.include_router(alertas_router, prefix=settings.api_v1_prefix)

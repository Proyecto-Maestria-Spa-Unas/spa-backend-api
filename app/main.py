"""Monolito modular: los 4 servicios de dominio bajo /api/v1 (ADR-0009).

En el Sprint 4 cada módulo se extrae a su propio servicio en EKS; las rutas no cambian.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.compartido.config import get_settings
from app.compartido.contrato import id_operacion, instalar_openapi
from app.compartido.errores import registrar_manejadores
from app.compartido.salud import router as salud_router
from app.modulos.analitica.api.router import router as analitica_router
from app.modulos.catalogo.api.router import router as catalogo_router
from app.modulos.identidad.api.router import router as identidad_router
from app.modulos.movimientos.api.router import router as movimientos_router

ROUTERS_DE_DOMINIO = (identidad_router, catalogo_router, movimientos_router, analitica_router)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="API del control interno de inventario. Contrato por servicio en docs/openapi/.",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
        generate_unique_id_function=id_operacion,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "If-Match"],
        expose_headers=["ETag"],
    )
    registrar_manejadores(application)
    application.include_router(salud_router, prefix=settings.api_prefix)
    for router in ROUTERS_DE_DOMINIO:
        application.include_router(router, prefix=settings.api_prefix)
    instalar_openapi(application)
    return application


app = create_app()

"""Endpoints de plataforma, presentes en cada servicio (también tras la extracción a EKS)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.compartido.config import get_settings
from app.compartido.db import base_disponible

router = APIRouter(tags=["plataforma"])


class EstadoSalud(BaseModel):
    status: str
    app: str
    env: str


@router.get("/health", response_model=EstadoSalud, summary="Vida del proceso (no toca la base)")
def health() -> EstadoSalud:
    settings = get_settings()
    return EstadoSalud(status="ok", app=settings.app_name, env=settings.app_env)


@router.get(
    "/health/ready",
    response_model=EstadoSalud,
    summary="Listo para atender: SELECT 1 en la base",
    responses={503: {"model": EstadoSalud}},
)
def ready() -> JSONResponse:
    settings = get_settings()
    disponible = base_disponible()
    cuerpo = EstadoSalud(status="ok" if disponible else "sin_base", app=settings.app_name, env=settings.app_env)
    return JSONResponse(cuerpo.model_dump(), status_code=200 if disponible else 503)

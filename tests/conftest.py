"""Configuración común de pruebas. No requiere base de datos salvo las marcadas `integracion`."""

import os
from collections.abc import Callable
from uuid import UUID

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "secreto-solo-para-pruebas-0123456789")
os.environ.setdefault("DB_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:1/inexistente")

import pytest
from fastapi.testclient import TestClient

from app.compartido.seguridad import emitir_token
from app.main import app

USUARIO_PRUEBA = UUID("00000000-0000-4000-8000-000000000001")

FabricaToken = Callable[..., dict[str, str]]


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def cabeceras() -> FabricaToken:
    """`cabeceras("producto.crear", rol="ADMINISTRADOR")` → {"Authorization": "Bearer ..."}."""

    def _fabricar(*permisos: str, rol: str = "ADMINISTRADOR") -> dict[str, str]:
        token, _ = emitir_token(USUARIO_PRUEBA, rol, list(permisos))
        return {"Authorization": f"Bearer {token}"}

    return _fabricar

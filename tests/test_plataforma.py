"""Salud, seguridad del JWT y formato de errores."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.compartido.seguridad import decodificar_token, emitir_token
from tests.conftest import USUARIO_PRUEBA

PREFIJO = get_settings().api_prefix


def test_health_responde_sin_base(cliente: TestClient) -> None:
    respuesta = cliente.get(f"{PREFIJO}/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["env"] == "test"


@pytest.mark.parametrize(("disponible", "codigo", "estado"), [(True, 200, "ok"), (False, 503, "sin_base")])
def test_ready_refleja_la_base(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch, disponible: bool, codigo: int, estado: str
) -> None:
    monkeypatch.setattr("app.compartido.salud.base_disponible", lambda: disponible)
    respuesta = cliente.get(f"{PREFIJO}/health/ready")
    assert respuesta.status_code == codigo
    assert respuesta.json()["status"] == estado


def test_base_disponible_es_falso_sin_conexion(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.compartido import db

    monkeypatch.setenv("DB_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:1/inexistente")
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    try:
        assert db.base_disponible() is False
    finally:
        get_settings.cache_clear()
        db.get_engine.cache_clear()


def test_token_emitido_se_decodifica() -> None:
    token, vigencia = emitir_token(USUARIO_PRUEBA, "ADMINISTRADOR", ["producto.crear"])
    principal = decodificar_token(token)
    assert principal.usuario_id == USUARIO_PRUEBA
    assert principal.permisos == frozenset({"producto.crear"})
    assert vigencia == get_settings().jwt_expires_minutes * 60


def test_token_vencido_responde_401(cliente: TestClient) -> None:
    settings = get_settings()
    vencido = jwt.encode(
        {"sub": str(USUARIO_PRUEBA), "permisos": [], "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    respuesta = cliente.get(f"{PREFIJO}/auth/me", headers={"Authorization": f"Bearer {vencido}"})
    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


def test_token_mal_formado_responde_401(cliente: TestClient) -> None:
    respuesta = cliente.get(f"{PREFIJO}/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert respuesta.status_code == 401


def test_ruta_inexistente_en_problem_json(cliente: TestClient) -> None:
    respuesta = cliente.get(f"{PREFIJO}/no-existe")
    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "RECURSO_NO_EXISTE"


def test_documentacion_viva(cliente: TestClient) -> None:
    assert cliente.get(f"{PREFIJO}/openapi.json").status_code == 200
    assert cliente.get(f"{PREFIJO}/docs").status_code == 200

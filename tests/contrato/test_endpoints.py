"""Pruebas de contrato y seguridad sobre los 37 endpoints (RF-01, RNF-07).

Siguen siendo válidas después de implementar cada endpoint: comprueban que la ruta existe,
que exige su permiso y que un usuario autorizado llega a la lógica del endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from tests.conftest import FabricaToken
from tests.contrato.endpoints import AUTENTICADO, CASOS, PRODUCTO, PUBLICO, Caso

PREFIJO = get_settings().api_prefix


def _llamar(cliente: TestClient, caso: Caso, cabeceras: dict[str, str]) -> tuple[int, dict[str, object]]:
    respuesta = cliente.request(
        caso.metodo, PREFIJO + caso.url, json=caso.json, params=caso.params, headers={**caso.headers, **cabeceras}
    )
    cuerpo = respuesta.json() if respuesta.headers.get("content-type", "").endswith("json") else {}
    return respuesta.status_code, cuerpo


def test_cobertura_de_la_tabla() -> None:
    """Todo endpoint de dominio declarado en los routers está en la tabla, y viceversa."""
    declarados = {
        (metodo.upper(), ruta.removeprefix(PREFIJO))
        for ruta, operaciones in app.openapi()["paths"].items()
        if not ruta.startswith(f"{PREFIJO}/health")
        for metodo in operaciones
    }
    en_tabla = {(c.metodo, c.ruta) for c in CASOS}
    assert declarados == en_tabla
    assert len(CASOS) == 37


PROTEGIDOS = [c for c in CASOS if c.permiso != PUBLICO]
CON_PERMISO = [c for c in CASOS if c.permiso not in (PUBLICO, AUTENTICADO)]


def _ids(casos: list[Caso]) -> list[str]:
    return [f"{c.metodo} {c.ruta}" for c in casos]


@pytest.mark.parametrize("caso", PROTEGIDOS, ids=_ids(PROTEGIDOS))
def test_sin_token_responde_401(cliente: TestClient, caso: Caso) -> None:
    estado, cuerpo = _llamar(cliente, caso, {})
    assert estado == 401
    assert cuerpo["code"] == "NO_AUTENTICADO"


@pytest.mark.parametrize("caso", CON_PERMISO, ids=_ids(CON_PERMISO))
def test_sin_el_permiso_responde_403(cliente: TestClient, cabeceras: FabricaToken, caso: Caso) -> None:
    otros = {c.permiso for c in CASOS} - {caso.permiso, PUBLICO, AUTENTICADO}
    estado, cuerpo = _llamar(cliente, caso, cabeceras(*otros))
    assert estado == 403
    assert cuerpo["code"] == "SIN_PERMISO"


@pytest.mark.parametrize("caso", CASOS, ids=_ids(CASOS))
def test_con_el_permiso_llega_al_endpoint(cliente: TestClient, cabeceras: FabricaToken, caso: Caso) -> None:
    permisos = () if caso.permiso in (PUBLICO, AUTENTICADO) else (caso.permiso,)
    estado, cuerpo = _llamar(cliente, caso, cabeceras(*permisos))
    assert estado not in (401, 403, 404, 405, 422), cuerpo
    if estado == 501:  # todavía pendiente de implementar
        assert cuerpo["code"] == "NO_IMPLEMENTADO"


@pytest.mark.parametrize("ruta", [f"/productos/{PRODUCTO}", "/movimientos/1"])
def test_no_existe_delete(cliente: TestClient, cabeceras: FabricaToken, ruta: str) -> None:
    """RN-12 y ADR-0003: productos y movimientos no se borran."""
    respuesta = cliente.delete(PREFIJO + ruta, headers=cabeceras(*{c.permiso for c in CASOS}))
    assert respuesta.status_code == 405
    assert respuesta.json()["code"] == "METODO_NO_PERMITIDO"


def test_datos_invalidos_en_problem_json(cliente: TestClient, cabeceras: FabricaToken) -> None:
    respuesta = cliente.post(f"{PREFIJO}/productos", json={"codigo": ""}, headers=cabeceras("producto.crear"))
    assert respuesta.status_code == 422
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "DATOS_INVALIDOS"
    assert {e["campo"] for e in cuerpo["errors"]} >= {"body.codigo", "body.nombre"}

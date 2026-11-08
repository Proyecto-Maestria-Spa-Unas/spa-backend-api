"""B14 y X7 · endpoints con el puerto reemplazado por uno en memoria: forma de la respuesta según el contrato."""

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from app.modulos.analitica.api.router import hoy_bogota, obtener_consultas
from tests.conftest import FabricaToken
from tests.unit.analitica.test_tablero_kardex import (
    ACETONA,
    CONSUMO,
    HOY,
    KARDEX_A3,
    ConsultasEnMemoria,
    _producto,
)

P = get_settings().api_prefix


@pytest.fixture
def consultas() -> Iterator[ConsultasEnMemoria]:
    falsas = ConsultasEnMemoria(
        productos=[_producto(ACETONA, "REM-001", "BAJO_STOCK", "350", "38")],
        consumo=CONSUMO,
        lineas=KARDEX_A3,
    )
    app.dependency_overrides[obtener_consultas] = lambda: falsas
    app.dependency_overrides[hoy_bogota] = lambda: HOY
    yield falsas
    app.dependency_overrides.clear()


def test_tablero(cliente: TestClient, cabeceras: FabricaToken, consultas: ConsultasEnMemoria) -> None:
    r = cliente.get(f"{P}/analitica/tablero", headers=cabeceras("analitica.consultar"))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["productos_por_estado"] == {"BAJO_STOCK": 1}
    assert cuerpo["valor_inventario"] == "13300.0000"
    assert cuerpo["consumo_30_dias"] == "103.500"
    assert cuerpo["top_rotacion"][0] == {
        "producto_id": str(ACETONA),
        "codigo": "REM-001",
        "nombre": "Producto REM-001",
        "consumo": "100.500",
    }


def test_consumo(cliente: TestClient, cabeceras: FabricaToken, consultas: ConsultasEnMemoria) -> None:
    r = cliente.get(
        f"{P}/analitica/consumo",
        params={"desde": "2026-11-01", "hasta": "2026-11-07", "agrupar_por": "producto"},
        headers=cabeceras("analitica.consultar"),
    )
    assert r.status_code == 200, r.text
    assert r.json() == [{"clave": "REM-001", "cantidad": "100.500"}, {"clave": "ESM-001", "cantidad": "3.000"}]


def test_consumo_rango_invertido(cliente: TestClient, cabeceras: FabricaToken, consultas: ConsultasEnMemoria) -> None:
    r = cliente.get(
        f"{P}/analitica/consumo",
        params={"desde": "2026-11-07", "hasta": "2026-11-01"},
        headers=cabeceras("analitica.consultar"),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "DATOS_INVALIDOS"


def test_cobertura(cliente: TestClient, cabeceras: FabricaToken, consultas: ConsultasEnMemoria) -> None:
    r = cliente.get(f"{P}/analitica/cobertura", headers=cabeceras("analitica.consultar"))
    assert r.status_code == 200, r.text
    fila = r.json()[0]
    assert fila["codigo"] == "REM-001"
    assert fila["consumo_diario_promedio"] == "3.350"  # 100,5 ÷ 30
    assert fila["dias_cobertura"] == "104.5"


def test_kardex(cliente: TestClient, cabeceras: FabricaToken, consultas: ConsultasEnMemoria) -> None:
    r = cliente.get(
        f"{P}/analitica/kardex", params={"producto_id": str(ACETONA)}, headers=cabeceras("analitica.consultar")
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["metodo"] == "PROMEDIO_PONDERADO"
    assert [linea["valor_saldo"] for linea in cuerpo["lineas"]] == [
        "13300.0000",
        "19600.0000",
        "19012.0000",
        "23512.0275",
        "20095.7500",
    ]
    assert cuerpo["lineas"][2]["costo_unitario"] == "39.2000"
    assert cuerpo["saldo_final"] == "500.000"
    assert cuerpo["valor_final"] == "20095.7500"


def test_kardex_producto_inexistente(
    cliente: TestClient, cabeceras: FabricaToken, consultas: ConsultasEnMemoria
) -> None:
    r = cliente.get(
        f"{P}/analitica/kardex",
        params={"producto_id": "11111111-1111-4111-8111-111111111111"},
        headers=cabeceras("analitica.consultar"),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "RECURSO_NO_EXISTE"


def test_hoy_bogota_es_una_fecha() -> None:
    assert isinstance(hoy_bogota(), date)

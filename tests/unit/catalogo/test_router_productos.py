"""Pruebas unitarias de los endpoints de consulta de productos."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from app.modulos.catalogo.api.router import obtener_catalogo_repository
from app.modulos.catalogo.domain.modelo import EstadoInventario, Producto
from tests.conftest import FabricaToken

RUTA = f"{get_settings().api_prefix}/productos"
PRODUCTO_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _producto() -> Producto:
    ahora = datetime(2026, 11, 10, tzinfo=UTC)
    return Producto(
        id=PRODUCTO_ID,
        codigo="ESM-001",
        nombre="Esmalte rojo",
        descripcion="Esmalte de prueba",
        categoria_id=3,
        unidad_medida_id=1,
        stock_actual=Decimal("12.500"),
        stock_minimo=Decimal("2.000"),
        descontinuado=False,
        version=4,
        creado_en=ahora,
        actualizado_en=ahora,
    )


class CatalogoEnMemoria:
    def __init__(self) -> None:
        self.producto = _producto()
        self.argumentos_listado: dict[str, Any] | None = None

    def listar_productos(self, **argumentos: Any) -> tuple[list[Producto], int]:
        self.argumentos_listado = argumentos
        return [self.producto], 7

    def obtener_producto(self, producto_id: UUID) -> Producto | None:
        return self.producto if producto_id == self.producto.id else None


@pytest.fixture
def repositorio(monkeypatch: pytest.MonkeyPatch) -> CatalogoEnMemoria:
    falso = CatalogoEnMemoria()
    monkeypatch.setitem(app.dependency_overrides, obtener_catalogo_repository, lambda: falso)
    return falso


def test_listar_productos_envia_filtros_y_paginacion_al_repositorio(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio: CatalogoEnMemoria,
) -> None:
    respuesta = cliente.get(
        RUTA,
        params={
            "page": 2,
            "size": 5,
            "categoria_id": 3,
            "estado": "DISPONIBLE",
            "q": "esmalte",
            "incluir_descontinuados": True,
        },
        headers=cabeceras("producto.consultar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert repositorio.argumentos_listado == {
        "categoria_id": 3,
        "estado": EstadoInventario.DISPONIBLE,
        "q": "esmalte",
        "incluir_descontinuados": True,
        "offset": 5,
        "limite": 5,
    }
    assert respuesta.json() == {
        "items": [
            {
                "id": str(PRODUCTO_ID),
                "codigo": "ESM-001",
                "nombre": "Esmalte rojo",
                "descripcion": "Esmalte de prueba",
                "categoria_id": 3,
                "unidad_medida_id": 1,
                "stock_actual": "12.500",
                "stock_minimo": "2.000",
                "estado": "DISPONIBLE",
                "descontinuado": False,
                "version": 4,
                "creado_en": "2026-11-10T00:00:00Z",
                "actualizado_en": "2026-11-10T00:00:00Z",
            }
        ],
        "total": 7,
        "page": 2,
        "size": 5,
    }


def test_obtener_producto_inexistente_responde_error_de_contrato(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio: CatalogoEnMemoria,
) -> None:
    respuesta = cliente.get(
        f"{RUTA}/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        headers=cabeceras("producto.consultar"),
    )

    assert repositorio.producto.id == PRODUCTO_ID
    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "RECURSO_NO_EXISTE"

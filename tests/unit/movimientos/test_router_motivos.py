"""Pruebas HTTP del endpoint de motivos de movimiento (X1)."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from app.modulos.movimientos.api.router import obtener_repositorio_movimientos
from app.modulos.movimientos.domain.modelo import MotivoMovimiento, TipoMovimiento
from tests.conftest import FabricaToken

URL = f"{get_settings().api_prefix}/motivos-movimiento"


class RepositorioFalso:
    """Doble del repositorio para probar el endpoint sin consultar PostgreSQL."""

    def __init__(self, *motivos: MotivoMovimiento) -> None:
        self._motivos = list(motivos)
        self.tipos_pedidos: list[TipoMovimiento | None] = []

    def listar_motivos(self, tipo: TipoMovimiento | None = None) -> list[MotivoMovimiento]:
        self.tipos_pedidos.append(tipo)
        return [m for m in self._motivos if tipo is None or m.aplica_a is tipo]


@pytest.fixture
def con_repositorio() -> Iterator[Callable[..., RepositorioFalso]]:
    def _instalar(*motivos: MotivoMovimiento) -> RepositorioFalso:
        falso = RepositorioFalso(*motivos)
        app.dependency_overrides[obtener_repositorio_movimientos] = lambda: falso
        return falso

    yield _instalar
    app.dependency_overrides.clear()


def test_get_motivos_devuelve_el_contrato(
    cliente: TestClient,
    cabeceras: FabricaToken,
    con_repositorio: Callable[..., RepositorioFalso],
) -> None:
    con_repositorio(
        MotivoMovimiento(1, "COMPRA", "Ingreso por compra a proveedor", TipoMovimiento.ENTRADA),
        MotivoMovimiento(2, "MERMA", "Disminución por merma", TipoMovimiento.SALIDA),
    )

    respuesta = cliente.get(URL, headers=cabeceras("movimiento.consultar"))

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == [
        {
            "id": 1,
            "codigo": "COMPRA",
            "nombre": "Ingreso por compra a proveedor",
            "aplica_a": "ENTRADA",
        },
        {
            "id": 2,
            "codigo": "MERMA",
            "nombre": "Disminución por merma",
            "aplica_a": "SALIDA",
        },
    ]


def test_get_motivos_filtra_por_tipo(
    cliente: TestClient,
    cabeceras: FabricaToken,
    con_repositorio: Callable[..., RepositorioFalso],
) -> None:
    falso = con_repositorio(
        MotivoMovimiento(1, "COMPRA", "Ingreso por compra a proveedor", TipoMovimiento.ENTRADA),
        MotivoMovimiento(2, "MERMA", "Disminución por merma", TipoMovimiento.SALIDA),
    )

    respuesta = cliente.get(
        URL,
        params={"tipo": "SALIDA"},
        headers=cabeceras("movimiento.consultar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == [
        {
            "id": 2,
            "codigo": "MERMA",
            "nombre": "Disminución por merma",
            "aplica_a": "SALIDA",
        }
    ]
    assert falso.tipos_pedidos == [TipoMovimiento.SALIDA]


def test_get_motivos_sin_permiso_es_rechazado(
    cliente: TestClient,
    cabeceras: FabricaToken,
    con_repositorio: Callable[..., RepositorioFalso],
) -> None:
    con_repositorio()

    respuesta = cliente.get(URL, headers=cabeceras())

    assert respuesta.status_code == 403

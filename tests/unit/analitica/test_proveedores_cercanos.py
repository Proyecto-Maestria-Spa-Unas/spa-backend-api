"""X6 · Proveedores cercanos: caso de uso y endpoint GeoJSON con un puerto en memoria (sin base de datos)."""

from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.compartido.errores import DatosInvalidos
from app.main import app
from app.modulos.analitica.api.router import obtener_proveedores
from app.modulos.analitica.application.proveedores import BuscarProveedoresCercanos
from app.modulos.analitica.domain.proveedores import ProveedorCercano
from tests.conftest import FabricaToken

RUTA = f"{get_settings().api_prefix}/analitica/proveedores-cercanos"
PLAZA_ESPANA = UUID("3c1f0000-0000-4000-8000-000000000003")
SAN_ANDRESITO = UUID("3c1f0000-0000-4000-8000-000000000005")


def _proveedor(pid: UUID, nombre: str, telefono: str | None, lat: float, lon: float, km: str) -> ProveedorCercano:
    return ProveedorCercano(pid, nombre, telefono, lat, lon, Decimal(km))


PROVEEDORES = [
    _proveedor(SAN_ANDRESITO, "San Andresito de la 18", "3000000005", 4.606, -74.0855, "0.59"),
    _proveedor(PLAZA_ESPANA, "Plaza España", None, 4.6038, -74.0875, "0.92"),
]


class ProveedoresEnMemoria:
    def __init__(self, proveedores: list[ProveedorCercano]) -> None:
        self._proveedores = proveedores
        self.llamadas: list[tuple[float, float, float]] = []

    def cercanos(self, latitud: float, longitud: float, radio_km: float) -> list[ProveedorCercano]:
        self.llamadas.append((latitud, longitud, radio_km))
        return self._proveedores


@pytest.fixture
def con_proveedores() -> Iterator[callable]:
    def _instalar(*proveedores: ProveedorCercano) -> ProveedoresEnMemoria:
        falsos = ProveedoresEnMemoria(list(proveedores))
        app.dependency_overrides[obtener_proveedores] = lambda: falsos
        return falsos

    yield _instalar
    app.dependency_overrides.clear()


# ── Caso de uso ────────────────────────────────────────────────────────────


def test_el_caso_de_uso_devuelve_lo_que_entrega_el_puerto() -> None:
    falsos = ProveedoresEnMemoria(PROVEEDORES)
    assert BuscarProveedoresCercanos(falsos)(4.6097, -74.0817, 5) == PROVEEDORES
    assert falsos.llamadas == [(4.6097, -74.0817, 5)]


@pytest.mark.parametrize(
    ("latitud", "longitud", "radio", "campo"),
    [
        (91, -74, 5, "latitud"),
        (-90.5, -74, 5, "latitud"),
        (4.6, 181, 5, "longitud"),
        (4.6, -180.1, 5, "longitud"),
        (4.6, -74, 0, "radio_km"),
        (4.6, -74, -1, "radio_km"),
        (4.6, -74, 100.5, "radio_km"),
    ],
)
def test_el_caso_de_uso_rechaza_puntos_y_radios_fuera_de_rango(
    latitud: float, longitud: float, radio: float, campo: str
) -> None:
    falsos = ProveedoresEnMemoria(PROVEEDORES)
    with pytest.raises(DatosInvalidos) as error:
        BuscarProveedoresCercanos(falsos)(latitud, longitud, radio)
    assert [e["campo"] for e in error.value.errors] == [campo]
    assert falsos.llamadas == []


@pytest.mark.parametrize(("latitud", "longitud", "radio"), [(90, 180, 100), (-90, -180, 0.01), (0, 0, 1)])
def test_el_caso_de_uso_acepta_los_extremos_validos(latitud: float, longitud: float, radio: float) -> None:
    assert BuscarProveedoresCercanos(ProveedoresEnMemoria([]))(latitud, longitud, radio) == []


# ── Endpoint ───────────────────────────────────────────────────────────────


def test_devuelve_un_feature_collection_geojson(cliente: TestClient, cabeceras: FabricaToken, con_proveedores) -> None:
    con_proveedores(*PROVEEDORES)
    r = cliente.get(RUTA, params={"latitud": 4.6097, "longitud": -74.0817}, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 200, r.text
    assert r.json() == {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-74.0855, 4.606]},
                "properties": {
                    "proveedor_id": str(SAN_ANDRESITO),
                    "nombre": "San Andresito de la 18",
                    "telefono": "3000000005",
                    "distancia_km": "0.59",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-74.0875, 4.6038]},
                "properties": {
                    "proveedor_id": str(PLAZA_ESPANA),
                    "nombre": "Plaza España",
                    "telefono": None,
                    "distancia_km": "0.92",
                },
            },
        ],
    }


def test_las_coordenadas_van_como_longitud_y_luego_latitud(
    cliente: TestClient, cabeceras: FabricaToken, con_proveedores
) -> None:
    """RFC 7946 §3.1.1: [longitud, latitud]. Al revés, Leaflet y QGIS dibujarían los puntos en otro lugar."""
    con_proveedores(_proveedor(PLAZA_ESPANA, "P", None, lat=4.6, lon=-74.1, km="1.00"))
    r = cliente.get(RUTA, params={"latitud": 4.6, "longitud": -74.1}, headers=cabeceras("alerta.consultar"))
    assert r.json()["features"][0]["geometry"]["coordinates"] == [-74.1, 4.6]


def test_sin_proveedores_en_el_radio_devuelve_la_coleccion_vacia(
    cliente: TestClient, cabeceras: FabricaToken, con_proveedores
) -> None:
    con_proveedores()
    r = cliente.get(RUTA, params={"latitud": 4.6, "longitud": -74.1}, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 200
    assert r.json() == {"type": "FeatureCollection", "features": []}


def test_el_radio_por_defecto_es_10_km(cliente: TestClient, cabeceras: FabricaToken, con_proveedores) -> None:
    falsos = con_proveedores()
    cliente.get(RUTA, params={"latitud": 4.6, "longitud": -74.1}, headers=cabeceras("alerta.consultar"))
    assert falsos.llamadas == [(4.6, -74.1, 10.0)]


def test_pasa_el_punto_y_el_radio_al_puerto(cliente: TestClient, cabeceras: FabricaToken, con_proveedores) -> None:
    falsos = con_proveedores()
    cliente.get(
        RUTA, params={"latitud": 4.61, "longitud": -74.08, "radio_km": 2.5}, headers=cabeceras("alerta.consultar")
    )
    assert falsos.llamadas == [(4.61, -74.08, 2.5)]


@pytest.mark.parametrize(
    ("params", "campo"),
    [
        ({"longitud": -74.1}, "query.latitud"),
        ({"latitud": 4.6}, "query.longitud"),
        ({"latitud": 91, "longitud": -74.1}, "query.latitud"),
        ({"latitud": 4.6, "longitud": 181}, "query.longitud"),
        ({"latitud": 4.6, "longitud": -74.1, "radio_km": 0}, "query.radio_km"),
        ({"latitud": 4.6, "longitud": -74.1, "radio_km": 101}, "query.radio_km"),
        ({"latitud": "abc", "longitud": -74.1}, "query.latitud"),
    ],
)
def test_parametros_invalidos_responden_422(
    cliente: TestClient, cabeceras: FabricaToken, con_proveedores, params: dict, campo: str
) -> None:
    falsos = con_proveedores(*PROVEEDORES)
    r = cliente.get(RUTA, params=params, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 422
    assert r.json()["code"] == "DATOS_INVALIDOS"
    assert r.json()["errors"][0]["campo"] == campo
    assert falsos.llamadas == []


def test_exige_token_y_permiso_de_alertas(cliente: TestClient, cabeceras: FabricaToken, con_proveedores) -> None:
    con_proveedores(*PROVEEDORES)
    params = {"latitud": 4.6, "longitud": -74.1}
    sin_token = cliente.get(RUTA, params=params)
    assert sin_token.status_code == 401
    assert sin_token.json()["code"] == "NO_AUTENTICADO"
    sin_permiso = cliente.get(RUTA, params=params, headers=cabeceras("producto.consultar"))
    assert sin_permiso.status_code == 403
    assert sin_permiso.json()["code"] == "SIN_PERMISO"

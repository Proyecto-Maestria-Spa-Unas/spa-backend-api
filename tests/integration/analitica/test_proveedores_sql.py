"""X6 · inventario.proveedores_cercanos() contra PostgreSQL/PostGIS con el esquema de spa-database (D12).

Los proveedores de estas pruebas viven cerca de Madrid, lejos de los de prueba de Bogotá que siembra D12,
y se crean dentro de la transacción de la prueba (se revierte al terminar).
"""

from decimal import Decimal
from math import asin, cos, radians, sin, sqrt
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modulos.analitica.infrastructure.proveedores_sql import ProveedoresSQL

pytestmark = pytest.mark.integracion

# Madrid. 0,01° de latitud ≈ 1,11 km.
LAT, LON = 40.4168, -3.7038


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia sobre una esfera de 6371 km: referencia independiente de PostGIS (difiere < 0,5 % del elipsoide)."""
    a = (
        sin(radians(lat2 - lat1) / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0088 * asin(sqrt(a))


def _crear(
    con: Connection,
    nit: str,
    nombre: str,
    lat: float | None,
    lon: float | None,
    *,
    activo: bool = True,
    tel: str | None = None,
) -> UUID:
    return con.execute(
        text(
            """
            INSERT INTO inventario.proveedor (nit, nombre, telefono, ubicacion, activo)
            VALUES (:nit, :nombre, :tel,
                    CASE WHEN CAST(:lon AS float8) IS NULL THEN NULL
                         ELSE ST_SetSRID(ST_MakePoint(CAST(:lon AS float8), CAST(:lat AS float8)), 4326)::geography END,
                    :activo)
            RETURNING id
            """
        ),
        {"nit": nit, "nombre": nombre, "tel": tel, "lat": lat, "lon": lon, "activo": activo},
    ).scalar_one()


@pytest.fixture
def escenario(transaccion: Connection) -> dict[str, UUID]:
    return {
        "cerca": _crear(transaccion, "X6-CERCA", "X6 Cerca", LAT + 0.01, LON, tel="600000001"),  # ≈ 1,1 km al norte
        "medio": _crear(transaccion, "X6-MEDIO", "X6 Medio", LAT, LON + 0.05),  # ≈ 4,2 km al este
        "lejos": _crear(transaccion, "X6-LEJOS", "X6 Lejos", LAT + 0.5, LON),  # ≈ 55 km
        "inactivo": _crear(transaccion, "X6-INACT", "X6 Inactivo", LAT + 0.005, LON, activo=False),
        "sin_ubicacion": _crear(transaccion, "X6-SINUB", "X6 Sin ubicación", None, None),
    }


def _buscar(con: Connection, radio_km: float):
    with Session(bind=con) as session:
        return ProveedoresSQL(session).cercanos(LAT, LON, radio_km)


def test_devuelve_solo_los_proveedores_dentro_del_radio_del_mas_cercano_al_mas_lejano(
    transaccion: Connection, escenario: dict[str, UUID]
) -> None:
    ids = [p.proveedor_id for p in _buscar(transaccion, 10)]
    assert ids == [escenario["cerca"], escenario["medio"]]


def test_un_radio_mayor_incluye_a_los_mas_lejanos(transaccion: Connection, escenario: dict[str, UUID]) -> None:
    ids = [p.proveedor_id for p in _buscar(transaccion, 100)]
    assert ids == [escenario["cerca"], escenario["medio"], escenario["lejos"]]


def test_un_radio_pequeno_deja_solo_al_mas_cercano(transaccion: Connection, escenario: dict[str, UUID]) -> None:
    assert [p.proveedor_id for p in _buscar(transaccion, 2)] == [escenario["cerca"]]


def test_excluye_a_los_inactivos_y_a_los_que_no_tienen_ubicacion(
    transaccion: Connection, escenario: dict[str, UUID]
) -> None:
    ids = {p.proveedor_id for p in _buscar(transaccion, 100)}
    assert escenario["inactivo"] not in ids
    assert escenario["sin_ubicacion"] not in ids


def test_devuelve_distancia_en_km_con_dos_decimales(transaccion: Connection, escenario: dict[str, UUID]) -> None:
    cerca, medio = _buscar(transaccion, 10)
    assert cerca.distancia_km == pytest.approx(
        Decimal(str(_haversine_km(LAT, LON, LAT + 0.01, LON))), abs=Decimal("0.02")
    )
    assert medio.distancia_km == pytest.approx(
        Decimal(str(_haversine_km(LAT, LON, LAT, LON + 0.05))), abs=Decimal("0.05")
    )
    assert cerca.distancia_km == Decimal("1.11")
    assert medio.distancia_km == Decimal("4.24")
    assert cerca.distancia_km.as_tuple().exponent == medio.distancia_km.as_tuple().exponent == -2


def test_las_coordenadas_se_devuelven_en_latitud_y_longitud_correctas(
    transaccion: Connection, escenario: dict[str, UUID]
) -> None:
    cerca = _buscar(transaccion, 10)[0]
    assert cerca.latitud == pytest.approx(LAT + 0.01)
    assert cerca.longitud == pytest.approx(LON)


def test_devuelve_nombre_y_telefono(transaccion: Connection, escenario: dict[str, UUID]) -> None:
    cerca, medio = _buscar(transaccion, 10)
    assert (cerca.nombre, cerca.telefono) == ("X6 Cerca", "600000001")
    assert (medio.nombre, medio.telefono) == ("X6 Medio", None)


def test_sin_proveedores_en_el_radio_devuelve_lista_vacia(transaccion: Connection, escenario: dict[str, UUID]) -> None:
    with Session(bind=transaccion) as session:
        assert ProveedoresSQL(session).cercanos(-33.0, 151.0, 5) == []  # Sídney


def test_los_proveedores_de_prueba_de_bogota_de_d12_aparecen_con_ubicacion(transaccion: Connection) -> None:
    with Session(bind=transaccion) as session:
        encontrados = ProveedoresSQL(session).cercanos(4.6097, -74.0817, 10)
    nombres = {p.nombre for p in encontrados}
    if not any("Plaza España" in n for n in nombres):
        pytest.skip("La base no tiene los proveedores de prueba de D12")
    assert all(4.4 < p.latitud < 4.8 and -74.3 < p.longitud < -73.9 for p in encontrados)
    assert [p.distancia_km for p in encontrados] == sorted(p.distancia_km for p in encontrados)

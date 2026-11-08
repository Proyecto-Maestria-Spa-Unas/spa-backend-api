"""Adaptador de ConsultasProveedores: llama a inventario.proveedores_cercanos() (D12, ST_DWithin).

La función devuelve id, NIT, nombre, dirección y distancia; el teléfono y las coordenadas se leen de
inventario.proveedor con ST_X/ST_Y (longitud primero en PostGIS). Los proveedores sin ubicación nunca
salen de la función, así que toda fila tiene coordenadas. Solo SELECT.
"""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modulos.analitica.domain.proveedores import ProveedorCercano

_CONSULTA = text(
    """
    SELECT p.id,
           p.nombre,
           p.telefono,
           ST_Y(p.ubicacion::geometry) AS latitud,
           ST_X(p.ubicacion::geometry) AS longitud,
           c.distancia_km
    FROM inventario.proveedores_cercanos(:latitud, :longitud, :radio_km) AS c
    JOIN inventario.proveedor AS p ON p.id = c.id
    ORDER BY c.distancia_km, p.nombre
    """
)


def _kilometros(valor: float) -> Decimal:
    """Distancia en km con 2 decimales (precisión de 10 m), como en el contrato."""
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ProveedoresSQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def cercanos(self, latitud: float, longitud: float, radio_km: float) -> list[ProveedorCercano]:
        filas = self._session.execute(
            _CONSULTA, {"latitud": latitud, "longitud": longitud, "radio_km": radio_km}
        ).mappings()
        return [
            ProveedorCercano(
                proveedor_id=f["id"],
                nombre=f["nombre"],
                telefono=f["telefono"],
                latitud=float(f["latitud"]),
                longitud=float(f["longitud"]),
                distancia_km=_kilometros(f["distancia_km"]),
            )
            for f in filas
        ]

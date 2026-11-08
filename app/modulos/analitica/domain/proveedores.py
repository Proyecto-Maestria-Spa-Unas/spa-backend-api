"""X6 · Proveedores cercanos. Solo lectura sobre inventario.proveedor (D12)."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

RADIO_MAX_KM = 100  # mismo tope que declara el contrato (analitica-v1)


@dataclass(frozen=True)
class ProveedorCercano:
    """Un proveedor con ubicación dentro del radio consultado, con su distancia al punto."""

    proveedor_id: UUID
    nombre: str
    telefono: str | None
    latitud: float
    longitud: float
    distancia_km: Decimal

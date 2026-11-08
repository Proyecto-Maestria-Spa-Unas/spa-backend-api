"""X6 · Búsqueda de proveedores cercanos a un punto (reposición de productos en alerta, RF-17)."""

from typing import Protocol

from app.compartido.errores import DatosInvalidos
from app.modulos.analitica.domain.proveedores import RADIO_MAX_KM, ProveedorCercano


class ConsultasProveedores(Protocol):
    def cercanos(self, latitud: float, longitud: float, radio_km: float) -> list[ProveedorCercano]:
        """Proveedores activos con ubicación dentro del radio, del más cercano al más lejano."""
        ...


class BuscarProveedoresCercanos:
    def __init__(self, consultas: ConsultasProveedores) -> None:
        self._consultas = consultas

    def __call__(self, latitud: float, longitud: float, radio_km: float) -> list[ProveedorCercano]:
        errores = []
        if not -90 <= latitud <= 90:
            errores.append({"campo": "latitud", "mensaje": "Debe estar entre -90 y 90"})
        if not -180 <= longitud <= 180:
            errores.append({"campo": "longitud", "mensaje": "Debe estar entre -180 y 180"})
        if not 0 < radio_km <= RADIO_MAX_KM:
            errores.append({"campo": "radio_km", "mensaje": f"Debe ser mayor que 0 y de máximo {RADIO_MAX_KM} km"})
        if errores:
            raise DatosInvalidos("El punto o el radio de búsqueda no son válidos", errors=errores)
        return self._consultas.cercanos(latitud, longitud, radio_km)

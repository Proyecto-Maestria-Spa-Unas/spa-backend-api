"""Puertos de movimientos. Solo INSERT sobre inventario.movimiento."""

from typing import Any, Protocol
from uuid import UUID


class MovimientoRepository(Protocol):
    """TODO (S3 · Damx0611): reemplazar `Any` por las entidades del dominio."""

    def registrar(self, movimiento: Any, clave_idempotencia: UUID) -> Any: ...

    def buscar_por_clave(self, clave_idempotencia: UUID) -> Any | None: ...

    def obtener(self, movimiento_id: int) -> Any | None: ...

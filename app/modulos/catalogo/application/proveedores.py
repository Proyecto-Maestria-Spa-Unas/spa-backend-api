"""Puerto de persistencia para proveedores."""

from typing import Protocol
from uuid import UUID

from app.modulos.catalogo.domain.modelo import Proveedor


class ProveedoresRepository(Protocol):
    """Operaciones de persistencia disponibles para proveedores."""

    def listar(self, incluir_inactivos: bool = False) -> list[Proveedor]:
        """Lista proveedores, incluyendo inactivos si se solicita."""
        ...

    def crear(self, datos: dict[str, object]) -> Proveedor:
        """Registra un proveedor nuevo."""
        ...

    def obtener(self, proveedor_id: UUID) -> Proveedor:
        """Consulta un proveedor por su identificador."""
        ...

    def actualizar(self, proveedor_id: UUID, cambios: dict[str, object]) -> Proveedor:
        """Actualiza los campos permitidos de un proveedor."""
        ...

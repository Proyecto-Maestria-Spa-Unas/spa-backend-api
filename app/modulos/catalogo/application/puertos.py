"""Puertos del catálogo. El módulo S2 lee stock_actual pero no lo escribe."""

from typing import Protocol
from uuid import UUID

from app.modulos.catalogo.domain.modelo import Categoria, Producto, UnidadMedida


class CatalogoRepository(Protocol):
    """Contrato de acceso a categorías, unidades y productos del catálogo.

    Las firmas utilizan entidades del dominio, no tipos genéricos ni modelos
    específicos de SQLAlchemy. La infraestructura implementa este protocolo.
    """

    def listar_categorias(self, solo_activas: bool) -> list[Categoria]: ...

    def listar_unidades(self) -> list[UnidadMedida]: ...

    def obtener_producto(self, producto_id: UUID) -> Producto | None: ...

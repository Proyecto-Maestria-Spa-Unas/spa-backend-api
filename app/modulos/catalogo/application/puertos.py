"""Puertos del catálogo. El módulo S2 lee stock_actual pero no lo escribe."""

from typing import Protocol
from uuid import UUID

from app.modulos.catalogo.domain.modelo import (
    Categoria,
    EstadoInventario,
    Producto,
    UnidadMedida,
)


class CatalogoRepository(Protocol):
    """Contrato de acceso a categorías, unidades y productos del catálogo."""

    def listar_categorias(self, solo_activas: bool) -> list[Categoria]: ...

    def listar_unidades(self) -> list[UnidadMedida]: ...

    def obtener_producto(self, producto_id: UUID) -> Producto | None: ...

    def listar_productos(
        self,
        categoria_id: int | None,
        estado: EstadoInventario | None,
        q: str | None,
        incluir_descontinuados: bool,
        offset: int,
        limite: int,
    ) -> tuple[list[Producto], int]: ...

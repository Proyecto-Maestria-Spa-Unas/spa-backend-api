"""Puertos del catálogo. S2 lee `stock_actual` pero nunca lo escribe: solo S3, vía trigger."""

from typing import Any, Protocol


class CatalogoRepository(Protocol):
    """Tablas inventario.categoria, unidad_medida y producto; vista inventario.v_inventario.

    TODO (B3): reemplazar `Any` por las entidades del dominio cuando existan.
    """

    def listar_categorias(self, solo_activas: bool) -> list[Any]: ...

    def listar_unidades(self) -> list[Any]: ...

    def obtener_producto(self, producto_id: Any) -> Any | None: ...

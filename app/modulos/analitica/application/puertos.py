"""Puertos de analítica. Lee inventario.v_inventario, v_alerta_stock, v_consumo_diario y v_kardex (solo SELECT)."""

from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.modulos.analitica.domain.modelo import (
    ConsumoDiario,
    LineaKardex,
    ProductoInventario,
    ProductoReferencia,
)


class ConsultasAnaliticas(Protocol):
    def alertas(self, estado: str | None) -> list[Any]:
        """TODO (X4 · Estefa44445): tipar con los modelos del dominio."""
        ...

    def inventario(self) -> list[ProductoInventario]: ...

    def consumo_diario(self, desde: date, hasta: date) -> list[ConsumoDiario]: ...

    def producto(self, producto_id: UUID) -> ProductoReferencia | None: ...

    def kardex(self, producto_id: UUID, desde: date | None, hasta: date | None) -> list[LineaKardex]: ...

    def ultima_linea_kardex(self, producto_id: UUID, hasta: date | None) -> LineaKardex | None: ...


class Exportador(Protocol):
    """Genera CSV o Parquet con DuckDB (X5)."""

    def exportar(self, conjunto: str, formato: str) -> bytes: ...

"""Puertos de analítica. Lee inventario.v_inventario, v_alerta_stock y movimiento (solo SELECT)."""

from datetime import date
from typing import Any, Protocol


class ConsultasAnaliticas(Protocol):
    """TODO (S4 · ivonnelizethmoreno-cloud): tipar con los modelos del dominio."""

    def alertas(self, estado: str | None) -> list[Any]: ...

    def consumo(self, agrupar_por: str, desde: date, hasta: date) -> list[Any]: ...


class Exportador(Protocol):
    """Genera CSV o Parquet con DuckDB (agregar `duckdb` y `pandas` a las dependencias al implementarlo)."""

    def exportar(self, conjunto: str, formato: str) -> bytes: ...

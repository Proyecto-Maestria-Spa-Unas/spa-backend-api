"""Puertos de analítica. Lee inventario.v_inventario, v_alerta_stock y movimiento (solo SELECT)."""

from datetime import date
from typing import Any, Protocol

from app.modulos.analitica.domain.modelo import Alerta, EstadoAlerta, ResumenAlertas


class ConsultasAnaliticas(Protocol):
    """Lecturas de analítica. Las alertas ya están tipadas; el resto lo tipa B14 (S4)."""

    def alertas(self, estado: EstadoAlerta | None) -> list[Alerta]: ...

    def resumen_alertas(self) -> ResumenAlertas: ...

    def consumo(self, agrupar_por: str, desde: date, hasta: date) -> list[Any]: ...


class Exportador(Protocol):
    """Genera CSV o Parquet con DuckDB (agregar `duckdb` y `pandas` a las dependencias al implementarlo)."""

    def exportar(self, conjunto: str, formato: str) -> bytes: ...

"""Modelo del dominio de analítica. Solo lectura: S4 nunca escribe en la base."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class EstadoAlerta(StrEnum):
    BAJO_STOCK = "BAJO_STOCK"
    AGOTADO = "AGOTADO"


class AgrupacionConsumo(StrEnum):
    CATEGORIA = "categoria"
    PRODUCTO = "producto"
    DIA = "dia"


@dataclass(frozen=True)
class Alerta:
    """Producto que alcanzó o bajó del stock mínimo (RN-09, RN-10)."""

    producto_id: UUID
    codigo: str
    nombre: str
    stock_actual: Decimal
    stock_minimo: Decimal
    estado: EstadoAlerta

    @property
    def faltante(self) -> Decimal:
        """stock_minimo − stock_actual: cuánto falta para volver al mínimo (nunca negativo)."""
        return max(self.stock_minimo - self.stock_actual, Decimal(0))


@dataclass(frozen=True)
class ResumenAlertas:
    """Conteo por estado; `total` alimenta el contador del menú (RF-18)."""

    bajo_stock: int
    agotado: int

    @property
    def total(self) -> int:
        return self.bajo_stock + self.agotado

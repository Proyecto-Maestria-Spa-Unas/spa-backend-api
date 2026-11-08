"""Modelo del dominio de analítica. Solo lectura: S4 nunca escribe en la base."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

DIAS_VENTANA_CONSUMO = 30


class EstadoAlerta(StrEnum):
    BAJO_STOCK = "BAJO_STOCK"
    AGOTADO = "AGOTADO"


class AgrupacionConsumo(StrEnum):
    CATEGORIA = "categoria"
    PRODUCTO = "producto"
    DIA = "dia"


@dataclass(frozen=True)
class ProductoInventario:
    """Una fila de inventario.v_inventario: lo que el tablero necesita de cada producto."""

    producto_id: UUID
    codigo: str
    nombre: str
    estado: str
    stock_actual: Decimal
    costo_promedio: Decimal


@dataclass(frozen=True)
class ConsumoDiario:
    """Salidas no anuladas de un producto en un día (inventario.v_consumo_diario, D9)."""

    fecha: date
    producto_id: UUID
    codigo: str
    nombre: str
    categoria: str
    cantidad: Decimal


@dataclass(frozen=True)
class LineaKardex:
    """Una línea del kardex valorizado (inventario.v_kardex, D9)."""

    ocurrido_en: datetime
    tipo: str
    motivo_codigo: str
    cantidad: Decimal
    costo_unitario: Decimal | None
    costo_total: Decimal | None
    saldo: Decimal
    costo_promedio: Decimal
    valor_saldo: Decimal


@dataclass(frozen=True)
class ProductoReferencia:
    producto_id: UUID
    codigo: str
    nombre: str


def valor_inventario(productos: list[ProductoInventario]) -> Decimal | None:
    """Σ stock_actual × costo_promedio (DEC-11). None si ningún producto tiene costo registrado."""
    if not any(p.costo_promedio > 0 for p in productos):
        return None
    total = sum((p.stock_actual * p.costo_promedio for p in productos), Decimal(0))
    return total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def dias_cobertura(stock_actual: Decimal, consumo_diario_promedio: Decimal) -> Decimal | None:
    """Días que alcanza el stock al ritmo de consumo actual. None si no hubo consumo (RF-17)."""
    if consumo_diario_promedio <= 0:
        return None
    return (stock_actual / consumo_diario_promedio).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

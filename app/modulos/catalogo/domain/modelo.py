"""Entidades y reglas puras del dominio del catálogo.

Este módulo no depende de FastAPI, SQLAlchemy ni Pydantic para que las reglas
puedan utilizarse y probarse sin iniciar la API ni conectarse a la base de datos.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class EstadoInventario(StrEnum):
    DISPONIBLE = "DISPONIBLE"  # RN-08
    BAJO_STOCK = "BAJO_STOCK"  # RN-09
    AGOTADO = "AGOTADO"  # RN-10
    DESCONTINUADO = "DESCONTINUADO"  # RN-11


class Magnitud(StrEnum):
    CONTEO = "CONTEO"
    VOLUMEN = "VOLUMEN"
    MASA = "MASA"


@dataclass(slots=True)
class Categoria:
    """Categoría que agrupa productos del inventario."""

    id: int
    nombre: str
    descripcion: str | None = None
    orden: int = 0
    activa: bool = True


@dataclass(slots=True)
class UnidadMedida:
    """Unidad con la que se cuantifica un producto."""

    id: int
    codigo: str
    nombre: str
    magnitud: Magnitud
    admite_decimales: bool


def calcular_estado_inventario(
    stock_actual: Decimal,
    stock_minimo: Decimal | None,
    descontinuado: bool,
) -> EstadoInventario:
    """Devuelve el estado derivado del inventario aplicando RN-08..RN-11.

    - Un producto marcado como descontinuado queda en DESCONTINUADO.
    - Un producto activo con stock cero queda en AGOTADO.
    - Si hay stock positivo y se configuró un mínimo, llegar al mínimo o quedar
      por debajo produce BAJO_STOCK.
    - En los demás casos queda DISPONIBLE.

    ``None`` como stock mínimo significa que no se configura una alerta por
    stock bajo (RN-14). Las cantidades negativas deben impedirse en la capa de
    validación y en la base de datos.
    """
    if descontinuado:
        return EstadoInventario.DESCONTINUADO
    if stock_actual <= Decimal("0"):
        return EstadoInventario.AGOTADO
    if stock_minimo is not None and stock_actual <= stock_minimo:
        return EstadoInventario.BAJO_STOCK
    return EstadoInventario.DISPONIBLE


@dataclass(slots=True)
class Producto:
    """Entidad de dominio de producto, independiente del ORM y la API."""

    id: UUID
    codigo: str
    nombre: str
    descripcion: str | None
    categoria_id: int
    unidad_medida_id: int
    stock_actual: Decimal
    stock_minimo: Decimal | None
    descontinuado: bool
    version: int
    creado_en: datetime
    actualizado_en: datetime

    @property
    def estado(self) -> EstadoInventario:
        """El estado se calcula; el catálogo no lo escribe directamente."""
        return calcular_estado_inventario(
            stock_actual=self.stock_actual,
            stock_minimo=self.stock_minimo,
            descontinuado=self.descontinuado,
        )

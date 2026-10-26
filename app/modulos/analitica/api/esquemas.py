"""Esquemas del contrato analitica-v1. Cambiarlos cambia docs/openapi/analitica-v1.yaml."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.compartido.tipos import Cantidad, Costo
from app.modulos.analitica.domain.modelo import EstadoAlerta


class Alerta(BaseModel):
    producto_id: UUID
    codigo: str
    nombre: str
    stock_actual: Cantidad
    stock_minimo: Cantidad
    estado: EstadoAlerta
    faltante: Cantidad = Field(description="stock_minimo − stock_actual")


class ResumenAlertas(BaseModel):
    bajo_stock: int
    agotado: int
    total: int


class ProductoRotacion(BaseModel):
    producto_id: UUID
    codigo: str
    nombre: str
    consumo: Cantidad


class Tablero(BaseModel):
    productos_por_estado: dict[str, int] = Field(examples=[{"DISPONIBLE": 40, "BAJO_STOCK": 5, "AGOTADO": 2}])
    valor_inventario: Costo | None = Field(description="null mientras DEC-11 no se decida")
    consumo_30_dias: Cantidad
    top_rotacion: list[ProductoRotacion] = Field(max_length=10)


class ConsumoItem(BaseModel):
    clave: str = Field(description="Categoría, código de producto o fecha, según agrupar_por")
    cantidad: Cantidad


class Cobertura(BaseModel):
    producto_id: UUID
    codigo: str
    nombre: str
    stock_actual: Cantidad
    consumo_diario_promedio: Cantidad
    dias_cobertura: Decimal | None = Field(description="null si no hubo consumo en 30 días")

"""Esquemas del contrato analitica-v1. Cambiarlos cambia docs/openapi/analitica-v1.yaml."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.compartido.tipos import Cantidad, Costo
from app.modulos.analitica.domain.modelo import EstadoAlerta


class Alerta(BaseModel):
    producto_id: UUID = Field(examples=["0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b"])
    codigo: str = Field(examples=["REM-001"])
    nombre: str = Field(examples=["Acetona pura"])
    stock_actual: Cantidad = Field(examples=["350.000"])
    stock_minimo: Cantidad = Field(examples=["500.000"])
    estado: EstadoAlerta
    faltante: Cantidad = Field(description="stock_minimo − stock_actual", examples=["150.000"])


class ResumenAlertas(BaseModel):
    bajo_stock: int = Field(examples=[5])
    agotado: int = Field(examples=[2])
    total: int = Field(examples=[7], description="Valor del contador del menú")


class ProductoRotacion(BaseModel):
    producto_id: UUID = Field(examples=["0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b"])
    codigo: str = Field(examples=["REM-001"])
    nombre: str = Field(examples=["Acetona pura"])
    consumo: Cantidad = Field(examples=["150.000"], description="Salidas de los últimos 30 días")


class Tablero(BaseModel):
    productos_por_estado: dict[str, int] = Field(examples=[{"DISPONIBLE": 40, "BAJO_STOCK": 5, "AGOTADO": 2}])
    valor_inventario: Costo | None = Field(
        description="Σ stock_actual × costo_promedio (DEC-11); null si no hay costos registrados",
        examples=["4250000.0000"],
    )
    consumo_30_dias: Cantidad = Field(examples=["1280.000"])
    top_rotacion: list[ProductoRotacion] = Field(max_length=10)


class ConsumoItem(BaseModel):
    clave: str = Field(description="Categoría, código de producto o fecha, según agrupar_por", examples=["Removedores"])
    cantidad: Cantidad = Field(examples=["150.000"])


class Cobertura(BaseModel):
    producto_id: UUID = Field(examples=["0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b"])
    codigo: str = Field(examples=["REM-001"])
    nombre: str = Field(examples=["Acetona pura"])
    stock_actual: Cantidad = Field(examples=["350.000"])
    consumo_diario_promedio: Cantidad = Field(examples=["5.000"], description="Promedio de los últimos 30 días")
    dias_cobertura: Decimal | None = Field(description="null si no hubo consumo en 30 días", examples=["70.0"])


class LineaKardex(BaseModel):
    ocurrido_en: datetime = Field(examples=["2026-10-28T09:00:00-05:00"])
    tipo: str = Field(examples=["ENTRADA"])
    motivo_codigo: str = Field(examples=["COMPRA"])
    cantidad: Cantidad = Field(examples=["150.000"])
    costo_unitario: Costo | None = Field(examples=["42.0000"], description="null en salidas")
    costo_total: Costo | None = Field(examples=["6300.0000"], description="cantidad × costo_unitario")
    saldo: Cantidad = Field(examples=["500.000"])
    costo_promedio: Costo = Field(examples=["39.2000"], description="(saldo anterior × promedio + entrada) ÷ saldo")
    valor_saldo: Costo = Field(examples=["19600.0000"], description="saldo × costo_promedio")


class Kardex(BaseModel):
    """Kardex valorizado por costo promedio ponderado (NIIF para Pymes, Sección 13 · DEC-11)."""

    producto_id: UUID = Field(examples=["0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b"])
    codigo: str = Field(examples=["REM-001"])
    nombre: str = Field(examples=["Acetona pura"])
    metodo: Literal["PROMEDIO_PONDERADO"] = "PROMEDIO_PONDERADO"
    lineas: list[LineaKardex]
    saldo_final: Cantidad = Field(examples=["500.000"])
    valor_final: Costo = Field(examples=["19600.0000"])


class GeometriaPunto(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float] = Field(
        description="[longitud, latitud] (EPSG:4326)", examples=[[-74.0645, 4.6484]]
    )


class PropiedadesProveedor(BaseModel):
    proveedor_id: UUID = Field(examples=["f0000000-0000-4000-8000-000000000001"])
    nombre: str = Field(examples=["Distribuidora Belleza Total"])
    telefono: str | None = Field(examples=["6015550101"])
    distancia_km: Decimal = Field(examples=["0.19"], description="Distancia geodésica desde el punto consultado")


class ProveedorCercano(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: GeometriaPunto
    properties: PropiedadesProveedor


class ColeccionProveedores(BaseModel):
    """GeoJSON (RFC 7946) listo para Leaflet, QGIS o ArcGIS."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[ProveedorCercano]
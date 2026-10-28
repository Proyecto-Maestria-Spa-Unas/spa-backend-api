"""Esquemas del contrato movimientos-v1. Cambiarlos cambia docs/openapi/movimientos-v1.yaml."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.compartido.tipos import Cantidad, Costo
from app.modulos.movimientos.domain.modelo import TipoMovimiento

PRODUCTO = "0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b"
PROVEEDOR = "f0000000-0000-4000-8000-000000000001"
USUARIO = "a0000000-0000-4000-8000-000000000002"


class MotivoMovimiento(BaseModel):
    id: int = Field(examples=[3])
    codigo: str = Field(examples=["CONSUMO_SERVICIO"])
    nombre: str = Field(examples=["Consumo en servicio"])
    aplica_a: TipoMovimiento = Field(description="Tipo de movimiento en el que se puede usar este motivo")


class EntradaRegistrar(BaseModel):
    producto_id: UUID = Field(examples=[PRODUCTO])
    cantidad: Cantidad = Field(gt=0, description="RN-04: decimales solo si la unidad los admite", examples=["500"])
    motivo_codigo: str = Field(examples=["COMPRA"], description="COMPRA, AJUSTE_CONTEO o SALDO_INICIAL")
    costo_unitario: Costo | None = Field(
        default=None,
        ge=0,
        description="Obligatorio en COMPRA: alimenta el costo promedio ponderado (DEC-11)",
        examples=["38.50"],
    )
    proveedor_id: UUID | None = Field(default=None, description="Proveedor de la compra", examples=[PROVEEDOR])
    observacion: str | None = Field(default=None, max_length=280, examples=["Factura FV-1023"])


class SalidaRegistrar(BaseModel):
    producto_id: UUID = Field(examples=[PRODUCTO])
    cantidad: Cantidad = Field(gt=0, examples=["15"], description="409 STOCK_INSUFICIENTE si supera el disponible")
    motivo_codigo: str = Field(examples=["CONSUMO_SERVICIO"], description="CONSUMO_SERVICIO, MERMA o VENCIMIENTO")
    observacion: str | None = Field(default=None, max_length=280, examples=["Retiro de semipermanente, cabina 2"])


class AnulacionRegistrar(BaseModel):
    motivo: str = Field(min_length=5, max_length=280, examples=["Registro duplicado por error de digitación"])
    confirmacion: Literal[True] = Field(description="Debe ser true: la anulación revierte el saldo")


class Movimiento(BaseModel):
    id: int = Field(examples=[42])
    producto_id: UUID = Field(examples=[PRODUCTO])
    tipo: TipoMovimiento
    motivo_codigo: str = Field(examples=["CONSUMO_SERVICIO"])
    cantidad: Cantidad = Field(examples=["15.000"])
    saldo_resultante: Cantidad = Field(
        examples=["335.000"], description="Stock del producto después de este movimiento"
    )
    costo_unitario: Costo | None = Field(default=None, examples=[None])
    costo_promedio_resultante: Costo | None = Field(
        default=None, description="Kardex valorizado (DEC-11)", examples=["39.2000"]
    )
    proveedor_id: UUID | None = None
    observacion: str | None = Field(default=None, examples=["Retiro de semipermanente, cabina 2"])
    registrado_por: UUID = Field(examples=[USUARIO], description="Usuario de la sesión (RN-07)")
    ocurrido_en: datetime = Field(examples=["2026-10-28T15:30:00-05:00"])
    movimiento_anulado_id: int | None = Field(default=None, description="Solo en ANULACION")
    anulado_por_id: int | None = Field(default=None, description="Id de la ANULACION que lo revirtió")


class MovimientoRegistrado(BaseModel):
    movimiento: Movimiento
    saldo: Cantidad = Field(examples=["335.000"])
    estado: str = Field(examples=["BAJO_STOCK"], description="Estado del producto tras el movimiento")
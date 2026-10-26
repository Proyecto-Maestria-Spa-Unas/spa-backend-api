"""Esquemas del contrato movimientos-v1. Cambiarlos cambia docs/openapi/movimientos-v1.yaml."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.compartido.tipos import Cantidad, Costo
from app.modulos.movimientos.domain.modelo import TipoMovimiento


class MotivoMovimiento(BaseModel):
    id: int
    codigo: str = Field(examples=["CONSUMO_SERVICIO"])
    nombre: str
    aplica_a: TipoMovimiento


class EntradaRegistrar(BaseModel):
    producto_id: UUID
    cantidad: Cantidad = Field(gt=0, description="RN-04: decimales solo si la unidad los admite")
    motivo_codigo: str = Field(examples=["COMPRA"])
    costo_unitario: Costo | None = Field(
        default=None, ge=0, description="Obligatorio en COMPRA: alimenta el costo promedio ponderado (DEC-11)"
    )
    proveedor_id: UUID | None = Field(default=None, description="Proveedor de la compra")
    observacion: str | None = Field(default=None, max_length=280)


class SalidaRegistrar(BaseModel):
    producto_id: UUID
    cantidad: Cantidad = Field(gt=0)
    motivo_codigo: str = Field(examples=["CONSUMO_SERVICIO"])
    observacion: str | None = Field(default=None, max_length=280)


class AnulacionRegistrar(BaseModel):
    motivo: str = Field(min_length=5, max_length=280)
    confirmacion: Literal[True] = Field(description="Debe ser true: la anulación revierte el saldo")


class Movimiento(BaseModel):
    id: int
    producto_id: UUID
    tipo: TipoMovimiento
    motivo_codigo: str
    cantidad: Cantidad
    saldo_resultante: Cantidad
    costo_unitario: Costo | None = None
    costo_promedio_resultante: Costo | None = Field(default=None, description="Kardex valorizado (DEC-11)")
    proveedor_id: UUID | None = None
    observacion: str | None = None
    registrado_por: UUID
    ocurrido_en: datetime
    movimiento_anulado_id: int | None = Field(default=None, description="Solo en ANULACION")
    anulado_por_id: int | None = Field(default=None, description="Id de la ANULACION que lo revirtió")


class MovimientoRegistrado(BaseModel):
    movimiento: Movimiento
    saldo: Cantidad
    estado: str = Field(examples=["BAJO_STOCK"], description="Estado del producto tras el movimiento")

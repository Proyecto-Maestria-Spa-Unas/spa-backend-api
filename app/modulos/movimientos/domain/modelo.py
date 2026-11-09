"""Modelo del dominio de movimientos. El movimiento es un libro mayor inmutable (kardex).

Se corrige con ANULACION, nunca con UPDATE ni DELETE (ADR-0003, DEC-06).
El saldo lo actualiza el trigger `trg_movimiento_aplicar` en la misma transacción del INSERT.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class TipoMovimiento(StrEnum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    ANULACION = "ANULACION"


@dataclass(slots=True)
class MotivoMovimiento:
    id: int
    codigo: str
    nombre: str
    aplica_a: TipoMovimiento


@dataclass(frozen=True, slots=True)
class Movimiento:
    id: int
    producto_id: UUID
    tipo: TipoMovimiento
    motivo_codigo: str
    cantidad: Decimal
    saldo_resultante: Decimal
    costo_unitario: Decimal | None
    costo_promedio_resultante: Decimal
    proveedor_id: UUID | None
    observacion: str | None
    registrado_por: UUID
    ocurrido_en: datetime


@dataclass(frozen=True, slots=True)
class MovimientoRegistrado:
    movimiento: Movimiento
    saldo: Decimal
    estado: str

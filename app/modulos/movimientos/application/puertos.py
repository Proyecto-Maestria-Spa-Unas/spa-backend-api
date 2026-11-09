"""Puertos de movimientos. Solo INSERT sobre inventario.movimiento."""

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modulos.movimientos.domain.modelo import (
    MotivoMovimiento,
    MovimientoRegistrado,
    TipoMovimiento,
)


class MovimientoRepository(Protocol):
    """Puerto para registrar movimientos y consultar motivos."""

    def registrar_entrada(
        self,
        producto_id: UUID,
        cantidad: Decimal,
        motivo_codigo: str,
        costo_unitario: Decimal | None,
        proveedor_id: UUID | None,
        observacion: str | None,
        registrado_por: UUID,
        clave_idempotencia: UUID,
    ) -> MovimientoRegistrado: ...

    def registrar_salida(
        self,
        producto_id: UUID,
        cantidad: Decimal,
        motivo_codigo: str,
        observacion: str | None,
        registrado_por: UUID,
        clave_idempotencia: UUID,
    ) -> MovimientoRegistrado: ...

    def listar_motivos(
        self,
        tipo: TipoMovimiento | None = None,
    ) -> list[MotivoMovimiento]: ...

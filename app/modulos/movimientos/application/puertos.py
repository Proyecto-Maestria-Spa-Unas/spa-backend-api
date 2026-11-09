"""Puertos de movimientos. Solo INSERT sobre inventario.movimiento."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modulos.movimientos.domain.modelo import Movimiento, MovimientoRegistrado, TipoMovimiento


class MovimientoRepository(Protocol):
    """Puerto para registrar movimientos de inventario."""

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

    def listar(
        self,
        producto_id: UUID | None,
        tipo: TipoMovimiento | None,
        usuario_id: UUID | None,
        desde: datetime | None,
        hasta: datetime | None,
        offset: int,
        limite: int,
    ) -> tuple[list[Movimiento], int]: ...

    def obtener(self, movimiento_id: int, usuario_id: UUID | None = None) -> Movimiento | None: ...

    def anular(
        self,
        movimiento_id: int,
        motivo: str,
        registrado_por: UUID,
        clave_idempotencia: UUID,
    ) -> MovimientoRegistrado: ...

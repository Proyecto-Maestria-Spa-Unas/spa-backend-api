"""Adaptador SQLAlchemy de MovimientoRepository.

Errores de la base que este adaptador traduce a errores de dominio (app.compartido.errores):
- CHECK de saldo o mensaje del trigger por stock → StockInsuficiente (409)
- UNIQUE de clave_idempotencia → devolver el movimiento existente (reintento seguro)
- UNIQUE de movimiento_anulado_id → MovimientoYaAnulado (409)
"""

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modulos.movimientos.domain.modelo import MotivoMovimiento, TipoMovimiento


class MovimientoRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(self, movimiento: Any, clave_idempotencia: UUID) -> Any:
        raise NotImplementedError

    def buscar_por_clave(self, clave_idempotencia: UUID) -> Any | None:
        raise NotImplementedError

    def obtener(self, movimiento_id: int) -> Any | None:
        raise NotImplementedError

    def listar_motivos(self, tipo: TipoMovimiento | None = None) -> list[MotivoMovimiento]:
        filas = (
            self._session.execute(
                text(
                    """
                    SELECT id, codigo, nombre, aplica_a
                    FROM inventario.motivo_movimiento
                    WHERE activo = TRUE
                    AND (
                        CAST(:tipo AS TEXT) IS NULL
                        OR aplica_a = :tipo
                    )
                    ORDER BY nombre, codigo
                    """
                ),
                {"tipo": tipo.value if tipo is not None else None},
            )
            .mappings()
            .all()
        )

        return [
            MotivoMovimiento(
                id=fila["id"],
                codigo=fila["codigo"],
                nombre=fila["nombre"],
                aplica_a=TipoMovimiento(fila["aplica_a"]),
            )
            for fila in filas
        ]

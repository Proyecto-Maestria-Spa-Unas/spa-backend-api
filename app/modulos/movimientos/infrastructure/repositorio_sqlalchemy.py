"""Adaptador SQLAlchemy de MovimientoRepository.

Errores de la base que este adaptador traduce a errores de dominio (app.compartido.errores):
- CHECK de saldo o mensaje del trigger por stock → StockInsuficiente (409)
- UNIQUE de clave_idempotencia → devolver el movimiento existente (reintento seguro)
- UNIQUE de movimiento_anulado_id → MovimientoYaAnulado (409)
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session


class MovimientoRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(self, movimiento: Any, clave_idempotencia: UUID) -> Any:
        raise NotImplementedError

    def buscar_por_clave(self, clave_idempotencia: UUID) -> Any | None:
        raise NotImplementedError

    def obtener(self, movimiento_id: int) -> Any | None:
        raise NotImplementedError

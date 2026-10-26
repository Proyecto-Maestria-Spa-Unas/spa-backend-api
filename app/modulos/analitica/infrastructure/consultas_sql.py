"""Adaptador de ConsultasAnaliticas sobre las vistas de S0 (security_invoker = true respeta RLS).

TODO (S4): implementar con SQLAlchemy `text()` sobre inventario.v_alerta_stock y movimiento.
Para el tablero y la exportación: pandas + DuckDB en memoria sobre el resultado de la consulta.
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session


class ConsultasAnaliticasSQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def alertas(self, estado: str | None) -> list[Any]:
        raise NotImplementedError

    def consumo(self, agrupar_por: str, desde: date, hasta: date) -> list[Any]:
        raise NotImplementedError

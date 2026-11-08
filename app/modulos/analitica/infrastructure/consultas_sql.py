"""Adaptador de ConsultasAnaliticas sobre las vistas de S0 (security_invoker = true respeta RLS).

Alertas y resumen (X4) leen inventario.v_alerta_stock con SQLAlchemy `text()`.
TODO (B14): consumo, tablero y exportación (pandas + DuckDB en memoria sobre el resultado de la consulta).
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modulos.analitica.domain.modelo import Alerta, EstadoAlerta, ResumenAlertas

# Primero los agotados y, dentro de cada grupo, los que más falta tienen; el resto del orden
# (nombre, código) hace que el resultado sea estable entre llamadas.
_ORDEN_ALERTAS = """
    ORDER BY CASE estado WHEN 'AGOTADO' THEN 0 ELSE 1 END,
             (stock_minimo - stock_actual) DESC,
             nombre,
             codigo
"""


class ConsultasAnaliticasSQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def alertas(self, estado: EstadoAlerta | None = None) -> list[Alerta]:
        filtro = "WHERE estado = :estado" if estado is not None else ""
        consulta = text(
            f"""
            SELECT id, codigo, nombre, stock_actual, stock_minimo, estado
            FROM inventario.v_alerta_stock
            {filtro}
            {_ORDEN_ALERTAS}
            """  # noqa: S608 - `filtro` es una constante del código, el valor viaja como parámetro
        )
        parametros = {"estado": estado.value} if estado is not None else {}
        filas = self._session.execute(consulta, parametros).mappings().all()
        return [
            Alerta(
                producto_id=fila["id"],
                codigo=fila["codigo"],
                nombre=fila["nombre"],
                stock_actual=Decimal(fila["stock_actual"]),
                stock_minimo=Decimal(fila["stock_minimo"]),
                estado=EstadoAlerta(fila["estado"]),
            )
            for fila in filas
        ]

    def resumen_alertas(self) -> ResumenAlertas:
        fila = (
            self._session.execute(
                text(
                    """
                    SELECT
                        count(*) FILTER (WHERE estado = 'BAJO_STOCK') AS bajo_stock,
                        count(*) FILTER (WHERE estado = 'AGOTADO')    AS agotado
                    FROM inventario.v_alerta_stock
                    """
                )
            )
            .mappings()
            .one()
        )
        return ResumenAlertas(bajo_stock=int(fila["bajo_stock"]), agotado=int(fila["agotado"]))

    def consumo(self, agrupar_por: str, desde: date, hasta: date) -> list[Any]:
        raise NotImplementedError

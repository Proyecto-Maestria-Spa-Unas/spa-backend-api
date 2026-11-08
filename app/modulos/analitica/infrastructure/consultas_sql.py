"""Adaptador de ConsultasAnaliticas sobre las vistas de S0 (D6 y D9). Solo SELECT.

Las fechas de los filtros son días de Bogotá: las vistas y estas consultas convierten
`ocurrido_en` con AT TIME ZONE 'America/Bogota' antes de compararlo.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from app.modulos.analitica.domain.modelo import (
    Alerta,
    ConsumoDiario,
    EstadoAlerta,
    LineaKardex,
    ProductoInventario,
    ProductoReferencia,
    ResumenAlertas,
)

# Primero los agotados y, dentro de cada grupo, los que más falta tienen; el resto del orden
# (nombre, código) hace que el resultado sea estable entre llamadas.
_ORDEN_ALERTAS = """
    ORDER BY CASE estado WHEN 'AGOTADO' THEN 0 ELSE 1 END,
             (stock_minimo - stock_actual) DESC,
             nombre,
             codigo
"""


def _linea(fila: RowMapping) -> LineaKardex:
    # A3 §3: la salida se valora al promedio vigente, por eso se usa costo_valoracion de v_kardex.
    return LineaKardex(
        ocurrido_en=fila["ocurrido_en"],
        tipo=fila["tipo"],
        motivo_codigo=fila["motivo_codigo"],
        cantidad=Decimal(fila["cantidad"]),
        costo_unitario=Decimal(fila["costo_valoracion"]) if fila["costo_valoracion"] is not None else None,
        costo_total=Decimal(fila["costo_total"]) if fila["costo_total"] is not None else None,
        saldo=Decimal(fila["saldo"]),
        costo_promedio=Decimal(fila["costo_promedio"]),
        valor_saldo=Decimal(fila["valor_saldo"]),
    )


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

    def inventario(self) -> list[ProductoInventario]:
        filas = self._session.execute(
            text(
                """
                SELECT id, codigo, nombre, estado, stock_actual, costo_promedio
                FROM inventario.v_inventario
                ORDER BY codigo
                """
            )
        ).mappings()
        return [
            ProductoInventario(
                producto_id=f["id"],
                codigo=f["codigo"],
                nombre=f["nombre"],
                estado=f["estado"],
                stock_actual=Decimal(f["stock_actual"]),
                costo_promedio=Decimal(f["costo_promedio"]),
            )
            for f in filas
        ]

    def consumo_diario(self, desde: date, hasta: date) -> list[ConsumoDiario]:
        filas = self._session.execute(
            text(
                """
                SELECT fecha, producto_id, codigo, nombre, categoria, sum(cantidad) AS cantidad
                FROM inventario.v_consumo_diario
                WHERE fecha BETWEEN :desde AND :hasta
                GROUP BY fecha, producto_id, codigo, nombre, categoria
                ORDER BY fecha, codigo
                """
            ),
            {"desde": desde, "hasta": hasta},
        ).mappings()
        return [
            ConsumoDiario(
                fecha=f["fecha"],
                producto_id=f["producto_id"],
                codigo=f["codigo"],
                nombre=f["nombre"],
                categoria=f["categoria"],
                cantidad=Decimal(f["cantidad"]),
            )
            for f in filas
        ]

    def producto(self, producto_id: UUID) -> ProductoReferencia | None:
        fila = (
            self._session.execute(
                text("SELECT id, codigo, nombre FROM inventario.producto WHERE id = :id"),
                {"id": producto_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            return None
        return ProductoReferencia(producto_id=fila["id"], codigo=fila["codigo"], nombre=fila["nombre"])

    def kardex(self, producto_id: UUID, desde: date | None, hasta: date | None) -> list[LineaKardex]:
        filas = self._session.execute(
            text(
                """
                SELECT ocurrido_en, tipo, motivo_codigo, cantidad, costo_valoracion, costo_total,
                       saldo, costo_promedio, valor_saldo
                FROM inventario.v_kardex
                WHERE producto_id = :producto_id
                  AND (CAST(:desde AS date) IS NULL
                       OR (ocurrido_en AT TIME ZONE 'America/Bogota')::date >= CAST(:desde AS date))
                  AND (CAST(:hasta AS date) IS NULL
                       OR (ocurrido_en AT TIME ZONE 'America/Bogota')::date <= CAST(:hasta AS date))
                ORDER BY id
                """
            ),
            {"producto_id": producto_id, "desde": desde, "hasta": hasta},
        ).mappings()
        return [_linea(f) for f in filas]

    def ultima_linea_kardex(self, producto_id: UUID, hasta: date | None) -> LineaKardex | None:
        fila = (
            self._session.execute(
                text(
                    """
                    SELECT ocurrido_en, tipo, motivo_codigo, cantidad, costo_valoracion, costo_total,
                       saldo, costo_promedio, valor_saldo
                    FROM inventario.v_kardex
                    WHERE producto_id = :producto_id
                      AND (CAST(:hasta AS date) IS NULL
                           OR (ocurrido_en AT TIME ZONE 'America/Bogota')::date <= CAST(:hasta AS date))
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"producto_id": producto_id, "hasta": hasta},
            )
            .mappings()
            .first()
        )
        return _linea(fila) if fila is not None else None

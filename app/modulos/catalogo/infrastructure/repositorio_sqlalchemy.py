
"""Adaptador SQLAlchemy de CatalogoRepository (esquema inventario)."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modulos.catalogo.domain.modelo import (
    Categoria,
    EstadoInventario,
    Magnitud,
    Producto,
    UnidadMedida,
)


class CatalogoRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_categorias(self, solo_activas: bool) -> list[Categoria]:
        raise NotImplementedError

    def listar_unidades(self) -> list[UnidadMedida]:
        raise NotImplementedError

    def _producto_desde_fila(self, fila: Any) -> Producto:
        return Producto(
            id=fila.id,
            codigo=fila.codigo,
            nombre=fila.nombre,
            descripcion=fila.descripcion,
            categoria_id=fila.categoria_id,
            unidad_medida_id=fila.unidad_medida_id,
            stock_actual=Decimal(fila.stock_actual),
            stock_minimo=(
                Decimal(fila.stock_minimo)
                if fila.stock_minimo is not None
                else None
            ),
            descontinuado=fila.descontinuado,
            version=fila.version,
            creado_en=fila.creado_en,
            actualizado_en=fila.actualizado_en,
        )

    def obtener_producto(self, producto_id: UUID) -> Producto | None:
        consulta = text("""
            SELECT id, codigo, nombre, descripcion,
                   categoria_id, unidad_medida_id,
                   stock_actual, stock_minimo, descontinuado,
                   version, creado_en, actualizado_en
            FROM inventario.producto
            WHERE id = :producto_id
        """)

        fila = self._session.execute(
            consulta, {"producto_id": producto_id}
        ).mappings().first()

        if fila is None:
            return None

        return self._producto_desde_fila(fila)

    def listar_productos(
        self,
        categoria_id: int | None,
        estado: EstadoInventario | None,
        q: str | None,
        incluir_descontinuados: bool,
        offset: int,
        limite: int,
    ) -> tuple[list[Producto], int]:
        filtros = """
            WHERE (:categoria_id IS NULL OR categoria_id = :categoria_id)
              AND (:estado IS NULL OR estado = :estado)
              AND (
                    :q IS NULL
                    OR codigo::text ILIKE :q
                    OR nombre ILIKE :q
                  )
              AND (
                    :incluir_descontinuados
                    OR descontinuado = false
                  )
        """

        parametros = {
            "categoria_id": categoria_id,
            "estado": estado.value if estado is not None else None,
            "q": f"%{q.strip()}%" if q and q.strip() else None,
            "incluir_descontinuados": incluir_descontinuados,
            "offset": offset,
            "limite": limite,
        }

        consulta_total = text(
            "SELECT COUNT(*) FROM inventario.producto " + filtros
        )

        total = self._session.execute(
            consulta_total, parametros
        ).scalar_one()

        consulta_productos = text("""
            SELECT id, codigo, nombre, descripcion,
                   categoria_id, unidad_medida_id,
                   stock_actual, stock_minimo, descontinuado,
                   version, creado_en, actualizado_en
            FROM inventario.producto
        """ + filtros + """
            ORDER BY nombre, codigo
            LIMIT :limite OFFSET :offset
        """)

        filas = self._session.execute(
            consulta_productos, parametros
        ).mappings().all()

        productos = [
            self._producto_desde_fila(fila)
            for fila in filas
        ]

        return productos, total

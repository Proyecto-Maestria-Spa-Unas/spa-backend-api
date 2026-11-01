
"""Pruebas de integración para la consulta de productos del catálogo."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modulos.catalogo.infrastructure.repositorio_sqlalchemy import (
    CatalogoRepositorySQL,
)

pytestmark = pytest.mark.integracion

def test_consultar_productos_y_obtener_detalle(transaccion: Connection) -> None:
    """Consulta productos, aplica filtros y recupera el detalle por UUID."""
    
    categoria_id = transaccion.execute(text("SELECT id FROM inventario.categoria ORDER BY id LIMIT 1")).scalar()

    unidad_id = transaccion.execute(text("SELECT id FROM inventario.unidad_medida WHERE codigo = 'UND'")).scalar()

    if categoria_id is None or unidad_id is None:
        pytest.skip("La base no tiene los datos de referencia del catálogo")

    codigo = f"B8-{uuid4().hex[:12].upper()}"

    with Session(bind=transaccion) as session:
        producto_id = session.execute(
            text("""
                INSERT INTO inventario.producto (
                    codigo,
                    nombre,
                    descripcion,
                    categoria_id,
                    unidad_medida_id,
                    stock_actual,
                    stock_minimo
                )
                VALUES (
                    :codigo,
                    'Producto de prueba B8',
                    'Registro temporal para pruebas',
                    :categoria_id,
                    :unidad_id,
                    10,
                    2
                )
                RETURNING id
            """),
            {
                "codigo": codigo,
                "categoria_id": categoria_id,
                "unidad_id": unidad_id,
            },
        ).scalar_one()

        repositorio = CatalogoRepositorySQL(session)

        productos, total = repositorio.listar_productos(
            categoria_id=categoria_id,
            estado=None,
            q=codigo,
            incluir_descontinuados=False,
            offset=0,
            limite=10,
        )

        assert total >= 1
        assert any(producto.id == producto_id for producto in productos)

        producto = repositorio.obtener_producto(producto_id)

        assert producto is not None
        assert producto.id == producto_id
        assert producto.codigo == codigo
        assert producto.nombre == "Producto de prueba B8"
        assert producto.estado.value == "DISPONIBLE"

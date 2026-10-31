"""Pruebas unitarias de frontera para el dominio del catálogo (B3)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modulos.catalogo.domain.modelo import (
    Categoria,
    EstadoInventario,
    Magnitud,
    Producto,
    UnidadMedida,
    calcular_estado_inventario,
)


@pytest.mark.parametrize(
    ("stock_actual", "stock_minimo", "descontinuado", "esperado"),
    [
        (Decimal("10"), Decimal("5"), False, EstadoInventario.DISPONIBLE),
        (Decimal("1"), None, False, EstadoInventario.DISPONIBLE),
        (Decimal("1"), Decimal("0"), False, EstadoInventario.DISPONIBLE),
        (Decimal("5"), Decimal("5"), False, EstadoInventario.BAJO_STOCK),
        (Decimal("4.999"), Decimal("5"), False, EstadoInventario.BAJO_STOCK),
        (Decimal("0"), Decimal("5"), False, EstadoInventario.AGOTADO),
        (Decimal("0"), None, False, EstadoInventario.AGOTADO),
        (Decimal("10"), Decimal("5"), True, EstadoInventario.DESCONTINUADO),
        (Decimal("0"), Decimal("5"), True, EstadoInventario.DESCONTINUADO),
    ],
)
def test_calcular_estado_inventario(
    stock_actual: Decimal,
    stock_minimo: Decimal | None,
    descontinuado: bool,
    esperado: EstadoInventario,
) -> None:
    assert calcular_estado_inventario(stock_actual, stock_minimo, descontinuado) == esperado


def test_producto_expone_estado_derivado() -> None:
    ahora = datetime.now(UTC)
    producto = Producto(
        id=uuid4(),
        codigo="REM-001",
        nombre="Removedor",
        descripcion=None,
        categoria_id=1,
        unidad_medida_id=2,
        stock_actual=Decimal("3"),
        stock_minimo=Decimal("3"),
        descontinuado=False,
        version=1,
        creado_en=ahora,
        actualizado_en=ahora,
    )

    assert producto.estado is EstadoInventario.BAJO_STOCK


def test_entidades_basicas_del_catalogo() -> None:
    categoria = Categoria(id=1, nombre="Esmaltes")
    unidad = UnidadMedida(
        id=2,
        codigo="ML",
        nombre="Mililitro",
        magnitud=Magnitud.VOLUMEN,
        admite_decimales=True,
    )

    assert categoria.activa is True
    assert categoria.orden == 0
    assert unidad.magnitud is Magnitud.VOLUMEN

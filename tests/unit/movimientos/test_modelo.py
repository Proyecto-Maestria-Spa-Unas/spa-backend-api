"""Pruebas unitarias del dominio de movimientos (X1)."""

from app.modulos.movimientos.domain.modelo import MotivoMovimiento, TipoMovimiento


def test_motivo_movimiento() -> None:
    motivo = MotivoMovimiento(
        id=1,
        codigo="COMPRA",
        nombre="Ingreso de productos por compra a proveedor",
        aplica_a=TipoMovimiento.ENTRADA,
    )

    assert motivo.id == 1
    assert motivo.codigo == "COMPRA"
    assert motivo.nombre == "Ingreso de productos por compra a proveedor"
    assert motivo.aplica_a is TipoMovimiento.ENTRADA


def test_motivo_movimiento_salida() -> None:
    motivo = MotivoMovimiento(
        id=2,
        codigo="MERMA",
        nombre="Disminución de inventario por merma",
        aplica_a=TipoMovimiento.SALIDA,
    )

    assert motivo.aplica_a is TipoMovimiento.SALIDA

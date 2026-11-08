"""#59 · CP-HU02-06 contra la base real: el disparador de D7 rechaza decimales y la API lo traduce a 422."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

from app.compartido.errores import DatosInvalidos, error_de_base

pytestmark = pytest.mark.integracion


def test_saldo_inicial_con_decimales_en_unidad_entera(transaccion: Connection) -> None:
    if not transaccion.execute(text("SELECT to_regclass('inventario.movimiento') IS NOT NULL")).scalar():
        pytest.skip("La base no tiene la tabla de movimientos (D7)")
    categoria = transaccion.execute(text("SELECT id FROM inventario.categoria ORDER BY id LIMIT 1")).scalar()
    unidad = transaccion.execute(
        text("SELECT id FROM inventario.unidad_medida WHERE NOT admite_decimales LIMIT 1")
    ).scalar()
    motivo = transaccion.execute(
        text("SELECT id FROM inventario.motivo_movimiento WHERE codigo = 'SALDO_INICIAL'")
    ).scalar()
    if None in (categoria, unidad, motivo):
        pytest.skip("La base no tiene los datos de referencia necesarios")
    # Usuario propio: la transacción se revierte al terminar, así que no queda en la base.
    usuario = transaccion.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:i, :e) RETURNING id"),
        {"i": uuid4(), "e": f"t59-{uuid4().hex[:8]}@example.test"},
    ).scalar()
    producto = transaccion.execute(
        text(
            "INSERT INTO inventario.producto (codigo, nombre, categoria_id, unidad_medida_id) "
            "VALUES (:c, 'Prueba #59', :cat, :u) RETURNING id"
        ),
        {"c": f"T59-{uuid4().hex[:8]}", "cat": categoria, "u": unidad},
    ).scalar()

    with pytest.raises(DBAPIError) as capturado, transaccion.begin_nested():
        transaccion.execute(
            text(
                "INSERT INTO inventario.movimiento (producto_id, tipo, motivo_id, cantidad, clave_idempotencia, "
                "registrado_por) VALUES (:p, 'ENTRADA', :m, 2.5, :k, :r)"
            ),
            {"p": producto, "m": motivo, "k": uuid4(), "r": usuario},
        )

    error = error_de_base(capturado.value)
    assert isinstance(error, DatosInvalidos)
    assert error.status == 422

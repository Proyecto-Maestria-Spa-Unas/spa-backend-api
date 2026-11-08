"""B14 y X7 · adaptador SQL sobre las vistas de D9 con el kardex del ejemplo de A3."""

from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modulos.analitica.infrastructure.consultas_sql import ConsultasAnaliticasSQL

pytestmark = pytest.mark.integracion
D = Decimal


@pytest.fixture
def con_kardex(transaccion: Connection) -> Iterator[tuple[Session, UUID]]:
    """Producto de prueba con los movimientos del ejemplo de A3 (todo se revierte al final)."""
    if transaccion.execute(text("SELECT to_regclass('inventario.v_kardex')")).scalar() is None:
        pytest.skip("La base no tiene las vistas de D9")
    usuario = uuid4()
    transaccion.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"), {"id": usuario, "email": f"{usuario}@x7.test"}
    )
    producto = transaccion.execute(
        text(
            """
            INSERT INTO inventario.producto (codigo, nombre, categoria_id, unidad_medida_id)
            SELECT :codigo, 'Acetona X7', c.id, u.id
            FROM inventario.categoria c, inventario.unidad_medida u
            WHERE c.nombre = 'Removedores' AND u.codigo = 'ML'
            RETURNING id
            """
        ),
        {"codigo": f"X7-{uuid4().hex[:8].upper()}"},
    ).scalar_one()
    for tipo, motivo, cantidad, costo in [
        ("ENTRADA", "SALDO_INICIAL", 350, 38),
        ("ENTRADA", "COMPRA", 150, 42),
        ("SALIDA", "CONSUMO_SERVICIO", 15, None),
        ("ENTRADA", "COMPRA", 100, 45),
        ("SALIDA", "MERMA", 85, None),
    ]:
        transaccion.execute(
            text(
                """
                INSERT INTO inventario.movimiento
                  (producto_id, tipo, motivo_id, cantidad, costo_unitario, registrado_por, clave_idempotencia)
                SELECT :producto, :tipo, id, :cantidad, :costo, :usuario, gen_random_uuid()
                FROM inventario.motivo_movimiento WHERE codigo = :motivo
                """
            ),
            {
                "producto": producto,
                "tipo": tipo,
                "motivo": motivo,
                "cantidad": cantidad,
                "costo": costo,
                "usuario": usuario,
            },
        )
    with Session(bind=transaccion) as session:
        yield session, producto


def test_kardex_cuadra_con_a3(con_kardex: tuple[Session, UUID]) -> None:
    session, producto = con_kardex
    consultas = ConsultasAnaliticasSQL(session)
    lineas = consultas.kardex(producto, None, None)
    assert [(linea.saldo, linea.costo_promedio, linea.valor_saldo) for linea in lineas] == [
        (D("350.000"), D("38.0000"), D("13300.0000")),
        (D("500.000"), D("39.2000"), D("19600.0000")),
        (D("485.000"), D("39.2000"), D("19012.0000")),
        (D("585.000"), D("40.1915"), D("23512.0275")),
        (D("500.000"), D("40.1915"), D("20095.7500")),
    ]
    salida = lineas[2]
    assert (salida.tipo, salida.motivo_codigo, salida.costo_unitario, salida.costo_total) == (
        "SALIDA",
        "CONSUMO_SERVICIO",
        D("39.2000"),
        D("588.0000"),
    )
    ultima = consultas.ultima_linea_kardex(producto, None)
    assert ultima is not None and ultima.valor_saldo == D("20095.7500")
    referencia = consultas.producto(producto)
    assert referencia is not None and referencia.nombre == "Acetona X7"
    assert consultas.producto(uuid4()) is None


def test_consumo_e_inventario(con_kardex: tuple[Session, UUID]) -> None:
    session, producto = con_kardex
    consultas = ConsultasAnaliticasSQL(session)
    hoy = session.execute(text("SELECT (now() AT TIME ZONE 'America/Bogota')::date")).scalar_one()
    consumo = [c for c in consultas.consumo_diario(hoy, hoy) if c.producto_id == producto]
    assert len(consumo) == 1
    assert (consumo[0].categoria, consumo[0].cantidad) == ("Removedores", D("100.000"))
    fila = next(p for p in consultas.inventario() if p.producto_id == producto)
    assert (fila.stock_actual, fila.costo_promedio, fila.estado) == (D("500.000"), D("40.1915"), "DISPONIBLE")

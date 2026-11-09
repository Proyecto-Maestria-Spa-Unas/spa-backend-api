"""X5 · Exportación contra las vistas reales de S0 (v_inventario y v_kardex) con el kardex del ejemplo de A3."""

import csv
import io
import tempfile
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import duckdb
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modulos.analitica.infrastructure.exportador_duckdb import BOM_UTF8, CONJUNTOS, ExportadorDuckDB

pytestmark = pytest.mark.integracion
D = Decimal


@pytest.fixture
def con_kardex(transaccion: Connection) -> Iterator[tuple[Session, UUID, str]]:
    """Producto de prueba con los 5 movimientos de A3 (todo se revierte al final)."""
    if transaccion.execute(text("SELECT to_regclass('inventario.v_kardex')")).scalar() is None:
        pytest.skip("La base no tiene las vistas de D9")
    usuario = uuid4()
    transaccion.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"), {"id": usuario, "email": f"{usuario}@x5.test"}
    )
    codigo = f"X5-{uuid4().hex[:8].upper()}"
    producto = transaccion.execute(
        text(
            """
            INSERT INTO inventario.producto (codigo, nombre, categoria_id, unidad_medida_id)
            SELECT :codigo, 'Acetona cañón X5', c.id, u.id
            FROM inventario.categoria c, inventario.unidad_medida u
            WHERE c.nombre = 'Removedores' AND u.codigo = 'ML'
            RETURNING id
            """
        ),
        {"codigo": codigo},
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
        yield session, producto, codigo


def _filas_csv(contenido: bytes) -> list[dict[str, str]]:
    assert contenido.startswith(BOM_UTF8)
    return list(csv.DictReader(io.StringIO(contenido[len(BOM_UTF8) :].decode("utf-8"))))


def _filas_parquet(contenido: bytes, columnas: str, filtro: str) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as carpeta:
        archivo = Path(carpeta) / "datos.parquet"
        archivo.write_bytes(contenido)
        with duckdb.connect() as con:
            cursor = con.execute(f"SELECT {columnas} FROM '{archivo}' WHERE {filtro}")  # noqa: S608
            nombres = [c[0] for c in cursor.description]
            return [dict(zip(nombres, fila, strict=True)) for fila in cursor.fetchall()]


def test_inventario_csv_trae_el_producto_con_su_valor(con_kardex: tuple[Session, UUID, str]) -> None:
    session, producto, codigo = con_kardex
    filas = _filas_csv(ExportadorDuckDB(session).exportar("inventario", "csv"))
    assert list(filas[0]) == [nombre for nombre, _ in CONJUNTOS["inventario"].columnas]
    (fila,) = [f for f in filas if f["codigo"] == codigo]
    assert fila["producto_id"] == str(producto)
    assert fila["nombre"] == "Acetona cañón X5"
    assert (fila["categoria"], fila["unidad_medida"], fila["estado"]) == ("Removedores", "ML", "DISPONIBLE")
    assert (fila["stock_actual"], fila["costo_promedio"], fila["valor_inventario"]) == (
        "500.000",
        "40.1915",
        "20095.7500",
    )
    assert fila["descontinuado"] == "false"
    assert fila["stock_minimo"] == ""  # sin mínimo registrado: vacío, no 0


def test_inventario_parquet_tiene_decimales_exactos(con_kardex: tuple[Session, UUID, str]) -> None:
    session, _, codigo = con_kardex
    (fila,) = _filas_parquet(
        ExportadorDuckDB(session).exportar("inventario", "parquet"),
        "stock_actual, valor_inventario, stock_minimo, descontinuado, typeof(actualizado_en) AS tipo_fecha",
        f"codigo = '{codigo}'",
    )
    assert fila["stock_actual"] == D("500.000")
    assert fila["valor_inventario"] == D("20095.7500")
    assert fila["stock_minimo"] is None
    assert fila["descontinuado"] is False
    assert fila["tipo_fecha"] == "TIMESTAMP WITH TIME ZONE"


def test_movimientos_csv_reproduce_el_kardex_de_a3(con_kardex: tuple[Session, UUID, str]) -> None:
    session, _, codigo = con_kardex
    filas = [f for f in _filas_csv(ExportadorDuckDB(session).exportar("movimientos", "csv")) if f["codigo"] == codigo]
    assert [(f["tipo"], f["motivo_codigo"], f["saldo"], f["costo_promedio"], f["valor_saldo"]) for f in filas] == [
        ("ENTRADA", "SALDO_INICIAL", "350.000", "38.0000", "13300.0000"),
        ("ENTRADA", "COMPRA", "500.000", "39.2000", "19600.0000"),
        ("SALIDA", "CONSUMO_SERVICIO", "485.000", "39.2000", "19012.0000"),
        ("ENTRADA", "COMPRA", "585.000", "40.1915", "23512.0275"),
        ("SALIDA", "MERMA", "500.000", "40.1915", "20095.7500"),
    ]
    salida = filas[2]
    assert (salida["cantidad"], salida["cantidad_neta"], salida["costo_unitario"], salida["costo_total"]) == (
        "15.000",
        "-15.000",
        "",
        "588.0000",
    )
    assert filas[0]["ocurrido_en"].endswith("-05")  # hora de Bogotá


def test_movimientos_parquet_sale_ordenado_por_id(con_kardex: tuple[Session, UUID, str]) -> None:
    session, _, codigo = con_kardex
    filas = _filas_parquet(
        ExportadorDuckDB(session).exportar("movimientos", "parquet"),
        "id, saldo, costo_unitario, costo_total",
        f"codigo = '{codigo}' ORDER BY id",
    )
    assert [f["saldo"] for f in filas] == [D("350.000"), D("500.000"), D("485.000"), D("585.000"), D("500.000")]
    assert filas[2]["costo_unitario"] is None and filas[2]["costo_total"] == D("588.0000")

"""X5 · Exportación a CSV y Parquet con DuckDB en memoria (RNF-10).

Las filas salen de las vistas de S0 (`v_inventario` y `v_kardex`, solo SELECT) y se cargan en un DataFrame de
pandas de texto. DuckDB las convierte a su tipo (DECIMAL, TIMESTAMPTZ, BOOLEAN...) y escribe el archivo, para no
perder precisión con números de punto flotante: 24.000 sale como `24.000` y se guarda como DECIMAL(14,3) en Parquet.

* CSV: UTF-8 con BOM (así Excel respeta tildes y eñes), separador coma y punto decimal.
* Parquet: tipos exactos (DECIMAL, TIMESTAMP WITH TIME ZONE, BOOLEAN).
* Las fechas se escriben en hora de Bogotá con su desfase (`2026-11-07 14:30:00-05`).
* Los nombres de las vistas y de las columnas son constantes de este archivo: nada de lo que envía el usuario
  entra a una consulta.
"""

import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from sqlalchemy import TextClause, text
from sqlalchemy.orm import Session

BOM_UTF8 = b"\xef\xbb\xbf"
ZONA_HORARIA = "America/Bogota"


@dataclass(frozen=True)
class Conjunto:
    consulta: TextClause
    columnas: tuple[tuple[str, str], ...]  # (nombre, tipo de DuckDB), en el orden del archivo


_INVENTARIO = Conjunto(
    consulta=text(
        """
        SELECT id AS producto_id, codigo, nombre, descripcion, categoria, unidad_medida,
               stock_actual, stock_minimo, costo_promedio,
               round(valor_inventario, 4) AS valor_inventario,
               estado, descontinuado, actualizado_en
        FROM inventario.v_inventario
        ORDER BY codigo
        """
    ),
    columnas=(
        ("producto_id", "VARCHAR"),
        ("codigo", "VARCHAR"),
        ("nombre", "VARCHAR"),
        ("descripcion", "VARCHAR"),
        ("categoria", "VARCHAR"),
        ("unidad_medida", "VARCHAR"),
        ("stock_actual", "DECIMAL(14, 3)"),
        ("stock_minimo", "DECIMAL(14, 3)"),
        ("costo_promedio", "DECIMAL(14, 4)"),
        ("valor_inventario", "DECIMAL(28, 4)"),
        ("estado", "VARCHAR"),
        ("descontinuado", "BOOLEAN"),
        ("actualizado_en", "TIMESTAMPTZ"),
    ),
)

_MOVIMIENTOS = Conjunto(
    consulta=text(
        """
        SELECT id, producto_id, codigo, nombre, ocurrido_en, tipo, motivo_codigo,
               cantidad, cantidad_neta, costo_unitario, costo_valoracion, costo_total,
               saldo, costo_promedio, valor_saldo,
               movimiento_anulado_id, anulado_por_id, proveedor_id, registrado_por, observacion
        FROM inventario.v_kardex
        ORDER BY id
        """
    ),
    columnas=(
        ("id", "BIGINT"),
        ("producto_id", "VARCHAR"),
        ("codigo", "VARCHAR"),
        ("nombre", "VARCHAR"),
        ("ocurrido_en", "TIMESTAMPTZ"),
        ("tipo", "VARCHAR"),
        ("motivo_codigo", "VARCHAR"),
        ("cantidad", "DECIMAL(14, 3)"),
        ("cantidad_neta", "DECIMAL(14, 3)"),
        ("costo_unitario", "DECIMAL(14, 4)"),
        ("costo_valoracion", "DECIMAL(14, 4)"),
        ("costo_total", "DECIMAL(28, 4)"),
        ("saldo", "DECIMAL(14, 3)"),
        ("costo_promedio", "DECIMAL(14, 4)"),
        ("valor_saldo", "DECIMAL(28, 4)"),
        ("movimiento_anulado_id", "BIGINT"),
        ("anulado_por_id", "BIGINT"),
        ("proveedor_id", "VARCHAR"),
        ("registrado_por", "VARCHAR"),
        ("observacion", "VARCHAR"),
    ),
)

CONJUNTOS: dict[str, Conjunto] = {"inventario": _INVENTARIO, "movimientos": _MOVIMIENTOS}


def _texto(valor: Any) -> str | None:
    """Valor de la base como texto exacto; DuckDB lo convierte al tipo de la columna."""
    if valor is None:
        return None
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, datetime):
        return valor.isoformat()
    return str(valor)


def serializar(columnas: Sequence[tuple[str, str]], filas: Sequence[Mapping[Any, Any]], formato: str) -> bytes:
    """Escribe las filas en CSV o Parquet con DuckDB. `formato` solo puede ser "csv" o "parquet"."""
    if formato not in ("csv", "parquet"):
        raise ValueError(f"Formato no soportado: {formato}")
    marco = pd.DataFrame(
        {nombre: pd.Series([_texto(f[nombre]) for f in filas], dtype="object") for nombre, _ in columnas}
    )
    seleccion = ", ".join(f'CAST("{nombre}" AS {tipo}) AS "{nombre}"' for nombre, tipo in columnas)
    opciones = "FORMAT csv, HEADER true" if formato == "csv" else "FORMAT parquet, COMPRESSION zstd"
    with tempfile.TemporaryDirectory() as carpeta, duckdb.connect() as con:
        destino = Path(carpeta) / f"exportacion.{formato}"
        con.execute(f"SET TimeZone = '{ZONA_HORARIA}'")
        con.register("datos", marco)
        con.execute(f"COPY (SELECT {seleccion} FROM datos) TO '{destino}' ({opciones})")  # noqa: S608
        contenido = destino.read_bytes()
    return BOM_UTF8 + contenido if formato == "csv" else contenido


class ExportadorDuckDB:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exportar(self, conjunto: str, formato: str) -> bytes:
        definicion = CONJUNTOS[conjunto]
        filas = self._session.execute(definicion.consulta).mappings().all()
        return serializar(definicion.columnas, filas, formato)

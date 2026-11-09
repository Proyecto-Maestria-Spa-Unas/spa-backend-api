"""X5 · Exportación (RNF-10): nombre del archivo, caso de uso, escritura CSV/Parquet con DuckDB y endpoint."""

import csv
import io
import tempfile
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.compartido.errores import DatosInvalidos
from app.main import app
from app.modulos.analitica.api.router import hoy_bogota, obtener_exportador
from app.modulos.analitica.application.exportacion import ExportarDatos
from app.modulos.analitica.domain.exportacion import nombre_archivo
from app.modulos.analitica.infrastructure.exportador_duckdb import BOM_UTF8, CONJUNTOS, serializar
from tests.conftest import FabricaToken

EXPORTAR = f"{get_settings().api_prefix}/analitica/exportar"
DIA = date(2026, 11, 8)

COLUMNAS_INVENTARIO = CONJUNTOS["inventario"].columnas
FILA_INVENTARIO = {
    "producto_id": "0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b",
    "codigo": "REM-001",
    "nombre": 'Acetona "pura", 100 ml · cañón',
    "descripcion": None,
    "categoria": "Removedores",
    "unidad_medida": "ML",
    "stock_actual": Decimal("350.000"),
    "stock_minimo": None,
    "costo_promedio": Decimal("39.2000"),
    "valor_inventario": Decimal("13720.0000"),
    "estado": "DISPONIBLE",
    "descontinuado": False,
    "actualizado_en": datetime(2026, 11, 7, 19, 30, tzinfo=UTC),
}


def _leer_csv(contenido: bytes) -> list[dict[str, str]]:
    assert contenido.startswith(BOM_UTF8)
    return list(csv.DictReader(io.StringIO(contenido[len(BOM_UTF8) :].decode("utf-8"))))


def _consultar_parquet(contenido: bytes, consulta: str) -> list[tuple[Any, ...]]:
    with tempfile.TemporaryDirectory() as carpeta:
        archivo = Path(carpeta) / "datos.parquet"
        archivo.write_bytes(contenido)
        with duckdb.connect() as con:
            return con.execute(consulta.format(archivo=archivo)).fetchall()


# ── Dominio y caso de uso ──────────────────────────────────────────────────


def test_nombre_del_archivo_lleva_conjunto_dia_y_formato() -> None:
    assert nombre_archivo("inventario", "csv", DIA) == "inventario-20261108.csv"
    assert nombre_archivo("movimientos", "parquet", date(2026, 1, 5)) == "movimientos-20260105.parquet"


class ExportadorFalso:
    def __init__(self, contenido: bytes = b"datos") -> None:
        self.contenido = contenido
        self.pedidos: list[tuple[str, str]] = []

    def exportar(self, conjunto: str, formato: str) -> bytes:
        self.pedidos.append((conjunto, formato))
        return self.contenido


@pytest.mark.parametrize(("formato", "tipo"), [("csv", "text/csv"), ("parquet", "application/vnd.apache.parquet")])
def test_exportar_devuelve_contenido_tipo_y_nombre(formato: str, tipo: str) -> None:
    falso = ExportadorFalso(b"abc")
    archivo = ExportarDatos(falso)("movimientos", formato, DIA)
    assert (archivo.contenido, archivo.tipo_mime, archivo.nombre) == (b"abc", tipo, f"movimientos-20261108.{formato}")
    assert falso.pedidos == [("movimientos", formato)]


def test_exportar_rechaza_conjunto_y_formato_desconocidos_sin_tocar_los_datos() -> None:
    falso = ExportadorFalso()
    with pytest.raises(DatosInvalidos) as error:
        ExportarDatos(falso)("proveedores", "xlsx", DIA)
    assert [e["campo"] for e in error.value.errors] == ["conjunto", "formato"]
    assert falso.pedidos == []


# ── Escritura con DuckDB ───────────────────────────────────────────────────


def test_csv_tiene_bom_encabezado_y_valores_exactos() -> None:
    (fila,) = _leer_csv(serializar(COLUMNAS_INVENTARIO, [FILA_INVENTARIO], "csv"))
    assert list(fila) == [nombre for nombre, _ in COLUMNAS_INVENTARIO]
    assert fila["stock_actual"] == "350.000"  # sin errores de punto flotante
    assert fila["costo_promedio"] == "39.2000"
    assert fila["valor_inventario"] == "13720.0000"
    assert fila["descontinuado"] == "false"
    assert fila["estado"] == "DISPONIBLE"


def test_csv_respeta_comillas_comas_tildes_y_vacios() -> None:
    (fila,) = _leer_csv(serializar(COLUMNAS_INVENTARIO, [FILA_INVENTARIO], "csv"))
    assert fila["nombre"] == 'Acetona "pura", 100 ml · cañón'
    assert fila["descripcion"] == ""
    assert fila["stock_minimo"] == ""


def test_las_fechas_salen_en_hora_de_bogota() -> None:
    (fila,) = _leer_csv(serializar(COLUMNAS_INVENTARIO, [FILA_INVENTARIO], "csv"))
    assert fila["actualizado_en"] == "2026-11-07 14:30:00-05"


def test_parquet_conserva_los_tipos_exactos() -> None:
    contenido = serializar(COLUMNAS_INVENTARIO, [FILA_INVENTARIO], "parquet")
    assert contenido[:4] == b"PAR1"
    tipos = dict(
        (nombre, tipo) for nombre, tipo, *_ in _consultar_parquet(contenido, "DESCRIBE SELECT * FROM '{archivo}'")
    )
    assert tipos["stock_actual"] == "DECIMAL(14,3)"
    assert tipos["valor_inventario"] == "DECIMAL(28,4)"
    assert tipos["descontinuado"] == "BOOLEAN"
    assert tipos["actualizado_en"] == "TIMESTAMP WITH TIME ZONE"
    (fila,) = _consultar_parquet(contenido, "SELECT stock_actual, stock_minimo, nombre, descontinuado FROM '{archivo}'")
    assert fila == (Decimal("350.000"), None, 'Acetona "pura", 100 ml · cañón', False)


def test_parquet_guarda_el_instante_correcto() -> None:
    contenido = serializar(COLUMNAS_INVENTARIO, [FILA_INVENTARIO], "parquet")
    (instante,) = _consultar_parquet(contenido, "SELECT epoch(actualizado_en)::BIGINT FROM '{archivo}'")
    assert instante == (int(datetime(2026, 11, 7, 19, 30, tzinfo=UTC).timestamp()),)


@pytest.mark.parametrize("conjunto", sorted(CONJUNTOS))
def test_sin_filas_el_csv_trae_solo_el_encabezado_y_el_parquet_las_columnas(conjunto: str) -> None:
    columnas = CONJUNTOS[conjunto].columnas
    assert _leer_csv(serializar(columnas, [], "csv")) == []
    encabezado = serializar(columnas, [], "csv")[len(BOM_UTF8) :].decode().strip()
    assert encabezado == ",".join(nombre for nombre, _ in columnas)
    contenido = serializar(columnas, [], "parquet")
    assert _consultar_parquet(contenido, "SELECT count(*) FROM '{archivo}'") == [(0,)]
    descritas = [f[0] for f in _consultar_parquet(contenido, "DESCRIBE SELECT * FROM '{archivo}'")]
    assert descritas == [nombre for nombre, _ in columnas]


def test_formato_no_soportado_falla() -> None:
    with pytest.raises(ValueError, match="no soportado"):
        serializar(COLUMNAS_INVENTARIO, [], "xlsx")


def test_los_dos_conjuntos_tienen_las_columnas_de_su_consulta() -> None:
    """Cada columna del archivo sale de la consulta (si no, KeyError al exportar)."""
    for definicion in CONJUNTOS.values():
        sql = str(definicion.consulta)
        for nombre, _ in definicion.columnas:
            assert nombre in sql


# ── Endpoint ───────────────────────────────────────────────────────────────


@pytest.fixture
def con_exportador() -> Iterator[ExportadorFalso]:
    falso = ExportadorFalso(b"codigo\nREM-001\n")
    app.dependency_overrides[obtener_exportador] = lambda: falso
    app.dependency_overrides[hoy_bogota] = lambda: DIA
    yield falso
    app.dependency_overrides.clear()


def test_exportar_csv_es_el_formato_por_defecto(
    cliente: TestClient, cabeceras: FabricaToken, con_exportador: ExportadorFalso
) -> None:
    r = cliente.get(EXPORTAR, params={"conjunto": "inventario"}, headers=cabeceras("analitica.consultar"))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"] == 'attachment; filename="inventario-20261108.csv"'
    assert r.headers["cache-control"] == "no-store"
    assert r.content == b"codigo\nREM-001\n"
    assert con_exportador.pedidos == [("inventario", "csv")]


def test_exportar_parquet(cliente: TestClient, cabeceras: FabricaToken, con_exportador: ExportadorFalso) -> None:
    r = cliente.get(
        EXPORTAR, params={"conjunto": "movimientos", "formato": "parquet"}, headers=cabeceras("analitica.consultar")
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/vnd.apache.parquet"
    assert r.headers["content-disposition"] == 'attachment; filename="movimientos-20261108.parquet"'
    assert con_exportador.pedidos == [("movimientos", "parquet")]


def test_exportar_sin_token_responde_401(cliente: TestClient, con_exportador: ExportadorFalso) -> None:
    r = cliente.get(EXPORTAR, params={"conjunto": "inventario"})
    assert r.status_code == 401
    assert r.json()["code"] == "NO_AUTENTICADO"
    assert con_exportador.pedidos == []


def test_exportar_sin_el_permiso_responde_403(
    cliente: TestClient, cabeceras: FabricaToken, con_exportador: ExportadorFalso
) -> None:
    r = cliente.get(EXPORTAR, params={"conjunto": "inventario"}, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 403
    assert r.json()["code"] == "SIN_PERMISO"
    assert con_exportador.pedidos == []


@pytest.mark.parametrize(
    ("params", "campo"),
    [
        ({}, "query.conjunto"),
        ({"conjunto": "proveedores"}, "query.conjunto"),
        ({"conjunto": "inventario", "formato": "xlsx"}, "query.formato"),
    ],
)
def test_exportar_con_parametros_invalidos_responde_422(
    cliente: TestClient, cabeceras: FabricaToken, con_exportador: ExportadorFalso, params: dict[str, str], campo: str
) -> None:
    r = cliente.get(EXPORTAR, params=params, headers=cabeceras("analitica.consultar"))
    assert r.status_code == 422
    assert r.json()["code"] == "DATOS_INVALIDOS"
    assert campo in [e["campo"] for e in r.json()["errors"]]
    assert con_exportador.pedidos == []

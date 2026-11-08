"""B14 · Tablero, consumo y cobertura.

Las filas que entrega el puerto se cargan en un DataFrame de pandas y se agregan con DuckDB
en memoria. Las cantidades viajan como texto y DuckDB las convierte a DECIMAL, para no perder
precisión con números de punto flotante.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import duckdb
import pandas as pd

from app.compartido.errores import DatosInvalidos
from app.modulos.analitica.application.puertos import ConsultasAnaliticas
from app.modulos.analitica.domain.modelo import (
    DIAS_VENTANA_CONSUMO,
    AgrupacionConsumo,
    ConsumoDiario,
    dias_cobertura,
    valor_inventario,
)

TOP_ROTACION = 10
CERO = Decimal("0.000")


@dataclass(frozen=True)
class FilaRotacion:
    producto_id: str
    codigo: str
    nombre: str
    consumo: Decimal


@dataclass(frozen=True)
class ResultadoTablero:
    productos_por_estado: dict[str, int]
    valor_inventario: Decimal | None
    consumo_30_dias: Decimal
    top_rotacion: list[FilaRotacion]


@dataclass(frozen=True)
class FilaConsumo:
    clave: str
    cantidad: Decimal


@dataclass(frozen=True)
class FilaCobertura:
    producto_id: str
    codigo: str
    nombre: str
    stock_actual: Decimal
    consumo_diario_promedio: Decimal
    dias_cobertura: Decimal | None


def ventana_consumo(hoy: date) -> tuple[date, date]:
    """Los últimos 30 días, incluido hoy."""
    return hoy - timedelta(days=DIAS_VENTANA_CONSUMO - 1), hoy


def _marco_consumo(filas: list[ConsumoDiario]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fecha": [f.fecha.isoformat() for f in filas],
            "producto_id": [str(f.producto_id) for f in filas],
            "codigo": [f.codigo for f in filas],
            "nombre": [f.nombre for f in filas],
            "categoria": [f.categoria for f in filas],
            "cantidad": [str(f.cantidad) for f in filas],
        },
        columns=["fecha", "producto_id", "codigo", "nombre", "categoria", "cantidad"],
    )


def _consumo_por_producto(filas: list[ConsumoDiario]) -> list[tuple[str, str, str, Decimal]]:
    """(producto_id, codigo, nombre, cantidad total) ordenado de mayor a menor consumo."""
    if not filas:
        return []
    with duckdb.connect() as con:
        con.register("consumo", _marco_consumo(filas))
        return con.execute(
            """
            SELECT producto_id, codigo, nombre, sum(CAST(cantidad AS DECIMAL(18, 3))) AS total
            FROM consumo
            GROUP BY producto_id, codigo, nombre
            ORDER BY total DESC, codigo
            """
        ).fetchall()


class ObtenerTablero:
    def __init__(self, consultas: ConsultasAnaliticas) -> None:
        self._consultas = consultas

    def __call__(self, hoy: date) -> ResultadoTablero:
        productos = self._consultas.inventario()
        estados = pd.Series([p.estado for p in productos], dtype="object").value_counts()
        por_producto = _consumo_por_producto(self._consultas.consumo_diario(*ventana_consumo(hoy)))
        return ResultadoTablero(
            productos_por_estado={str(estado): int(total) for estado, total in estados.items()},
            valor_inventario=valor_inventario(productos),
            consumo_30_dias=sum((fila[3] for fila in por_producto), CERO),
            top_rotacion=[
                FilaRotacion(producto_id=pid, codigo=codigo, nombre=nombre, consumo=total)
                for pid, codigo, nombre, total in por_producto[:TOP_ROTACION]
            ],
        )


class ConsultarConsumo:
    def __init__(self, consultas: ConsultasAnaliticas) -> None:
        self._consultas = consultas

    def __call__(self, desde: date, hasta: date, agrupar_por: AgrupacionConsumo) -> list[FilaConsumo]:
        if desde > hasta:
            raise DatosInvalidos(
                "La fecha 'desde' no puede ser posterior a 'hasta'",
                errors=[{"campo": "desde", "mensaje": "Debe ser anterior o igual a 'hasta'"}],
            )
        filas = self._consultas.consumo_diario(desde, hasta)
        if not filas:
            return []
        columna = {
            AgrupacionConsumo.CATEGORIA: "categoria",
            AgrupacionConsumo.PRODUCTO: "codigo",
            AgrupacionConsumo.DIA: "fecha",
        }[agrupar_por]
        with duckdb.connect() as con:
            con.register("consumo", _marco_consumo(filas))
            agregado = con.execute(
                f"""
                SELECT {columna} AS clave, sum(CAST(cantidad AS DECIMAL(18, 3))) AS cantidad
                FROM consumo
                GROUP BY {columna}
                ORDER BY {"clave" if agrupar_por is AgrupacionConsumo.DIA else "cantidad DESC, clave"}
                """  # noqa: S608 - la columna sale de un diccionario fijo, no de la petición
            ).fetchall()
        return [FilaConsumo(clave=str(clave), cantidad=cantidad) for clave, cantidad in agregado]


class CalcularCobertura:
    def __init__(self, consultas: ConsultasAnaliticas) -> None:
        self._consultas = consultas

    def __call__(self, hoy: date) -> list[FilaCobertura]:
        consumo = {
            pid: total
            for pid, _, _, total in _consumo_por_producto(self._consultas.consumo_diario(*ventana_consumo(hoy)))
        }
        resultado = []
        for p in self._consultas.inventario():
            if p.estado == "DESCONTINUADO":
                continue
            promedio = (consumo.get(str(p.producto_id), CERO) / DIAS_VENTANA_CONSUMO).quantize(Decimal("0.001"))
            resultado.append(
                FilaCobertura(
                    producto_id=str(p.producto_id),
                    codigo=p.codigo,
                    nombre=p.nombre,
                    stock_actual=p.stock_actual,
                    consumo_diario_promedio=promedio,
                    dias_cobertura=dias_cobertura(p.stock_actual, promedio),
                )
            )
        # Primero los que se agotan antes; sin consumo (None) al final.
        return sorted(resultado, key=lambda f: (f.dias_cobertura is None, f.dias_cobertura or 0, f.codigo))

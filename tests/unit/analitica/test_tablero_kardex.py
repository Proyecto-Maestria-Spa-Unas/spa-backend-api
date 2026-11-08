"""B14 y X7 · casos de uso de analítica con un puerto en memoria (sin base de datos)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.compartido.errores import DatosInvalidos, RecursoNoExiste
from app.modulos.analitica.application.kardex import ConsultarKardex
from app.modulos.analitica.application.tablero import (
    CalcularCobertura,
    ConsultarConsumo,
    ObtenerTablero,
    ventana_consumo,
)
from app.modulos.analitica.domain.modelo import (
    AgrupacionConsumo,
    ConsumoDiario,
    LineaKardex,
    ProductoInventario,
    ProductoReferencia,
    dias_cobertura,
    valor_inventario,
)

HOY = date(2026, 11, 7)
ACETONA = UUID("0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b")
ESMALTE = UUID("0b8e6f0a-3c4d-4e5f-8a9b-000000000002")
LIMA = UUID("0b8e6f0a-3c4d-4e5f-8a9b-000000000003")
D = Decimal


def _producto(pid: UUID, codigo: str, estado: str, stock: str, costo: str) -> ProductoInventario:
    return ProductoInventario(pid, codigo, f"Producto {codigo}", estado, D(stock), D(costo))


def _consumo(fecha: date, pid: UUID, codigo: str, categoria: str, cantidad: str) -> ConsumoDiario:
    return ConsumoDiario(fecha, pid, codigo, f"Producto {codigo}", categoria, D(cantidad))


def _linea(tipo: str, motivo: str, cantidad: str, costo: str | None, saldo: str, promedio: str) -> LineaKardex:
    total = (D(cantidad) * D(costo)).quantize(D("0.0001")) if costo else None
    return LineaKardex(
        ocurrido_en=datetime(2026, 11, 7, 15, tzinfo=UTC),
        tipo=tipo,
        motivo_codigo=motivo,
        cantidad=D(cantidad),
        costo_unitario=D(costo) if costo else None,
        costo_total=total,
        saldo=D(saldo),
        costo_promedio=D(promedio),
        valor_saldo=(D(saldo) * D(promedio)).quantize(D("0.0001")),
    )


class ConsultasEnMemoria:
    def __init__(
        self,
        productos: list[ProductoInventario] | None = None,
        consumo: list[ConsumoDiario] | None = None,
        lineas: list[LineaKardex] | None = None,
        anterior: LineaKardex | None = None,
    ) -> None:
        self.productos = productos or []
        self.consumo = consumo or []
        self.lineas = lineas or []
        self.anterior = anterior
        self.rango_consumo: tuple[date, date] | None = None

    def alertas(self, estado: str | None) -> list[Any]:
        raise NotImplementedError

    def inventario(self) -> list[ProductoInventario]:
        return self.productos

    def consumo_diario(self, desde: date, hasta: date) -> list[ConsumoDiario]:
        self.rango_consumo = (desde, hasta)
        return [c for c in self.consumo if desde <= c.fecha <= hasta]

    def producto(self, producto_id: UUID) -> ProductoReferencia | None:
        return ProductoReferencia(producto_id, "REM-001", "Acetona pura") if producto_id == ACETONA else None

    def kardex(self, producto_id: UUID, desde: date | None, hasta: date | None) -> list[LineaKardex]:
        return self.lineas

    def ultima_linea_kardex(self, producto_id: UUID, hasta: date | None) -> LineaKardex | None:
        return self.anterior


# ── Dominio ─────────────────────────────────────────────────────────────────
def test_valor_inventario_suma_stock_por_costo() -> None:
    productos = [_producto(ACETONA, "A", "DISPONIBLE", "500", "40.1915"), _producto(LIMA, "L", "AGOTADO", "0", "2")]
    assert valor_inventario(productos) == D("20095.7500")


def test_valor_inventario_es_none_sin_costos() -> None:
    assert valor_inventario([_producto(ACETONA, "A", "DISPONIBLE", "10", "0")]) is None


def test_dias_cobertura() -> None:
    assert dias_cobertura(D("350"), D("5")) == D("70.0")
    assert dias_cobertura(D("350"), D("0")) is None


# ── Tablero ─────────────────────────────────────────────────────────────────
def test_ventana_de_30_dias_incluye_hoy() -> None:
    assert ventana_consumo(HOY) == (date(2026, 10, 9), HOY)


def test_tablero() -> None:
    consultas = ConsultasEnMemoria(
        productos=[
            _producto(ACETONA, "REM-001", "BAJO_STOCK", "350", "38"),
            _producto(ESMALTE, "ESM-001", "DISPONIBLE", "24", "12.5"),
            _producto(LIMA, "HER-001", "DISPONIBLE", "10", "0"),
        ],
        consumo=[
            _consumo(date(2026, 11, 6), ACETONA, "REM-001", "Removedores", "15"),
            _consumo(date(2026, 11, 7), ACETONA, "REM-001", "Removedores", "85"),
            _consumo(date(2026, 11, 7), ESMALTE, "ESM-001", "Esmaltes", "3"),
            _consumo(date(2026, 10, 1), LIMA, "HER-001", "Herramientas", "99"),  # fuera de la ventana
        ],
    )
    r = ObtenerTablero(consultas)(HOY)
    assert r.productos_por_estado == {"DISPONIBLE": 2, "BAJO_STOCK": 1}
    assert r.valor_inventario == D("13600.0000")  # 350 × 38 + 24 × 12,5
    assert r.consumo_30_dias == D("103")
    assert [(f.codigo, f.consumo) for f in r.top_rotacion] == [("REM-001", D("100")), ("ESM-001", D("3"))]
    assert consultas.rango_consumo == (date(2026, 10, 9), HOY)


def test_tablero_vacio() -> None:
    r = ObtenerTablero(ConsultasEnMemoria())(HOY)
    assert r.productos_por_estado == {}
    assert r.valor_inventario is None
    assert r.consumo_30_dias == 0
    assert r.top_rotacion == []


def test_top_rotacion_maximo_10() -> None:
    consumo = [_consumo(HOY, uuid4(), f"P-{i:02d}", "Esmaltes", str(i + 1)) for i in range(12)]
    r = ObtenerTablero(ConsultasEnMemoria(consumo=consumo))(HOY)
    assert len(r.top_rotacion) == 10
    assert r.top_rotacion[0].codigo == "P-11"


# ── Consumo ─────────────────────────────────────────────────────────────────
CONSUMO = [
    _consumo(date(2026, 11, 6), ACETONA, "REM-001", "Removedores", "15.5"),
    _consumo(date(2026, 11, 7), ACETONA, "REM-001", "Removedores", "85"),
    _consumo(date(2026, 11, 7), ESMALTE, "ESM-001", "Esmaltes", "3"),
]


@pytest.mark.parametrize(
    ("agrupar", "esperado"),
    [
        (AgrupacionConsumo.CATEGORIA, [("Removedores", D("100.5")), ("Esmaltes", D("3"))]),
        (AgrupacionConsumo.PRODUCTO, [("REM-001", D("100.5")), ("ESM-001", D("3"))]),
        (AgrupacionConsumo.DIA, [("2026-11-06", D("15.5")), ("2026-11-07", D("88"))]),
    ],
)
def test_consumo_agrupado(agrupar: AgrupacionConsumo, esperado: list[tuple[str, Decimal]]) -> None:
    filas = ConsultarConsumo(ConsultasEnMemoria(consumo=CONSUMO))(date(2026, 11, 1), HOY, agrupar)
    assert [(f.clave, f.cantidad) for f in filas] == esperado


def test_consumo_sin_movimientos() -> None:
    assert ConsultarConsumo(ConsultasEnMemoria())(date(2026, 11, 1), HOY, AgrupacionConsumo.DIA) == []


def test_consumo_rango_invertido_es_422() -> None:
    with pytest.raises(DatosInvalidos):
        ConsultarConsumo(ConsultasEnMemoria())(HOY, date(2026, 11, 1), AgrupacionConsumo.DIA)


# ── Cobertura ───────────────────────────────────────────────────────────────
def test_cobertura() -> None:
    consultas = ConsultasEnMemoria(
        productos=[
            _producto(ACETONA, "REM-001", "BAJO_STOCK", "350", "38"),
            _producto(ESMALTE, "ESM-001", "DISPONIBLE", "24", "12.5"),
            _producto(LIMA, "HER-001", "DESCONTINUADO", "5", "2"),
        ],
        consumo=[_consumo(HOY, ACETONA, "REM-001", "Removedores", "150")],
    )
    filas = CalcularCobertura(consultas)(HOY)
    assert [f.codigo for f in filas] == ["REM-001", "ESM-001"]  # sin descontinuados; sin consumo al final
    assert filas[0].consumo_diario_promedio == D("5.000")
    assert filas[0].dias_cobertura == D("70.0")
    assert filas[1].dias_cobertura is None


# ── Kardex (ejemplo de A3) ──────────────────────────────────────────────────
KARDEX_A3 = [
    _linea("ENTRADA", "SALDO_INICIAL", "350", "38.0000", "350", "38.0000"),
    _linea("ENTRADA", "COMPRA", "150", "42.0000", "500", "39.2000"),
    _linea("SALIDA", "CONSUMO_SERVICIO", "15", "39.2000", "485", "39.2000"),
    _linea("ENTRADA", "COMPRA", "100", "45.0000", "585", "40.1915"),
    _linea("SALIDA", "MERMA", "85", "40.1915", "500", "40.1915"),
]


def test_kardex_cuadra_con_a3() -> None:
    r = ConsultarKardex(ConsultasEnMemoria(lineas=KARDEX_A3))(ACETONA, None, None)
    assert r.producto.codigo == "REM-001"
    assert [linea.valor_saldo for linea in r.lineas] == [
        D("13300.0000"),
        D("19600.0000"),
        D("19012.0000"),
        D("23512.0275"),
        D("20095.7500"),
    ]
    assert r.lineas[2].costo_total == D("588.0000")
    assert (r.saldo_final, r.valor_final) == (D("500"), D("20095.7500"))


def test_kardex_sin_movimientos_en_el_rango_usa_el_ultimo_anterior() -> None:
    r = ConsultarKardex(ConsultasEnMemoria(anterior=KARDEX_A3[1]))(ACETONA, date(2026, 11, 8), None)
    assert r.lineas == []
    assert (r.saldo_final, r.valor_final) == (D("500"), D("19600.0000"))


def test_kardex_de_producto_sin_movimientos() -> None:
    r = ConsultarKardex(ConsultasEnMemoria())(ACETONA, None, None)
    assert (r.saldo_final, r.valor_final) == (D("0"), D("0"))


def test_kardex_producto_inexistente_es_404() -> None:
    with pytest.raises(RecursoNoExiste):
        ConsultarKardex(ConsultasEnMemoria())(uuid4(), None, None)


def test_kardex_rango_invertido_es_422() -> None:
    with pytest.raises(DatosInvalidos):
        ConsultarKardex(ConsultasEnMemoria())(ACETONA, HOY, date(2026, 11, 1))

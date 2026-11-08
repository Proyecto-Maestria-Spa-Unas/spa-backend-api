"""X4 · Consultas de alertas contra inventario.v_alerta_stock (PostgreSQL con el esquema de spa-database)."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modulos.analitica.domain.modelo import EstadoAlerta
from app.modulos.analitica.infrastructure.consultas_sql import ConsultasAnaliticasSQL

pytestmark = pytest.mark.integracion


def _crear_producto(con: Connection, prefijo: str, actual: str, minimo: str | None, descontinuado: bool = False) -> str:
    categoria_id = con.execute(text("SELECT id FROM inventario.categoria ORDER BY id LIMIT 1")).scalar()
    unidad_id = con.execute(text("SELECT id FROM inventario.unidad_medida WHERE codigo = 'UND'")).scalar()
    if categoria_id is None or unidad_id is None:
        pytest.skip("La base no tiene los datos de referencia del catálogo")
    codigo = f"{prefijo}-{uuid4().hex[:10].upper()}"
    con.execute(
        text(
            """
            INSERT INTO inventario.producto
                (codigo, nombre, categoria_id, unidad_medida_id, stock_actual, stock_minimo, descontinuado)
            VALUES (:codigo, :nombre, :categoria, :unidad, :actual, :minimo, :descontinuado)
            """
        ),
        {
            "codigo": codigo,
            "nombre": f"Prueba X4 {codigo}",
            "categoria": categoria_id,
            "unidad": unidad_id,
            "actual": actual,
            "minimo": minimo,
            "descontinuado": descontinuado,
        },
    )
    return codigo


@pytest.fixture
def escenario(transaccion: Connection) -> dict[str, str]:
    return {
        "bajo": _crear_producto(transaccion, "X4B", "3", "5"),
        "justo": _crear_producto(transaccion, "X4J", "5", "5"),  # stock == mínimo también alerta (RN-09)
        "agotado": _crear_producto(transaccion, "X4A", "0", "5"),
        "bien": _crear_producto(transaccion, "X4D", "20", "5"),
        "sin_minimo": _crear_producto(transaccion, "X4N", "0", None),  # RN-14: sin mínimo no hay alerta
        "descontinuado": _crear_producto(transaccion, "X4X", "0", "5", descontinuado=True),
    }


def _codigos(alertas) -> list[str]:
    return [a.codigo for a in alertas]


def test_alertas_incluye_solo_productos_en_alerta(transaccion: Connection, escenario: dict[str, str]) -> None:
    with Session(bind=transaccion) as session:
        codigos = set(_codigos(ConsultasAnaliticasSQL(session).alertas(None)))
    assert {escenario["bajo"], escenario["justo"], escenario["agotado"]} <= codigos
    assert not codigos & {escenario["bien"], escenario["sin_minimo"], escenario["descontinuado"]}


def test_alertas_calcula_estado_y_faltante(transaccion: Connection, escenario: dict[str, str]) -> None:
    with Session(bind=transaccion) as session:
        por_codigo = {a.codigo: a for a in ConsultasAnaliticasSQL(session).alertas(None)}
    assert por_codigo[escenario["bajo"]].estado is EstadoAlerta.BAJO_STOCK
    assert por_codigo[escenario["bajo"]].faltante == Decimal("2")
    assert por_codigo[escenario["justo"]].estado is EstadoAlerta.BAJO_STOCK
    assert por_codigo[escenario["justo"]].faltante == Decimal(0)
    assert por_codigo[escenario["agotado"]].estado is EstadoAlerta.AGOTADO
    assert por_codigo[escenario["agotado"]].faltante == Decimal("5")


def test_alertas_filtra_por_estado(transaccion: Connection, escenario: dict[str, str]) -> None:
    with Session(bind=transaccion) as session:
        consultas = ConsultasAnaliticasSQL(session)
        agotados = consultas.alertas(EstadoAlerta.AGOTADO)
        bajos = consultas.alertas(EstadoAlerta.BAJO_STOCK)
    assert {a.estado for a in agotados} == {EstadoAlerta.AGOTADO}
    assert {a.estado for a in bajos} == {EstadoAlerta.BAJO_STOCK}
    assert escenario["agotado"] in _codigos(agotados)
    assert {escenario["bajo"], escenario["justo"]} <= set(_codigos(bajos))


def test_alertas_ordena_agotados_primero_y_luego_por_faltante(
    transaccion: Connection, escenario: dict[str, str]
) -> None:
    with Session(bind=transaccion) as session:
        alertas = ConsultasAnaliticasSQL(session).alertas(None)
    estados = [a.estado for a in alertas]
    assert estados == sorted(estados, key=lambda e: e is not EstadoAlerta.AGOTADO)
    propios = [a.codigo for a in alertas if a.codigo in {escenario["bajo"], escenario["justo"]}]
    assert propios == [escenario["bajo"], escenario["justo"]]  # faltan 2 y 0


def test_resumen_cuenta_por_estado(transaccion: Connection, escenario: dict[str, str]) -> None:
    with Session(bind=transaccion) as session:
        consultas = ConsultasAnaliticasSQL(session)
        resumen = consultas.resumen_alertas()
        todas = consultas.alertas(None)
    assert resumen.bajo_stock == sum(a.estado is EstadoAlerta.BAJO_STOCK for a in todas)
    assert resumen.agotado == sum(a.estado is EstadoAlerta.AGOTADO for a in todas)
    assert resumen.total == len(todas)
    assert resumen.bajo_stock >= 2
    assert resumen.agotado >= 1

"""#59 · Los RAISE EXCEPTION de los disparadores llegan como problem+json con su code, no como 500."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from app.compartido.errores import DatosInvalidos, StockInsuficiente, error_de_base, registrar_manejadores


class _PsycopgFalsoError(Exception):
    def __init__(self, sqlstate: str, primario: str, detalle: str | None) -> None:
        super().__init__(primario)
        self.sqlstate = sqlstate
        self.diag = SimpleNamespace(message_primary=primario, message_detail=detalle)


def _dbapi(sqlstate: str, primario: str, detalle: str | None = None) -> DBAPIError:
    return DBAPIError("INSERT ...", {}, _PsycopgFalsoError(sqlstate, primario, detalle))


def test_traduce_el_code_del_disparador() -> None:
    error = error_de_base(_dbapi("P0001", "DATOS_INVALIDOS", "La unidad del producto no admite decimales"))
    assert isinstance(error, DatosInvalidos)
    assert error.detail == "La unidad del producto no admite decimales"
    assert isinstance(error_de_base(_dbapi("P0001", "STOCK_INSUFICIENTE")), StockInsuficiente)


@pytest.mark.parametrize(
    ("sqlstate", "primario"),
    [("P0001", "MOVIMIENTO_INMUTABLE"), ("P0001", "otro mensaje"), ("23505", "DATOS_INVALIDOS")],
)
def test_lo_demas_no_se_traduce(sqlstate: str, primario: str) -> None:
    assert error_de_base(_dbapi(sqlstate, primario)) is None


def _app(error: DBAPIError) -> TestClient:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/falla")
    def falla() -> None:
        raise error

    return TestClient(app, raise_server_exceptions=False)


def test_respuesta_problem_json_con_el_status_del_contrato() -> None:
    r = _app(_dbapi("P0001", "DATOS_INVALIDOS", "La unidad del producto no admite decimales")).get("/falla")
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "DATOS_INVALIDOS"
    assert r.json()["detail"] == "La unidad del producto no admite decimales"


def test_error_de_base_desconocido_es_500_sin_detalle_tecnico() -> None:
    r = _app(_dbapi("42P01", 'relation "x" does not exist')).get("/falla")
    assert r.status_code == 500
    assert r.json()["code"] == "ERROR_INTERNO"
    assert "relation" not in r.text

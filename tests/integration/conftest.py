"""Pruebas de integración contra PostgreSQL/PostGIS con el esquema de spa-database.

Local:  docker compose up -d db   y en .env  DB_URL=...@localhost:54322/postgres
Si la base no responde, estas pruebas se omiten (skip) en lugar de fallar.
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

URL_INTEGRACION = os.environ.get(
    "DB_URL_INTEGRACION", "postgresql+psycopg://postgres:postgres@localhost:54322/postgres"
)


@pytest.fixture(scope="session")
def conexion() -> Iterator[Connection]:
    motor = create_engine(URL_INTEGRACION, connect_args={"prepare_threshold": None, "connect_timeout": 3})
    try:
        con = motor.connect()
    except Exception:
        pytest.skip("Base de integración no disponible: ejecute docker compose up -d db")
    try:
        yield con
    finally:
        con.close()
        motor.dispose()


@pytest.fixture
def transaccion(conexion: Connection) -> Iterator[Connection]:
    """Cada prueba corre dentro de una transacción que se revierte al terminar."""
    tx = conexion.begin()
    try:
        yield conexion
    finally:
        tx.rollback()


def esquema_existe(con: Connection, esquema: str) -> bool:
    return bool(con.execute(text("select 1 from pg_namespace where nspname = :e"), {"e": esquema}).scalar())

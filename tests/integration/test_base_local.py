"""Verifica que la base local tiene el esquema de spa-database (ejemplo de prueba de integración)."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection

from tests.integration.conftest import esquema_existe

pytestmark = pytest.mark.integracion


def test_la_base_responde(transaccion: Connection) -> None:
    assert transaccion.execute(text("select 1")).scalar() == 1


def test_esquema_de_inventario_aplicado(transaccion: Connection) -> None:
    if not esquema_existe(transaccion, "inventario"):
        pytest.skip("La base no tiene el esquema de spa-database: docker compose down -v && docker compose up -d db")
    assert esquema_existe(transaccion, "extensions")

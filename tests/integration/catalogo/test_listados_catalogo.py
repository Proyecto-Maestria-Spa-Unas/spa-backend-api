"""Pruebas de integración para categorías y unidades del catálogo."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.compartido.config import get_settings
from app.compartido.db import get_session
from app.main import app

pytestmark = pytest.mark.integracion


def test_listar_categorias_y_unidades_contrato_y_datos_reales(
    cliente: TestClient,
    cabeceras,
    transaccion: Connection,
) -> None:
    """Los GET responden según sus esquemas y reflejan los datos de PostgreSQL."""
    categorias_esperadas = [
        dict(fila)
        for fila in transaccion.execute(
            text(
                """
                SELECT id, nombre, descripcion, orden, activa
                FROM inventario.categoria
                WHERE activa
                ORDER BY orden, nombre
                """
            )
        ).mappings()
    ]
    unidades_esperadas = [
        dict(fila)
        for fila in transaccion.execute(
            text(
                """
                SELECT id, codigo, nombre, magnitud, admite_decimales
                FROM inventario.unidad_medida
                ORDER BY nombre
                """
            )
        ).mappings()
    ]

    if not categorias_esperadas or not unidades_esperadas:
        pytest.skip("La base no tiene datos de referencia para categorías y unidades")

    def sesion_integracion() -> Iterator[Session]:
        with Session(bind=transaccion, expire_on_commit=False) as sesion:
            yield sesion

    overrides_originales = app.dependency_overrides.copy()
    app.dependency_overrides[get_session] = sesion_integracion
    try:
        headers = cabeceras("producto.consultar")
        prefijo = get_settings().api_prefix
        respuesta_categorias = cliente.get(f"{prefijo}/categorias", headers=headers)
        respuesta_unidades = cliente.get(f"{prefijo}/unidades-medida", headers=headers)
    finally:
        app.dependency_overrides = overrides_originales

    assert respuesta_categorias.status_code == 200, respuesta_categorias.text
    assert respuesta_unidades.status_code == 200, respuesta_unidades.text

    categorias = respuesta_categorias.json()
    unidades = respuesta_unidades.json()

    assert categorias == categorias_esperadas
    assert unidades == unidades_esperadas
    assert all(
        set(categoria) == {"id", "nombre", "descripcion", "orden", "activa"} for categoria in categorias
    )
    assert all(
        set(unidad) == {"id", "codigo", "nombre", "magnitud", "admite_decimales"} for unidad in unidades
    )

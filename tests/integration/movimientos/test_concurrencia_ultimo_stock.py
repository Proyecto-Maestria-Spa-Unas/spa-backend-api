"""Prueba concurrente de B10: solo una salida consume la última unidad."""

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.compartido.db import get_session
from app.compartido.seguridad import emitir_token
from app.main import app

pytestmark = pytest.mark.integracion

URL_INTEGRACION = os.environ.get(
    "DB_URL_INTEGRACION", "postgresql+psycopg://postgres:postgres@localhost:54322/postgres"
)
PERMISO_SALIDA = "movimiento.registrar_salida"


def test_diez_pares_de_salidas_concurrentes_protegen_el_ultimo_stock(
    conexion: Connection,
    cliente: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    motor = create_engine(URL_INTEGRACION, connect_args={"prepare_threshold": None, "connect_timeout": 3})
    categoria_id = conexion.execute(text("SELECT id FROM inventario.categoria ORDER BY id LIMIT 1")).scalar()
    unidad_id = conexion.execute(text("SELECT id FROM inventario.unidad_medida WHERE codigo = 'UND'")).scalar()

    if categoria_id is None or unidad_id is None:
        motor.dispose()
        pytest.skip("La base no tiene los datos de referencia de categorías y unidades")

    usuario_id = uuid4()
    producto_ids = [uuid4() for _ in range(10)]
    try:
        with motor.begin() as setup:
            setup.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
                {"id": usuario_id, "email": f"b10-{usuario_id.hex}@example.test"},
            )
            for indice, producto_id in enumerate(producto_ids):
                setup.execute(
                    text(
                        """
                        INSERT INTO inventario.producto (
                            id, codigo, nombre, categoria_id, unidad_medida_id, stock_actual
                        ) VALUES (
                            :id, :codigo, :nombre, :categoria_id, :unidad_id, 1
                        )
                        """
                    ),
                    {
                        "id": producto_id,
                        "codigo": f"B10-CONC-{usuario_id.hex[:8]}-{indice}",
                        "nombre": f"Prueba concurrencia B10 {indice}",
                        "categoria_id": categoria_id,
                        "unidad_id": unidad_id,
                    },
                )

        def sesion_por_peticion() -> Iterator[Session]:
            with Session(motor, expire_on_commit=False) as session:
                yield session

        monkeypatch.setitem(app.dependency_overrides, get_session, sesion_por_peticion)
        token, _ = emitir_token(usuario_id, "ADMINISTRADOR", [PERMISO_SALIDA])
        headers_base = {"Authorization": f"Bearer {token}"}

        def pedir_salida(producto_id: UUID, barrera: Barrier) -> int:
            barrera.wait(timeout=10)
            respuesta = cliente.post(
                "/api/v1/movimientos/salidas",
                json={"producto_id": str(producto_id), "cantidad": "1", "motivo_codigo": "CONSUMO_SERVICIO"},
                headers={
                    **headers_base,
                    "Idempotency-Key": str(uuid4()),
                },
            )
            return respuesta.status_code

        trabajos = []
        with ThreadPoolExecutor(max_workers=20) as ejecutor:
            for producto_id in producto_ids:
                barrera = Barrier(2)
                trabajos.extend(ejecutor.submit(pedir_salida, producto_id, barrera) for _ in range(2))
            estados = [trabajo.result(timeout=30) for trabajo in trabajos]

        for indice in range(10):
            par = estados[indice * 2 : indice * 2 + 2]
            assert sorted(par) == [201, 409]

        with motor.connect() as verificacion:
            stocks = (
                verificacion.execute(
                    text("SELECT stock_actual FROM inventario.producto WHERE id = ANY(:ids) ORDER BY codigo"),
                    {"ids": producto_ids},
                )
                .scalars()
                .all()
            )
        assert len(stocks) == 10
        assert all(stock == 0 for stock in stocks)
    finally:
        with motor.begin() as limpieza:
            limpieza.execute(
                text("DELETE FROM inventario.movimiento WHERE producto_id = ANY(:ids)"), {"ids": producto_ids}
            )
            limpieza.execute(text("DELETE FROM inventario.producto WHERE id = ANY(:ids)"), {"ids": producto_ids})
            limpieza.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": usuario_id})
        motor.dispose()

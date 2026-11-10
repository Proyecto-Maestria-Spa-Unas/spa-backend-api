"""Pruebas de integración para el repositorio SQL de proveedores (X2)."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.compartido.errores import ProveedorDuplicado, RecursoNoExiste
from app.modulos.catalogo.infrastructure.proveedores_sql import ProveedoresSQL

pytestmark = pytest.mark.integracion


def _crear(
    con: Connection,
    nit: str,
    nombre: str,
    latitud: float | None = None,
    longitud: float | None = None,
) -> None:
    con.execute(
        text(
            """
            INSERT INTO inventario.proveedor (
                nit, nombre, ubicacion
            )
            VALUES (
                :nit, :nombre,
                CASE
                    WHEN CAST(:latitud AS double precision) IS NULL
                        OR CAST(:longitud AS double precision) IS NULL THEN NULL
                    ELSE ST_SetSRID(
                        ST_MakePoint(:longitud, :latitud), 4326
                    )::geography
                END
            )
            """
        ),
        {
            "nit": nit,
            "nombre": nombre,
            "latitud": latitud,
            "longitud": longitud,
        },
    )


def test_listar_devuelve_proveedores_y_sus_coordenadas(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"
    _crear(transaccion, nit, "Proveedor X2 Bogotá", 4.6533, -74.0836)

    with Session(bind=transaccion) as session:
        proveedores = ProveedoresSQL(session).listar()

    proveedor = next(p for p in proveedores if p.nit == nit)

    assert proveedor.nombre == "Proveedor X2 Bogotá"
    assert proveedor.latitud == pytest.approx(4.6533)
    assert proveedor.longitud == pytest.approx(-74.0836)
    assert proveedor.activo is True


def test_listar_incluye_inactivos_solo_cuando_se_solicita(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"
    proveedor_id = transaccion.execute(
        text(
            """
            INSERT INTO inventario.proveedor (nit, nombre, activo)
            VALUES (:nit, 'Proveedor inactivo X2', false)
            RETURNING id
            """
        ),
        {"nit": nit},
    ).scalar_one()

    with Session(bind=transaccion) as session:
        repositorio = ProveedoresSQL(session)

        activos = repositorio.listar()
        todos = repositorio.listar(incluir_inactivos=True)

    assert all(proveedor.id != proveedor_id for proveedor in activos)
    assert any(proveedor.id == proveedor_id for proveedor in todos)


def test_crear_proveedor_guarda_su_ubicacion(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"

    with Session(bind=transaccion) as session:
        proveedor = ProveedoresSQL(session).crear(
            {
                "nit": nit,
                "nombre": "Proveedor creado X2",
                "telefono": "3001234567",
                "correo": "proveedor@example.com",
                "direccion": "Bogotá",
                "ubicacion": {
                    "latitud": 4.6533,
                    "longitud": -74.0836,
                },
            }
        )

    assert proveedor.nit == nit
    assert proveedor.nombre == "Proveedor creado X2"
    assert proveedor.latitud == pytest.approx(4.6533)
    assert proveedor.longitud == pytest.approx(-74.0836)
    assert proveedor.activo is True


def test_crear_proveedor_con_nit_duplicado_lanza_error(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"
    _crear(transaccion, nit, "Proveedor original X2")

    with Session(
        bind=transaccion,
        join_transaction_mode="create_savepoint",
    ) as session:
        repositorio = ProveedoresSQL(session)

        with pytest.raises(ProveedorDuplicado) as capturado:
            repositorio.crear(
                {
                    "nit": nit,
                    "nombre": "Proveedor duplicado X2",
                }
            )

    assert capturado.value.status == 409


def test_actualizar_proveedor_modifica_datos_y_ubicacion(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"
    _crear(transaccion, nit, "Proveedor original X2", 4.6533, -74.0836)

    with Session(bind=transaccion) as session:
        repositorio = ProveedoresSQL(session)
        proveedor = repositorio.obtener(
            session.execute(
                text("SELECT id FROM inventario.proveedor WHERE nit = :nit"),
                {"nit": nit},
            ).scalar_one()
        )

        actualizado = repositorio.actualizar(
            proveedor.id,
            {
                "nombre": "Proveedor actualizado X2",
                "ubicacion": {
                    "latitud": 4.7110,
                    "longitud": -74.0721,
                },
            },
        )

    assert actualizado.nombre == "Proveedor actualizado X2"
    assert actualizado.latitud == pytest.approx(4.7110)
    assert actualizado.longitud == pytest.approx(-74.0721)


def test_actualizar_proveedor_permite_eliminar_ubicacion(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"
    _crear(transaccion, nit, "Proveedor sin ubicación X2", 4.6533, -74.0836)

    with Session(bind=transaccion) as session:
        repositorio = ProveedoresSQL(session)
        proveedor = next(p for p in repositorio.listar() if p.nit == nit)

        actualizado = repositorio.actualizar(
            proveedor.id,
            {"ubicacion": None},
        )

    assert actualizado.latitud is None
    assert actualizado.longitud is None


def test_actualizar_proveedor_permite_desactivarlo(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"
    _crear(transaccion, nit, "Proveedor para desactivar X2")

    with Session(bind=transaccion) as session:
        repositorio = ProveedoresSQL(session)
        proveedores = repositorio.listar()
        proveedor = next(p for p in proveedores if p.nit == nit)

        actualizado = repositorio.actualizar(
            proveedor.id,
            {"activo": False},
        )

    assert actualizado.activo is False


def test_obtener_proveedor_inexistente_lanza_error(
    transaccion: Connection,
) -> None:
    with Session(bind=transaccion) as session:
        repositorio = ProveedoresSQL(session)

        with pytest.raises(RecursoNoExiste) as capturado:
            repositorio.obtener(uuid4())

    assert capturado.value.status == 404


def test_actualizar_proveedor_sin_cambios_devuelve_el_actual(
    transaccion: Connection,
) -> None:
    nit = f"X2-{uuid4().hex[:10]}"
    _crear(transaccion, nit, "Proveedor sin cambios X2")

    with Session(bind=transaccion) as session:
        repositorio = ProveedoresSQL(session)
        proveedor = next(p for p in repositorio.listar() if p.nit == nit)

        actualizado = repositorio.actualizar(proveedor.id, {})

    assert actualizado.id == proveedor.id
    assert actualizado.nombre == "Proveedor sin cambios X2"


def test_actualizar_proveedor_inexistente_lanza_error(
    transaccion: Connection,
) -> None:
    with Session(bind=transaccion) as session:
        repositorio = ProveedoresSQL(session)

        with pytest.raises(RecursoNoExiste) as capturado:
            repositorio.actualizar(uuid4(), {"nombre": "Proveedor inexistente"})

    assert capturado.value.status == 404

"""Pruebas de los endpoints de proveedores."""

from collections.abc import Iterator
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from app.modulos.catalogo.api.router import obtener_proveedores_repository
from app.modulos.catalogo.domain.modelo import Proveedor
from tests.conftest import FabricaToken

RUTA = f"{get_settings().api_prefix}/proveedores"

PROVEEDOR_ID = UUID("3c1f0000-0000-4000-8000-000000000001")
OTRO_PROVEEDOR_ID = UUID("3c1f0000-0000-4000-8000-000000000002")


def _proveedor(
    proveedor_id: UUID = PROVEEDOR_ID,
    nit: str = "900123456-7",
    nombre: str = "Distribuidora Belleza Total",
    activo: bool = True,
) -> Proveedor:
    return Proveedor(
        id=proveedor_id,
        nit=nit,
        nombre=nombre,
        telefono="6015550101",
        correo="ventas@bellezatotal.co",
        direccion="Cl. 63 #13-20, Bogotá",
        latitud=4.6533,
        longitud=-74.0836,
        activo=activo,
    )


class ProveedoresEnMemoria:
    def __init__(self, proveedores: list[Proveedor] | None = None) -> None:
        self._proveedores = proveedores or []

    def listar(self, incluir_inactivos: bool = False) -> list[Proveedor]:
        if incluir_inactivos:
            return self._proveedores

        return [proveedor for proveedor in self._proveedores if proveedor.activo]

    def crear(self, datos: dict[str, object]) -> Proveedor:
        from app.compartido.errores import ProveedorDuplicado

        nit = str(datos["nit"])

        if any(proveedor.nit == nit for proveedor in self._proveedores):
            raise ProveedorDuplicado()

        proveedor = Proveedor(
            id=UUID(int=len(self._proveedores) + 1),
            nit=nit,
            nombre=str(datos["nombre"]),
            telefono=cast(str | None, datos.get("telefono")),
            correo=cast(str | None, datos.get("correo")),
            direccion=cast(str | None, datos.get("direccion")),
            latitud=None,
            longitud=None,
            activo=True,
        )
        self._proveedores.append(proveedor)
        return proveedor

    def actualizar(self, proveedor_id: UUID, cambios: dict[str, object]) -> Proveedor:
        for indice, proveedor in enumerate(self._proveedores):
            if proveedor.id == proveedor_id:
                ubicacion = cambios.get("ubicacion")

                latitud = proveedor.latitud
                longitud = proveedor.longitud

                if isinstance(ubicacion, dict):
                    latitud = ubicacion.get("latitud")
                    longitud = ubicacion.get("longitud")
                elif "ubicacion" in cambios:
                    latitud = None
                    longitud = None

                actualizado = Proveedor(
                    id=proveedor.id,
                    nit=proveedor.nit,
                    nombre=cast(str, cambios.get("nombre", proveedor.nombre)),
                    telefono=cast(str | None, cambios.get("telefono", proveedor.telefono)),
                    correo=cast(str | None, cambios.get("correo", proveedor.correo)),
                    direccion=cast(str | None, cambios.get("direccion", proveedor.direccion)),
                    latitud=latitud,
                    longitud=longitud,
                    activo=cast(bool, cambios.get("activo", proveedor.activo)),
                )

                self._proveedores[indice] = actualizado
                return actualizado

        from app.compartido.errores import RecursoNoExiste

        raise RecursoNoExiste("Proveedor no encontrado")


@pytest.fixture
def repositorio_proveedores() -> Iterator[ProveedoresEnMemoria]:
    falso = ProveedoresEnMemoria()
    app.dependency_overrides[obtener_proveedores_repository] = lambda: falso

    yield falso

    app.dependency_overrides.pop(obtener_proveedores_repository, None)


def test_listar_proveedores(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    repositorio_proveedores._proveedores.extend(
        [
            _proveedor(),
            _proveedor(
                proveedor_id=OTRO_PROVEEDOR_ID,
                nit="900123457-8",
                nombre="Suministros para Uñas",
            ),
        ]
    )

    respuesta = cliente.get(
        RUTA,
        headers=cabeceras("producto.consultar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()) == 2
    assert respuesta.json()[0]["nit"] == "900123456-7"
    assert respuesta.json()[0]["ubicacion"] == {
        "latitud": 4.6533,
        "longitud": -74.0836,
    }


def test_listar_proveedores_excluye_inactivos_por_defecto(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    repositorio_proveedores._proveedores.extend(
        [
            _proveedor(),
            _proveedor(
                proveedor_id=OTRO_PROVEEDOR_ID,
                nit="900123457-8",
                nombre="Proveedor inactivo",
                activo=False,
            ),
        ]
    )

    respuesta = cliente.get(
        RUTA,
        headers=cabeceras("producto.consultar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["activo"] is True


def test_crear_proveedor(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    datos = {
        "nombre": "Nueva Distribuidora",
        "nit": "900765432-1",
        "telefono": "6015550101",
        "correo": "ventas@nueva.co",
        "direccion": "Carrera 15 #80-20, Bogotá",
    }

    respuesta = cliente.post(
        RUTA,
        json=datos,
        headers=cabeceras("catalogo.administrar"),
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["nombre"] == datos["nombre"]
    assert respuesta.json()["nit"] == datos["nit"]
    assert respuesta.json()["activo"] is True
    assert len(repositorio_proveedores._proveedores) == 1


def test_crear_proveedor_rechaza_nit_duplicado(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    repositorio_proveedores._proveedores.append(_proveedor())

    respuesta = cliente.post(
        RUTA,
        json={
            "nombre": "Otra Distribuidora",
            "nit": "900123456-7",
        },
        headers=cabeceras("catalogo.administrar"),
    )

    assert respuesta.status_code == 409, respuesta.text
    assert len(repositorio_proveedores._proveedores) == 1


def test_actualizar_proveedor(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    repositorio_proveedores._proveedores.append(_proveedor())

    respuesta = cliente.patch(
        f"{RUTA}/{PROVEEDOR_ID}",
        json={"nombre": "Distribuidora Actualizada"},
        headers=cabeceras("catalogo.administrar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["nombre"] == "Distribuidora Actualizada"
    assert respuesta.json()["nit"] == "900123456-7"


def test_actualizar_ubicacion_proveedor(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    repositorio_proveedores._proveedores.append(_proveedor())

    respuesta = cliente.patch(
        f"{RUTA}/{PROVEEDOR_ID}",
        json={
            "ubicacion": {
                "latitud": 4.6097,
                "longitud": -74.0817,
            }
        },
        headers=cabeceras("catalogo.administrar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["ubicacion"] == {
        "latitud": 4.6097,
        "longitud": -74.0817,
    }


def test_listar_proveedores_incluye_inactivos_cuando_se_solicita(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    repositorio_proveedores._proveedores.extend(
        [
            _proveedor(),
            _proveedor(
                proveedor_id=OTRO_PROVEEDOR_ID,
                nit="900123457-8",
                nombre="Proveedor inactivo",
                activo=False,
            ),
        ]
    )

    respuesta = cliente.get(
        RUTA,
        params={"incluir_inactivos": True},
        headers=cabeceras("producto.consultar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()) == 2
    assert respuesta.json()[1]["activo"] is False


def test_listar_proveedores_exige_token_y_permiso(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    sin_token = cliente.get(RUTA)

    assert sin_token.status_code == 401
    assert sin_token.json()["code"] == "NO_AUTENTICADO"

    sin_permiso = cliente.get(
        RUTA,
        headers=cabeceras("alerta.consultar"),
    )

    assert sin_permiso.status_code == 403
    assert sin_permiso.json()["code"] == "SIN_PERMISO"


def test_crear_y_actualizar_proveedores_exigen_permiso(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    datos = {
        "nombre": "Nueva Distribuidora",
        "nit": "900765432-1",
    }

    sin_permiso_post = cliente.post(
        RUTA,
        json=datos,
        headers=cabeceras("producto.consultar"),
    )

    assert sin_permiso_post.status_code == 403
    assert sin_permiso_post.json()["code"] == "SIN_PERMISO"

    repositorio_proveedores._proveedores.append(_proveedor())

    sin_permiso_patch = cliente.patch(
        f"{RUTA}/{PROVEEDOR_ID}",
        json={"nombre": "Nombre no autorizado"},
        headers=cabeceras("producto.consultar"),
    )

    assert sin_permiso_patch.status_code == 403
    assert sin_permiso_patch.json()["code"] == "SIN_PERMISO"
    assert repositorio_proveedores._proveedores[0].nombre == "Distribuidora Belleza Total"


def test_crear_proveedor_rechaza_datos_invalidos(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    respuesta = cliente.post(
        RUTA,
        json={
            "nombre": "Distribuidora Inválida",
            "nit": "NIT-INCORRECTO",
        },
        headers=cabeceras("catalogo.administrar"),
    )

    assert respuesta.status_code == 422
    assert repositorio_proveedores._proveedores == []


def test_actualizar_proveedor_inexistente(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    respuesta = cliente.patch(
        f"{RUTA}/{OTRO_PROVEEDOR_ID}",
        json={"nombre": "Proveedor inexistente"},
        headers=cabeceras("catalogo.administrar"),
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "RECURSO_NO_EXISTE"


def test_actualizar_proveedor_elimina_ubicacion(
    cliente: TestClient,
    cabeceras: FabricaToken,
    repositorio_proveedores: ProveedoresEnMemoria,
) -> None:
    repositorio_proveedores._proveedores.append(_proveedor())

    respuesta = cliente.patch(
        f"{RUTA}/{PROVEEDOR_ID}",
        json={"ubicacion": None},
        headers=cabeceras("catalogo.administrar"),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["ubicacion"] is None

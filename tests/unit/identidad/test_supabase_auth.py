"""Adaptador de Supabase Auth con un transporte simulado de httpx: no sale a la red."""

import json
from collections.abc import Callable
from uuid import uuid4

import httpx
import pytest

from app.modulos.identidad.infrastructure.supabase_auth import (
    ProveedorIdentidadNoDisponible,
    ProveedorSupabaseAuth,
)

URL = "https://proyecto.supabase.co"
CLAVE = "sb_secret_prueba"


def _proveedor(responder: Callable[[httpx.Request], httpx.Response]) -> ProveedorSupabaseAuth:
    return ProveedorSupabaseAuth(URL, CLAVE, httpx.Client(transport=httpx.MockTransport(responder)))


def test_envia_la_peticion_esperada_y_devuelve_el_id() -> None:
    usuario_id = uuid4()
    vistas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={"access_token": "x", "user": {"id": str(usuario_id)}})

    assert _proveedor(responder).verificar_credenciales("a@spa.co", "Clave-2026") == usuario_id
    peticion = vistas[0]
    assert peticion.method == "POST"
    assert peticion.url.path == "/auth/v1/token"
    assert peticion.url.params["grant_type"] == "password"
    assert peticion.headers["apikey"] == CLAVE
    assert "authorization" not in peticion.headers
    assert json.loads(peticion.content) == {"email": "a@spa.co", "password": "Clave-2026"}


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"code": 400, "error_code": "invalid_credentials", "msg": "Invalid login credentials"},
        {"code": "invalid_credentials", "message": "Invalid login credentials"},
    ],
)
def test_credenciales_invalidas_devuelven_none(cuerpo: dict[str, object]) -> None:
    assert _proveedor(lambda _: httpx.Response(400, json=cuerpo)).verificar_credenciales("a@spa.co", "x") is None


@pytest.mark.parametrize(
    ("estado", "cuerpo"),
    [
        (400, {"error_code": "email_not_confirmed", "msg": "Email not confirmed"}),
        (400, {"error_code": "user_banned", "msg": "User is banned"}),
        (401, {"message": "Invalid API key"}),
        (500, {"msg": "Database error"}),
    ],
)
def test_otras_respuestas_no_se_confunden_con_clave_incorrecta(estado: int, cuerpo: dict[str, object]) -> None:
    with pytest.raises(ProveedorIdentidadNoDisponible):
        _proveedor(lambda _: httpx.Response(estado, json=cuerpo)).verificar_credenciales("a@spa.co", "x")


def test_cuerpo_que_no_es_json_es_proveedor_no_disponible() -> None:
    with pytest.raises(ProveedorIdentidadNoDisponible):
        _proveedor(lambda _: httpx.Response(400, text="<html>")).verificar_credenciales("a@spa.co", "x")


def test_error_de_red_es_proveedor_no_disponible() -> None:
    def falla(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=peticion)

    with pytest.raises(ProveedorIdentidadNoDisponible):
        _proveedor(falla).verificar_credenciales("a@spa.co", "x")


def test_exige_url_y_clave() -> None:
    with pytest.raises(ValueError, match="SUPABASE"):
        ProveedorSupabaseAuth("", CLAVE)
    with pytest.raises(ValueError, match="SUPABASE"):
        ProveedorSupabaseAuth(URL, "")


# ---------- B6 · alta de cuentas (POST /auth/v1/admin/users)


def test_crear_cuenta_envia_la_peticion_esperada_y_devuelve_el_id() -> None:
    usuario_id = uuid4()
    vistas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={"id": str(usuario_id), "email": "nueva@spa.co"})

    assert _proveedor(responder).crear_cuenta("nueva@spa.co", "Temporal-2026") == usuario_id
    peticion = vistas[0]
    assert (peticion.method, peticion.url.path) == ("POST", "/auth/v1/admin/users")
    assert peticion.headers["apikey"] == CLAVE
    assert "authorization" not in peticion.headers
    assert json.loads(peticion.content) == {"email": "nueva@spa.co", "password": "Temporal-2026", "email_confirm": True}


@pytest.mark.parametrize("campo", ["error_code", "code"])
def test_crear_cuenta_con_correo_existente_es_codigo_duplicado(campo: str) -> None:
    from app.compartido.errores import CodigoDuplicado

    proveedor = _proveedor(lambda _: httpx.Response(422, json={campo: "email_exists", "msg": "ya registrado"}))
    with pytest.raises(CodigoDuplicado):
        proveedor.crear_cuenta("nueva@spa.co", "Temporal-2026")


def test_crear_cuenta_con_clave_debil_es_datos_invalidos() -> None:
    from app.compartido.errores import DatosInvalidos

    proveedor = _proveedor(lambda _: httpx.Response(422, json={"error_code": "weak_password"}))
    with pytest.raises(DatosInvalidos):
        proveedor.crear_cuenta("nueva@spa.co", "Temporal-2026")


@pytest.mark.parametrize("estado", [401, 403, 500])
def test_crear_cuenta_con_respuesta_inesperada_no_expone_detalle(estado: int) -> None:
    proveedor = _proveedor(lambda _: httpx.Response(estado, json={"msg": "detalle interno"}))
    with pytest.raises(ProveedorIdentidadNoDisponible):
        proveedor.crear_cuenta("nueva@spa.co", "Temporal-2026")


def test_crear_cuenta_sin_conexion_es_proveedor_no_disponible() -> None:
    def responder(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    with pytest.raises(ProveedorIdentidadNoDisponible):
        _proveedor(responder).crear_cuenta("nueva@spa.co", "Temporal-2026")

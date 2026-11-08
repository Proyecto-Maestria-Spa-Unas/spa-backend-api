"""X3 · POST /auth/recuperar: adaptador de Supabase Auth (transporte simulado) y endpoint (doble del puerto)."""

import json
import logging
from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from app.modulos.identidad.api.router import obtener_recuperacion
from app.modulos.identidad.application.recuperacion import MENSAJE_RECUPERACION, SolicitarRecuperacion
from app.modulos.identidad.infrastructure.supabase_auth import ProveedorSupabaseAuth, registro

URL = "https://proyecto.supabase.co"
CLAVE = "sb_secret_prueba"
RECUPERAR = f"{get_settings().api_prefix}/auth/recuperar"
CORREO = "manicurista@spa.co"


def _proveedor(
    responder: Callable[[httpx.Request], httpx.Response], redirigir_a: str | None = None
) -> ProveedorSupabaseAuth:
    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    return ProveedorSupabaseAuth(URL, CLAVE, cliente, redirigir_a=redirigir_a)


# ---------- Adaptador ----------


@pytest.fixture(autouse=True)
def _registro_activo(monkeypatch: pytest.MonkeyPatch) -> None:
    """import-linter (tests/test_arquitectura.py) configura logging y apaga los registros ya creados."""
    monkeypatch.setattr(registro, "disabled", False)


def test_envia_la_peticion_esperada_a_supabase() -> None:
    vistas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={})

    _proveedor(responder, "http://localhost:5173/recuperar").solicitar_recuperacion(CORREO)

    peticion = vistas[0]
    assert peticion.method == "POST"
    assert peticion.url.path == "/auth/v1/recover"
    assert peticion.url.params["redirect_to"] == "http://localhost:5173/recuperar"
    assert peticion.headers["apikey"] == CLAVE
    assert "authorization" not in peticion.headers
    assert json.loads(peticion.content) == {"email": CORREO}


def test_sin_direccion_del_frontend_no_envia_redirect_to() -> None:
    vistas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion)
        return httpx.Response(200, json={})

    _proveedor(responder).solicitar_recuperacion(CORREO)
    assert "redirect_to" not in vistas[0].url.params


def test_la_direccion_del_frontend_sale_de_la_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", CLAVE)
    monkeypatch.setenv("FRONTEND_URL", "https://nailspa.example.com/")
    get_settings.cache_clear()
    try:
        proveedor = ProveedorSupabaseAuth.desde_configuracion()
    finally:
        get_settings.cache_clear()
    assert proveedor._redirigir_a == "https://nailspa.example.com/recuperar"


@pytest.mark.parametrize(
    ("estado", "cuerpo"),
    [
        (429, {"code": 429, "error_code": "over_email_send_rate_limit", "msg": "email rate limit exceeded"}),
        (400, {"error_code": "validation_failed", "msg": "Unable to validate email address"}),
        (500, {"msg": "Error sending recovery email"}),
        (401, {"message": "Invalid API key"}),
    ],
)
def test_los_errores_de_supabase_no_se_propagan_ni_filtran_el_correo(
    estado: int, cuerpo: dict[str, object], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        _proveedor(lambda _: httpx.Response(estado, json=cuerpo)).solicitar_recuperacion(CORREO)
    assert f"HTTP {estado}" in caplog.text
    assert CORREO not in caplog.text


def test_una_caida_de_red_no_se_propaga(caplog: pytest.LogCaptureFixture) -> None:
    def responder(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("sin respuesta")

    with caplog.at_level(logging.WARNING):
        _proveedor(responder).solicitar_recuperacion(CORREO)
    assert "no se pudo contactar" in caplog.text
    assert CORREO not in caplog.text


# ---------- Caso de uso ----------


class RecuperacionFalsa:
    def __init__(self) -> None:
        self.correos: list[str] = []

    def solicitar_recuperacion(self, correo: str) -> None:
        self.correos.append(correo)


def test_el_caso_de_uso_pide_el_correo_y_siempre_devuelve_el_mismo_mensaje() -> None:
    falsa = RecuperacionFalsa()
    caso = SolicitarRecuperacion(falsa)
    assert caso.ejecutar(f"  {CORREO} ") == MENSAJE_RECUPERACION
    assert caso.ejecutar("otra@spa.co") == MENSAJE_RECUPERACION
    assert falsa.correos == [CORREO, "otra@spa.co"]


# ---------- Endpoint ----------


@pytest.fixture
def recuperacion() -> Iterator[RecuperacionFalsa]:
    falsa = RecuperacionFalsa()
    app.dependency_overrides[obtener_recuperacion] = lambda: falsa
    yield falsa
    app.dependency_overrides.clear()


def test_responde_202_con_el_mensaje_y_sin_token(cliente: TestClient, recuperacion: RecuperacionFalsa) -> None:
    r = cliente.post(RECUPERAR, json={"correo": CORREO})
    assert r.status_code == 202, r.text
    assert r.json() == {"mensaje": MENSAJE_RECUPERACION}
    assert recuperacion.correos == [CORREO]


def test_la_respuesta_es_identica_exista_o_no_la_cuenta(cliente: TestClient, recuperacion: RecuperacionFalsa) -> None:
    existente = cliente.post(RECUPERAR, json={"correo": CORREO})
    inexistente = cliente.post(RECUPERAR, json={"correo": "nadie@spa.co"})
    assert (existente.status_code, existente.json()) == (inexistente.status_code, inexistente.json())
    assert len(recuperacion.correos) == 2


def test_responde_202_aunque_supabase_falle(cliente: TestClient) -> None:
    """El adaptador real con Supabase caído: la API sigue respondiendo 202."""

    def caido(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error_code": "over_email_send_rate_limit"})

    app.dependency_overrides[obtener_recuperacion] = lambda: _proveedor(caido)
    try:
        r = cliente.post(RECUPERAR, json={"correo": CORREO})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 202
    assert r.json() == {"mensaje": MENSAJE_RECUPERACION}


@pytest.mark.parametrize("correo", ["", "sin-arroba", "a@b", "con espacio@spa.co"])
def test_un_correo_mal_formado_responde_422(cliente: TestClient, recuperacion: RecuperacionFalsa, correo: str) -> None:
    r = cliente.post(RECUPERAR, json={"correo": correo})
    assert r.status_code == 422
    assert r.json()["code"] == "DATOS_INVALIDOS"
    assert r.json()["errors"][0]["campo"] == "body.correo"
    assert recuperacion.correos == []

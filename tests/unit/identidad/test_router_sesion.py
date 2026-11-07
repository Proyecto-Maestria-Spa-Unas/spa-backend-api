"""B5 · POST /auth/login y GET /auth/me de punta a punta en la API, con dobles de los puertos."""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.compartido.seguridad import decodificar_token, emitir_token
from app.main import app
from app.modulos.identidad.api.router import obtener_proveedor_identidad, obtener_repositorio_usuarios
from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario
from app.modulos.identidad.infrastructure.supabase_auth import ProveedorIdentidadNoDisponible
from tests.unit.identidad.test_sesion import CLAVE, CORREO, ProveedorFalso, RepositorioFalso

LOGIN = f"{get_settings().api_prefix}/auth/login"
ME = f"{get_settings().api_prefix}/auth/me"
PERMISOS = frozenset({"producto.consultar", "movimiento.registrar_salida"})


def _usuario(activo: bool = True) -> Usuario:
    rol = Rol(CodigoRol.MANICURISTA, "Manicurista", PERMISOS)
    return Usuario(uuid4(), CORREO, "Diana Pérez", rol, activo, datetime.now(UTC))


@pytest.fixture
def con_dobles() -> Iterator[callable]:
    def _instalar(usuario: Usuario | None, usuario_id: UUID | None = None) -> None:
        repo = RepositorioFalso(*([usuario] if usuario else []))
        proveedor = ProveedorFalso(usuario_id or (usuario.id if usuario else None))
        app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repo
        app.dependency_overrides[obtener_proveedor_identidad] = lambda: proveedor

    yield _instalar
    app.dependency_overrides.clear()


def test_login_valido_devuelve_token_con_rol_y_permisos(cliente: TestClient, con_dobles) -> None:
    usuario = _usuario()
    con_dobles(usuario)
    r = cliente.post(LOGIN, json={"correo": CORREO, "contrasena": CLAVE})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["expires_in"] == get_settings().jwt_expires_minutes * 60
    assert cuerpo["usuario"] == {
        "id": str(usuario.id),
        "correo": CORREO,
        "nombre_completo": "Diana Pérez",
        "rol": "MANICURISTA",
        "permisos": sorted(PERMISOS),
    }
    principal = decodificar_token(cuerpo["access_token"])
    assert principal.usuario_id == usuario.id
    assert principal.rol == "MANICURISTA"
    assert principal.permisos == PERMISOS


def test_contrasena_incorrecta_responde_401_credenciales_invalidas(cliente: TestClient, con_dobles) -> None:
    con_dobles(_usuario())
    r = cliente.post(LOGIN, json={"correo": CORREO, "contrasena": "Otra-Clave-2026"})
    assert r.status_code == 401
    assert r.json()["code"] == "CREDENCIALES_INVALIDAS"


def test_cuenta_sin_perfil_responde_401_credenciales_invalidas(cliente: TestClient, con_dobles) -> None:
    con_dobles(None, usuario_id=uuid4())
    r = cliente.post(LOGIN, json={"correo": CORREO, "contrasena": CLAVE})
    assert r.status_code == 401
    assert r.json()["code"] == "CREDENCIALES_INVALIDAS"


def test_cuenta_desactivada_responde_403_usuario_inactivo(cliente: TestClient, con_dobles) -> None:
    con_dobles(_usuario(activo=False))
    r = cliente.post(LOGIN, json={"correo": CORREO, "contrasena": CLAVE})
    assert r.status_code == 403
    assert r.json()["code"] == "USUARIO_INACTIVO"


def test_login_con_datos_invalidos_responde_422(cliente: TestClient, con_dobles) -> None:
    con_dobles(_usuario())
    r = cliente.post(LOGIN, json={"correo": "no-es-correo", "contrasena": "corta"})
    assert r.status_code == 422
    assert r.json()["code"] == "DATOS_INVALIDOS"


def test_proveedor_no_disponible_responde_500_sin_detalle_interno(cliente: TestClient) -> None:
    def _falla():
        raise ProveedorIdentidadNoDisponible("El servicio de autenticación no está configurado")

    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: RepositorioFalso()
    app.dependency_overrides[obtener_proveedor_identidad] = _falla
    try:
        r = cliente.post(LOGIN, json={"correo": CORREO, "contrasena": CLAVE})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 500
    assert "SUPABASE" not in r.text


def test_me_devuelve_perfil_y_permisos_vigentes(cliente: TestClient, con_dobles) -> None:
    usuario = _usuario()
    con_dobles(usuario)
    token, _ = emitir_token(usuario.id, "MANICURISTA", ["permiso.viejo"])
    r = cliente.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["permisos"] == sorted(PERMISOS), "GET /auth/me usa los permisos de la base, no los del token"


def test_me_sin_token_responde_401(cliente: TestClient, con_dobles) -> None:
    con_dobles(_usuario())
    r = cliente.get(ME)
    assert r.status_code == 401
    assert r.json()["code"] == "NO_AUTENTICADO"


def test_me_de_cuenta_desactivada_responde_403(cliente: TestClient, con_dobles) -> None:
    usuario = _usuario(activo=False)
    con_dobles(usuario)
    token, _ = emitir_token(usuario.id, "MANICURISTA", sorted(PERMISOS))
    r = cliente.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.json()["code"] == "USUARIO_INACTIVO"


def test_me_de_cuenta_inexistente_responde_401(cliente: TestClient, con_dobles) -> None:
    con_dobles(None)
    token, _ = emitir_token(uuid4(), "MANICURISTA", [])
    r = cliente.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["code"] == "NO_AUTENTICADO"

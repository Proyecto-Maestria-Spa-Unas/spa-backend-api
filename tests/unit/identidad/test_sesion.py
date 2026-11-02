"""Casos de uso de sesión (B5) con dobles de los puertos: sin base ni Supabase."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.compartido.errores import CredencialesInvalidas, NoAutenticado, UsuarioInactivo
from app.modulos.identidad.application.sesion import ConsultarSesion, IniciarSesion
from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario, puede_iniciar_sesion

CORREO = "admin@spa.co"
CLAVE = "Clave-Segura-2026"


def _usuario(activo: bool = True) -> Usuario:
    rol = Rol(CodigoRol.ADMINISTRADOR, "Administrador", frozenset({"producto.consultar"}))
    return Usuario(uuid4(), CORREO, "Laura Gómez", rol, activo, datetime.now(UTC))


class ProveedorFalso:
    def __init__(self, usuario_id: UUID | None) -> None:
        self.usuario_id = usuario_id

    def verificar_credenciales(self, correo: str, contrasena: str) -> UUID | None:
        return self.usuario_id if (correo, contrasena) == (CORREO, CLAVE) else None

    def crear_cuenta(self, correo: str, contrasena_temporal: str) -> UUID:
        raise NotImplementedError


class RepositorioFalso:
    def __init__(self, *usuarios: Usuario) -> None:
        self._usuarios = {u.id: u for u in usuarios}

    def obtener(self, usuario_id: UUID) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def listar(self, activo: bool | None, rol: CodigoRol | None, offset: int, limite: int) -> tuple[list[Usuario], int]:
        raise NotImplementedError

    def guardar(self, usuario: Usuario) -> Usuario:
        raise NotImplementedError

    def roles(self) -> list[Rol]:
        raise NotImplementedError


def test_puede_iniciar_sesion_depende_de_activo() -> None:
    assert puede_iniciar_sesion(_usuario(activo=True))
    assert not puede_iniciar_sesion(_usuario(activo=False))


def test_login_valido_devuelve_el_usuario() -> None:
    usuario = _usuario()
    caso = IniciarSesion(ProveedorFalso(usuario.id), RepositorioFalso(usuario))
    assert caso.ejecutar(CORREO, CLAVE) is usuario


def test_contrasena_incorrecta_es_credenciales_invalidas() -> None:
    usuario = _usuario()
    caso = IniciarSesion(ProveedorFalso(usuario.id), RepositorioFalso(usuario))
    with pytest.raises(CredencialesInvalidas):
        caso.ejecutar(CORREO, "otra-clave-123")


def test_cuenta_sin_perfil_es_credenciales_invalidas() -> None:
    caso = IniciarSesion(ProveedorFalso(uuid4()), RepositorioFalso())
    with pytest.raises(CredencialesInvalidas):
        caso.ejecutar(CORREO, CLAVE)


def test_usuario_inactivo_con_clave_correcta_es_usuario_inactivo() -> None:
    usuario = _usuario(activo=False)
    caso = IniciarSesion(ProveedorFalso(usuario.id), RepositorioFalso(usuario))
    with pytest.raises(UsuarioInactivo):
        caso.ejecutar(CORREO, CLAVE)


def test_usuario_inactivo_con_clave_incorrecta_no_revela_el_estado() -> None:
    usuario = _usuario(activo=False)
    caso = IniciarSesion(ProveedorFalso(usuario.id), RepositorioFalso(usuario))
    with pytest.raises(CredencialesInvalidas):
        caso.ejecutar(CORREO, "otra-clave-123")


def test_consultar_sesion_activa() -> None:
    usuario = _usuario()
    assert ConsultarSesion(RepositorioFalso(usuario)).ejecutar(usuario.id) is usuario


def test_consultar_sesion_de_cuenta_inexistente_es_no_autenticado() -> None:
    with pytest.raises(NoAutenticado):
        ConsultarSesion(RepositorioFalso()).ejecutar(uuid4())


def test_consultar_sesion_de_cuenta_desactivada_es_usuario_inactivo() -> None:
    usuario = _usuario(activo=False)
    with pytest.raises(UsuarioInactivo):
        ConsultarSesion(RepositorioFalso(usuario)).ejecutar(usuario.id)

"""Casos de uso de gestión de usuarios y roles (B6, HU-09, RF-13). Solo dependen de los puertos."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.compartido.errores import DatosInvalidos, RecursoNoExiste
from app.modulos.identidad.application.puertos import ProveedorIdentidad, UsuarioRepository
from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario


def _rol_activo(usuarios: UsuarioRepository, codigo: CodigoRol) -> Rol:
    for rol in usuarios.roles():
        if rol.codigo == codigo:
            return rol
    raise DatosInvalidos(f"El rol {codigo.value} no está activo")


def _existente(usuarios: UsuarioRepository, usuario_id: UUID) -> Usuario:
    usuario = usuarios.obtener(usuario_id)
    if usuario is None:
        raise RecursoNoExiste("El usuario no existe")
    return usuario


class ListarUsuarios:
    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def ejecutar(
        self, activo: bool | None, rol: CodigoRol | None, offset: int, limite: int
    ) -> tuple[list[Usuario], int]:
        return self._usuarios.listar(activo, rol, offset, limite)


class ObtenerUsuario:
    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def ejecutar(self, usuario_id: UUID) -> Usuario:
        return _existente(self._usuarios, usuario_id)


class CrearUsuario:
    """POST /usuarios: valida el rol antes de crear la cuenta, para no dejar cuentas sin perfil."""

    def __init__(self, proveedor: ProveedorIdentidad, usuarios: UsuarioRepository) -> None:
        self._proveedor = proveedor
        self._usuarios = usuarios

    def ejecutar(self, correo: str, nombre_completo: str, rol: CodigoRol, contrasena_temporal: str) -> Usuario:
        rol_activo = _rol_activo(self._usuarios, rol)
        usuario_id = self._proveedor.crear_cuenta(correo, contrasena_temporal)
        nuevo = Usuario(usuario_id, correo, nombre_completo.strip(), rol_activo, True, datetime.now(UTC))
        return self._usuarios.guardar(nuevo)


class ActualizarUsuario:
    """PATCH /usuarios/{id}: cambia nombre o rol. Lo que no se envía queda igual."""

    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def ejecutar(self, usuario_id: UUID, nombre_completo: str | None, rol: CodigoRol | None) -> Usuario:
        usuario = _existente(self._usuarios, usuario_id)
        if nombre_completo is not None:
            usuario = replace(usuario, nombre_completo=nombre_completo.strip())
        if rol is not None:
            usuario = replace(usuario, rol=_rol_activo(self._usuarios, rol))
        return self._usuarios.guardar(usuario)


class CambiarEstadoUsuario:
    """PATCH /usuarios/{id}/estado: no existe DELETE; las cuentas se desactivan (HU-09)."""

    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def ejecutar(self, usuario_id: UUID, activo: bool) -> Usuario:
        usuario = _existente(self._usuarios, usuario_id)
        return self._usuarios.guardar(replace(usuario, activo=activo))


class ListarRoles:
    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def ejecutar(self) -> list[Rol]:
        return self._usuarios.roles()

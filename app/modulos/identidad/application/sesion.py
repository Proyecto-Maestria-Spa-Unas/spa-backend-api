"""Casos de uso de sesión (B5): iniciar sesión y consultar la sesión actual.

Solo dependen de los puertos. Los adaptadores reales son `ProveedorSupabaseAuth` (Supabase Auth)
y `UsuarioRepositorySQL` (esquema `seguridad`, pendiente de la migración D5).
"""

from uuid import UUID

from app.compartido.errores import CredencialesInvalidas, NoAutenticado, UsuarioInactivo
from app.modulos.identidad.application.puertos import ProveedorIdentidad, UsuarioRepository
from app.modulos.identidad.domain.modelo import Usuario, puede_iniciar_sesion


class IniciarSesion:
    """POST /auth/login (HU-01).

    Primero verifica las credenciales y solo después el estado de la cuenta, para no revelar
    si un correo existe o si su cuenta está desactivada a quien no conoce la contraseña.
    """

    def __init__(self, proveedor: ProveedorIdentidad, usuarios: UsuarioRepository) -> None:
        self._proveedor = proveedor
        self._usuarios = usuarios

    def ejecutar(self, correo: str, contrasena: str) -> Usuario:
        usuario_id = self._proveedor.verificar_credenciales(correo, contrasena)
        if usuario_id is None:
            raise CredencialesInvalidas()
        usuario = self._usuarios.obtener(usuario_id)
        if usuario is None:
            # La cuenta existe en Supabase Auth pero no tiene perfil en `seguridad.perfil`.
            raise CredencialesInvalidas()
        if not puede_iniciar_sesion(usuario):
            raise UsuarioInactivo()
        return usuario


class ConsultarSesion:
    """GET /auth/me (HU-01, RNF-07): perfil, rol y permisos vigentes del usuario del token."""

    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def ejecutar(self, usuario_id: UUID) -> Usuario:
        usuario = self._usuarios.obtener(usuario_id)
        if usuario is None:
            raise NoAutenticado("La cuenta del token ya no existe")
        if not puede_iniciar_sesion(usuario):
            raise UsuarioInactivo()
        return usuario

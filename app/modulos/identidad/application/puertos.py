"""Puertos (interfaces) que los casos de uso necesitan. Los adaptadores viven en infrastructure/."""

from typing import Protocol
from uuid import UUID

from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario


class ProveedorIdentidad(Protocol):
    """Supabase Auth: verifica credenciales y crea cuentas. Único lugar que usa SUPABASE_SECRET_KEY."""

    def verificar_credenciales(self, correo: str, contrasena: str) -> UUID | None: ...

    def crear_cuenta(self, correo: str, contrasena_temporal: str) -> UUID: ...


class RecuperacionContrasena(Protocol):
    """Supabase Auth: envía el correo con el enlace para restablecer la contraseña (X3)."""

    def solicitar_recuperacion(self, correo: str) -> None:
        """Pide el envío del correo. No revela si la cuenta existe y no falla si el correo no sale."""
        ...


class UsuarioRepository(Protocol):
    """Tablas seguridad.perfil, seguridad.rol, seguridad.rol_permiso."""

    def obtener(self, usuario_id: UUID) -> Usuario | None: ...

    def listar(
        self, activo: bool | None, rol: CodigoRol | None, offset: int, limite: int
    ) -> tuple[list[Usuario], int]: ...

    def guardar(self, usuario: Usuario) -> Usuario: ...

    def roles(self) -> list[Rol]: ...

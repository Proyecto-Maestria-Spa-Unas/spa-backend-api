"""Adaptador de UsuarioRepository con SQLAlchemy (esquema `seguridad`).

TODO (S1): mapear seguridad.perfil, rol y rol_permiso cuando spa-database publique su migración.
Este módulo solo lee y escribe tablas de `seguridad`; nunca ejecuta DDL.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario


class UsuarioRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def obtener(self, usuario_id: UUID) -> Usuario | None:
        raise NotImplementedError

    def listar(self, activo: bool | None, rol: CodigoRol | None, offset: int, limite: int) -> tuple[list[Usuario], int]:
        raise NotImplementedError

    def guardar(self, usuario: Usuario) -> Usuario:
        raise NotImplementedError

    def roles(self) -> list[Rol]:
        raise NotImplementedError

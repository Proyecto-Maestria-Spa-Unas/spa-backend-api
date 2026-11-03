"""Adaptador de UsuarioRepository con SQLAlchemy (esquema `seguridad`).

- `roles()` lee seguridad.rol, rol_permiso y permiso (migración D5, 20261102090000_seguridad.sql).
- TODO (B5/B6): `obtener`, `listar` y `guardar` esperan la columna `seguridad.perfil.nombre_completo`
  que exige el contrato identidad-v1 (spa-database#12).
Este módulo solo lee y escribe tablas de `seguridad`; nunca ejecuta DDL.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario

_SQL_ROLES = text(
    """
    select r.codigo,
           r.nombre,
           coalesce(array_agg(p.codigo order by p.codigo) filter (where p.codigo is not null), '{}') as permisos
    from seguridad.rol r
    left join seguridad.rol_permiso rp on rp.rol_id = r.id
    left join seguridad.permiso p on p.id = rp.permiso_id and p.activo
    where r.activo
    group by r.codigo, r.nombre
    order by r.codigo
    """
)


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
        """Roles activos con sus permisos activos, ordenados por código.

        Un rol sin permisos activos se devuelve con el conjunto vacío.
        """
        filas = self._session.execute(_SQL_ROLES).all()
        return [
            Rol(codigo=CodigoRol(fila.codigo), nombre=fila.nombre, permisos=frozenset(fila.permisos)) for fila in filas
        ]

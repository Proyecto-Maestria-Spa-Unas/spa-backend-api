"""Adaptador de UsuarioRepository con SQLAlchemy (esquema `seguridad`).

- `roles()` lee seguridad.rol, rol_permiso y permiso (migración D5, 20261102090000_seguridad.sql).
- `obtener()` (B5) lee seguridad.perfil, auth.users (correo) y el rol con sus permisos. Requiere la
  columna `seguridad.perfil.nombre_completo` (spa-database#30), que exige el contrato identidad-v1.
- TODO (B6): `listar` y `guardar`.
Este módulo solo lee y escribe tablas de `seguridad`; nunca ejecuta DDL.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario

_SQL_USUARIO = text(
    """
    select pe.usuario_id,
           u.email,
           pe.nombre_completo,
           pe.activo,
           pe.creado_en,
           r.codigo as rol_codigo,
           r.nombre as rol_nombre,
           coalesce(array_agg(p.codigo order by p.codigo) filter (where p.codigo is not null), '{}') as permisos
    from seguridad.perfil pe
    join auth.users u on u.id = pe.usuario_id
    join seguridad.rol r on r.id = pe.rol_id
    left join seguridad.rol_permiso rp on rp.rol_id = r.id and r.activo
    left join seguridad.permiso p on p.id = rp.permiso_id and p.activo
    where pe.usuario_id = :usuario_id
    group by pe.usuario_id, u.email, pe.nombre_completo, pe.activo, pe.creado_en, r.codigo, r.nombre
    """
)

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
        """Perfil con correo, rol y permisos vigentes. Si el rol está inactivo, no tiene permisos."""
        fila = self._session.execute(_SQL_USUARIO, {"usuario_id": usuario_id}).first()
        if fila is None:
            return None
        rol = Rol(codigo=CodigoRol(fila.rol_codigo), nombre=fila.rol_nombre, permisos=frozenset(fila.permisos))
        return Usuario(
            id=fila.usuario_id,
            correo=fila.email,
            nombre_completo=fila.nombre_completo,
            rol=rol,
            activo=fila.activo,
            creado_en=fila.creado_en,
        )

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

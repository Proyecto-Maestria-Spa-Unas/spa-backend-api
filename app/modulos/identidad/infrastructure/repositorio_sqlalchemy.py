"""Adaptador de UsuarioRepository con SQLAlchemy (esquema `seguridad`).

- `roles()` lee seguridad.rol, rol_permiso y permiso (migración D5, 20261102090000_seguridad.sql).
- `obtener()` (B5) lee seguridad.perfil, auth.users (correo) y el rol con sus permisos. Requiere la
  columna `seguridad.perfil.nombre_completo` (spa-database#30), que exige el contrato identidad-v1.
- `listar()` y `guardar()` (B6): consulta paginada y alta o cambio del perfil (nombre, rol, estado).
Este módulo solo lee y escribe tablas de `seguridad`; nunca ejecuta DDL.
"""

from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, Row, text
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
_SQL_LISTA = text(
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
    where (cast(:activo as boolean) is null or pe.activo = :activo)
      and (cast(:rol as text) is null or r.codigo = :rol)
    group by pe.usuario_id, u.email, pe.nombre_completo, pe.activo, pe.creado_en, r.codigo, r.nombre
    order by pe.nombre_completo, pe.usuario_id
    limit :limite offset :offset
    """
)
_SQL_TOTAL = text(
    """
    select count(*)
    from seguridad.perfil pe
    join seguridad.rol r on r.id = pe.rol_id
    where (cast(:activo as boolean) is null or pe.activo = :activo)
      and (cast(:rol as text) is null or r.codigo = :rol)
    """
)
_SQL_GUARDAR = text(
    """
    insert into seguridad.perfil (usuario_id, rol_id, activo, nombre_completo)
    select :usuario_id, r.id, :activo, :nombre_completo from seguridad.rol r where r.codigo = :rol
    on conflict (usuario_id) do update
       set rol_id = excluded.rol_id,
           activo = excluded.activo,
           nombre_completo = excluded.nombre_completo,
           actualizado_en = now()
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
        return None if fila is None else _usuario(fila)

    def listar(self, activo: bool | None, rol: CodigoRol | None, offset: int, limite: int) -> tuple[list[Usuario], int]:
        filtros = {"activo": activo, "rol": rol.value if rol else None}
        total = self._session.execute(_SQL_TOTAL, filtros).scalar_one()
        filas = self._session.execute(_SQL_LISTA, {**filtros, "limite": limite, "offset": offset}).all()
        return [_usuario(f) for f in filas], total

    def guardar(self, usuario: Usuario) -> Usuario:
        """Crea el perfil o actualiza nombre, rol y estado. El correo vive en Supabase Auth y no se cambia aquí."""
        resultado = cast(
            CursorResult[Any],
            self._session.execute(
                _SQL_GUARDAR,
                {
                    "usuario_id": usuario.id,
                    "rol": usuario.rol.codigo.value,
                    "activo": usuario.activo,
                    "nombre_completo": usuario.nombre_completo,
                },
            ),
        )
        if resultado.rowcount != 1:
            raise ValueError(f"El rol {usuario.rol.codigo} no existe en seguridad.rol")
        guardado = self.obtener(usuario.id)
        if guardado is None:
            raise ValueError(f"No se encontró el perfil {usuario.id} después de guardarlo")
        return guardado

    def roles(self) -> list[Rol]:
        """Roles activos con sus permisos activos, ordenados por código.

        Un rol sin permisos activos se devuelve con el conjunto vacío.
        """
        filas = self._session.execute(_SQL_ROLES).all()
        return [
            Rol(codigo=CodigoRol(fila.codigo), nombre=fila.nombre, permisos=frozenset(fila.permisos)) for fila in filas
        ]


def _usuario(fila: Row[Any]) -> Usuario:
    rol = Rol(codigo=CodigoRol(fila.rol_codigo), nombre=fila.rol_nombre, permisos=frozenset(fila.permisos))
    return Usuario(
        id=fila.usuario_id,
        correo=fila.email,
        nombre_completo=fila.nombre_completo,
        rol=rol,
        activo=fila.activo,
        creado_en=fila.creado_en,
    )

"""Router de S1 · Identidad. Cada función es un endpoint del contrato (sección 5).

No cambie la ruta, el permiso ni el esquema sin un PR de contrato aprobado por frontend.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.compartido.contrato import respuestas
from app.compartido.db import get_session
from app.compartido.paginacion import Pagina, Paginacion
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, UsuarioActual, emitir_token, requiere
from app.modulos.identidad.api.esquemas import (
    LoginEntrada,
    LoginSalida,
    Mensaje,
    RecuperarEntrada,
    Rol,
    Usuario,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioEstado,
    UsuarioSesion,
)
from app.modulos.identidad.application.gestion import (
    ActualizarUsuario,
    CambiarEstadoUsuario,
    CrearUsuario,
    ListarRoles,
    ListarUsuarios,
    ObtenerUsuario,
)
from app.modulos.identidad.application.puertos import ProveedorIdentidad, RecuperacionContrasena, UsuarioRepository
from app.modulos.identidad.application.recuperacion import SolicitarRecuperacion
from app.modulos.identidad.application.sesion import ConsultarSesion, IniciarSesion
from app.modulos.identidad.domain.modelo import CodigoRol
from app.modulos.identidad.domain.modelo import Rol as RolDominio
from app.modulos.identidad.domain.modelo import Usuario as UsuarioDominio
from app.modulos.identidad.infrastructure.repositorio_sqlalchemy import UsuarioRepositorySQL
from app.modulos.identidad.infrastructure.supabase_auth import (
    ProveedorIdentidadNoDisponible,
    ProveedorSupabaseAuth,
)

router = APIRouter(tags=["identidad"])
Gestor = Annotated[Principal, Depends(requiere(Permiso.USUARIO_GESTIONAR))]


def obtener_repositorio_usuarios(session: Annotated[Session, Depends(get_session)]) -> UsuarioRepository:
    return UsuarioRepositorySQL(session)


def obtener_proveedor_identidad() -> ProveedorIdentidad:
    try:
        return ProveedorSupabaseAuth.desde_configuracion()
    except ValueError as exc:
        raise ProveedorIdentidadNoDisponible("El servicio de autenticación no está configurado") from exc


def obtener_recuperacion() -> RecuperacionContrasena:
    try:
        return ProveedorSupabaseAuth.desde_configuracion()
    except ValueError as exc:
        raise ProveedorIdentidadNoDisponible("El servicio de autenticación no está configurado") from exc


Usuarios = Annotated[UsuarioRepository, Depends(obtener_repositorio_usuarios)]
Proveedor = Annotated[ProveedorIdentidad, Depends(obtener_proveedor_identidad)]
Recuperacion = Annotated[RecuperacionContrasena, Depends(obtener_recuperacion)]


def _sesion(usuario: UsuarioDominio) -> UsuarioSesion:
    return UsuarioSesion(
        id=usuario.id,
        correo=usuario.correo,
        nombre_completo=usuario.nombre_completo,
        rol=usuario.rol.codigo,
        permisos=sorted(usuario.rol.permisos),
    )


def _usuario(usuario: UsuarioDominio) -> Usuario:
    return Usuario(
        id=usuario.id,
        correo=usuario.correo,
        nombre_completo=usuario.nombre_completo,
        rol=usuario.rol.codigo,
        activo=usuario.activo,
        creado_en=usuario.creado_en,
    )


def _rol(rol: RolDominio) -> Rol:
    return Rol(codigo=rol.codigo, nombre=rol.nombre, permisos=sorted(rol.permisos))


@router.post(
    "/auth/login",
    response_model=LoginSalida,
    summary="Iniciar sesión",
    description="Público · HU-01",
    responses=respuestas(),
)
def login(datos: LoginEntrada, usuarios: Usuarios, proveedor: Proveedor) -> LoginSalida:
    usuario = IniciarSesion(proveedor, usuarios).ejecutar(datos.correo, datos.contrasena)
    token, vigencia = emitir_token(usuario.id, usuario.rol.codigo.value, sorted(usuario.rol.permisos))
    return LoginSalida(access_token=token, expires_in=vigencia, usuario=_sesion(usuario))


@router.post(
    "/auth/recuperar",
    response_model=Mensaje,
    status_code=202,
    summary="Solicitar recuperación de contraseña",
    description="Público · Supabase Auth envía el correo. Responde 202 aunque el correo no exista (no revela cuentas)",
    responses=respuestas(),
)
def recuperar_contrasena(datos: RecuperarEntrada, recuperacion: Recuperacion) -> Mensaje:
    return Mensaje(mensaje=SolicitarRecuperacion(recuperacion).ejecutar(datos.correo))


@router.get(
    "/auth/me",
    response_model=UsuarioSesion,
    summary="Sesión actual: perfil, rol y permisos",
    description="Autenticado · HU-01, RNF-07",
    responses=respuestas(),
)
def sesion_actual(principal: UsuarioActual, usuarios: Usuarios) -> UsuarioSesion:
    return _sesion(ConsultarSesion(usuarios).ejecutar(principal.usuario_id))


@router.get(
    "/usuarios",
    response_model=Pagina[Usuario],
    summary="Listar usuarios",
    description="usuario.gestionar · HU-09",
    responses=respuestas(),
)
def listar_usuarios(
    _: Gestor,
    pagina: Paginacion,
    usuarios: Usuarios,
    activo: Annotated[bool | None, Query()] = None,
    rol: Annotated[CodigoRol | None, Query()] = None,
) -> Pagina[Usuario]:
    items, total = ListarUsuarios(usuarios).ejecutar(activo, rol, pagina.offset, pagina.size)
    return Pagina[Usuario](items=[_usuario(u) for u in items], total=total, page=pagina.page, size=pagina.size)


@router.post(
    "/usuarios",
    response_model=Usuario,
    status_code=201,
    summary="Crear usuario",
    description="usuario.gestionar · HU-09, RF-13",
    responses=respuestas(409),
)
def crear_usuario(_: Gestor, datos: UsuarioCrear, usuarios: Usuarios, proveedor: Proveedor) -> Usuario:
    caso = CrearUsuario(proveedor, usuarios)
    return _usuario(caso.ejecutar(datos.correo, datos.nombre_completo, datos.rol, datos.contrasena_temporal))


@router.get(
    "/usuarios/{usuario_id}",
    response_model=Usuario,
    summary="Consultar usuario",
    description="usuario.gestionar · HU-09",
    responses=respuestas(404),
)
def obtener_usuario(_: Gestor, usuario_id: UUID, usuarios: Usuarios) -> Usuario:
    return _usuario(ObtenerUsuario(usuarios).ejecutar(usuario_id))


@router.patch(
    "/usuarios/{usuario_id}",
    response_model=Usuario,
    summary="Cambiar nombre o rol",
    description="usuario.gestionar · HU-09",
    responses=respuestas(404),
)
def actualizar_usuario(_: Gestor, usuario_id: UUID, datos: UsuarioActualizar, usuarios: Usuarios) -> Usuario:
    return _usuario(ActualizarUsuario(usuarios).ejecutar(usuario_id, datos.nombre_completo, datos.rol))


@router.patch(
    "/usuarios/{usuario_id}/estado",
    response_model=Usuario,
    summary="Activar o desactivar (no existe DELETE)",
    description="usuario.gestionar · HU-09",
    responses=respuestas(404),
)
def cambiar_estado_usuario(_: Gestor, usuario_id: UUID, datos: UsuarioEstado, usuarios: Usuarios) -> Usuario:
    return _usuario(CambiarEstadoUsuario(usuarios).ejecutar(usuario_id, datos.activo))


@router.get(
    "/roles",
    response_model=list[Rol],
    summary="Roles con sus permisos",
    description="usuario.gestionar · RF-01",
    responses=respuestas(),
)
def listar_roles(_: Gestor, usuarios: Usuarios) -> list[Rol]:
    return [_rol(r) for r in ListarRoles(usuarios).ejecutar()]

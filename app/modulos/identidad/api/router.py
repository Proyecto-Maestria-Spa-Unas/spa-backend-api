"""Router de S1 · Identidad. Cada función es un endpoint del contrato (sección 5).

Para implementar: reemplace `raise NoImplementado()` por la llamada al caso de uso.
No cambie la ruta, el permiso ni el esquema sin un PR de contrato aprobado por frontend.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.compartido.contrato import respuestas
from app.compartido.errores import NoImplementado
from app.compartido.paginacion import Pagina, Paginacion
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, UsuarioActual, requiere
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
from app.modulos.identidad.domain.modelo import CodigoRol

router = APIRouter(tags=["identidad"])
Gestor = Annotated[Principal, Depends(requiere(Permiso.USUARIO_GESTIONAR))]


@router.post(
    "/auth/login",
    response_model=LoginSalida,
    summary="Iniciar sesión",
    description="Público · HU-01",
    responses=respuestas(),
)
def login(datos: LoginEntrada) -> LoginSalida:
    raise NoImplementado()


@router.post(
    "/auth/recuperar",
    response_model=Mensaje,
    status_code=202,
    summary="Solicitar recuperación de contraseña",
    description="Público · Supabase Auth envía el correo. Responde 202 aunque el correo no exista (no revela cuentas)",
    responses=respuestas(),
)
def recuperar_contrasena(datos: RecuperarEntrada) -> Mensaje:
    raise NoImplementado()


@router.get(
    "/auth/me",
    response_model=UsuarioSesion,
    summary="Sesión actual: perfil, rol y permisos",
    description="Autenticado · HU-01, RNF-07",
    responses=respuestas(),
)
def sesion_actual(principal: UsuarioActual) -> UsuarioSesion:
    raise NoImplementado()


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
    activo: Annotated[bool | None, Query()] = None,
    rol: Annotated[CodigoRol | None, Query()] = None,
) -> Pagina[Usuario]:
    raise NoImplementado()


@router.post(
    "/usuarios",
    response_model=Usuario,
    status_code=201,
    summary="Crear usuario",
    description="usuario.gestionar · HU-09, RF-13",
    responses=respuestas(409),
)
def crear_usuario(_: Gestor, datos: UsuarioCrear) -> Usuario:
    raise NoImplementado()


@router.get(
    "/usuarios/{usuario_id}",
    response_model=Usuario,
    summary="Consultar usuario",
    description="usuario.gestionar · HU-09",
    responses=respuestas(404),
)
def obtener_usuario(_: Gestor, usuario_id: UUID) -> Usuario:
    raise NoImplementado()


@router.patch(
    "/usuarios/{usuario_id}",
    response_model=Usuario,
    summary="Cambiar nombre o rol",
    description="usuario.gestionar · HU-09",
    responses=respuestas(404),
)
def actualizar_usuario(_: Gestor, usuario_id: UUID, datos: UsuarioActualizar) -> Usuario:
    raise NoImplementado()


@router.patch(
    "/usuarios/{usuario_id}/estado",
    response_model=Usuario,
    summary="Activar o desactivar (no existe DELETE)",
    description="usuario.gestionar · HU-09",
    responses=respuestas(404),
)
def cambiar_estado_usuario(_: Gestor, usuario_id: UUID, datos: UsuarioEstado) -> Usuario:
    raise NoImplementado()


@router.get(
    "/roles",
    response_model=list[Rol],
    summary="Roles con sus permisos",
    description="usuario.gestionar · RF-01",
    responses=respuestas(),
)
def listar_roles(_: Gestor) -> list[Rol]:
    raise NoImplementado()

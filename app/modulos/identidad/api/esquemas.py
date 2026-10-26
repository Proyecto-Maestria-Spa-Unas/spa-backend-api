"""Esquemas del contrato identidad-v1. Cambiarlos cambia docs/openapi/identidad-v1.yaml."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modulos.identidad.domain.modelo import CodigoRol

CORREO = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255, examples=["admin@spa.co"])


class LoginEntrada(BaseModel):
    correo: str = CORREO
    contrasena: str = Field(min_length=8, max_length=128)


class UsuarioSesion(BaseModel):
    id: UUID
    correo: str
    nombre_completo: str
    rol: CodigoRol
    permisos: list[str]


class LoginSalida(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - tipo de token OAuth2, no es una contraseña
    expires_in: int = Field(description="Segundos de vigencia del token")
    usuario: UsuarioSesion


class Usuario(BaseModel):
    id: UUID
    correo: str
    nombre_completo: str
    rol: CodigoRol
    activo: bool
    creado_en: datetime


class UsuarioCrear(BaseModel):
    correo: str = CORREO
    nombre_completo: str = Field(min_length=3, max_length=120)
    rol: CodigoRol
    contrasena_temporal: str = Field(min_length=8, max_length=128)


class UsuarioActualizar(BaseModel):
    nombre_completo: str | None = Field(default=None, min_length=3, max_length=120)
    rol: CodigoRol | None = None


class UsuarioEstado(BaseModel):
    activo: bool


class Rol(BaseModel):
    codigo: CodigoRol
    nombre: str
    permisos: list[str]


class RecuperarEntrada(BaseModel):
    correo: str = CORREO


class Mensaje(BaseModel):
    mensaje: str

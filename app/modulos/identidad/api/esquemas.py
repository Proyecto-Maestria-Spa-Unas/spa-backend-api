"""Esquemas del contrato identidad-v1. Cambiarlos cambia docs/openapi/identidad-v1.yaml."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modulos.identidad.domain.modelo import CodigoRol

PATRON_CORREO = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
EJEMPLO_ID = "a0000000-0000-4000-8000-000000000001"
PERMISOS_ADMIN = ["producto.consultar", "producto.crear", "movimiento.registrar_salida", "usuario.gestionar"]


class LoginEntrada(BaseModel):
    correo: str = Field(pattern=PATRON_CORREO, max_length=255, examples=["admin@spa.co"])
    contrasena: str = Field(min_length=8, max_length=128, examples=["Clave-Segura-2026"])


class UsuarioSesion(BaseModel):
    id: UUID = Field(examples=[EJEMPLO_ID])
    correo: str = Field(examples=["admin@spa.co"])
    nombre_completo: str = Field(examples=["Laura Gómez"])
    rol: CodigoRol
    permisos: list[str] = Field(
        examples=[PERMISOS_ADMIN], description="Permisos del rol; el frontend oculta lo que no esté aquí"
    )


class LoginSalida(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."], description="JWT HS256")
    token_type: str = "bearer"  # noqa: S105 - tipo de token OAuth2, no es una contraseña
    expires_in: int = Field(examples=[1800], description="Segundos de vigencia del token")
    usuario: UsuarioSesion


class Usuario(BaseModel):
    id: UUID = Field(examples=[EJEMPLO_ID])
    correo: str = Field(examples=["manicurista@spa.co"])
    nombre_completo: str = Field(examples=["Diana Pérez"])
    rol: CodigoRol
    activo: bool = Field(examples=[True], description="Los usuarios no se borran: se desactivan (HU-09)")
    creado_en: datetime


class UsuarioCrear(BaseModel):
    correo: str = Field(pattern=PATRON_CORREO, max_length=255, examples=["nueva@spa.co"])
    nombre_completo: str = Field(min_length=3, max_length=120, examples=["Camila Rojas"])
    rol: CodigoRol
    contrasena_temporal: str = Field(
        min_length=8, max_length=128, examples=["Temporal-2026"], description="La usuaria la cambia al ingresar"
    )


class UsuarioActualizar(BaseModel):
    nombre_completo: str | None = Field(default=None, min_length=3, max_length=120, examples=["Camila Rojas Díaz"])
    rol: CodigoRol | None = None


class UsuarioEstado(BaseModel):
    activo: bool = Field(examples=[False], description="false desactiva la cuenta; no existe DELETE")


class Rol(BaseModel):
    codigo: CodigoRol
    nombre: str = Field(examples=["Administrador"])
    permisos: list[str] = Field(examples=[PERMISOS_ADMIN])


class RecuperarEntrada(BaseModel):
    correo: str = Field(pattern=PATRON_CORREO, max_length=255, examples=["manicurista@spa.co"])


class Mensaje(BaseModel):
    mensaje: str = Field(examples=["Si el correo está registrado, recibirá un enlace para restablecer la contraseña."])
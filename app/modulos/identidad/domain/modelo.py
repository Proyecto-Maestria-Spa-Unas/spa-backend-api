"""Modelo del dominio de identidad. Sin FastAPI, sin SQLAlchemy, sin Supabase."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class CodigoRol(StrEnum):
    ADMINISTRADOR = "ADMINISTRADOR"
    MANICURISTA = "MANICURISTA"
    GERENTE = "GERENTE"  # DEC-01: pendiente de confirmar por el grupo


@dataclass(frozen=True, slots=True)
class Rol:
    codigo: CodigoRol
    nombre: str
    permisos: frozenset[str] = field(default_factory=frozenset)


@dataclass(slots=True)
class Usuario:
    id: UUID
    correo: str
    nombre_completo: str
    rol: Rol
    activo: bool
    creado_en: datetime

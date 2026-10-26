"""Esquemas del contrato catalogo-v1. Cambiarlos cambia docs/openapi/catalogo-v1.yaml."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.compartido.tipos import Cantidad
from app.modulos.catalogo.domain.modelo import EstadoInventario, Magnitud


class Categoria(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    orden: int = 0
    activa: bool = True


class CategoriaCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    orden: int = Field(default=0, ge=0)


class CategoriaActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    orden: int | None = Field(default=None, ge=0)
    activa: bool | None = None


class UnidadMedida(BaseModel):
    id: int
    codigo: str = Field(examples=["ML"])
    nombre: str = Field(examples=["Mililitro"])
    magnitud: Magnitud
    admite_decimales: bool


class Producto(BaseModel):
    id: UUID
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_id: int
    unidad_medida_id: int
    stock_actual: Cantidad
    stock_minimo: Cantidad | None = None
    estado: EstadoInventario
    descontinuado: bool
    version: int = Field(description="Enviar en If-Match al actualizar (bloqueo optimista)")
    creado_en: datetime
    actualizado_en: datetime


class ProductoCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=40, description="Único (RN-01)")
    nombre: str = Field(min_length=1, max_length=120, description="Obligatorio (RN-02)")
    descripcion: str | None = None
    categoria_id: int
    unidad_medida_id: int
    stock_minimo: Cantidad | None = Field(default=None, ge=0)
    cantidad_inicial: Cantidad | None = Field(
        default=None, gt=0, description="Se registra como ENTRADA con motivo SALDO_INICIAL"
    )


class ProductoActualizar(BaseModel):
    """No permite cambiar `codigo` ni `stock_actual`."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = None
    categoria_id: int | None = None
    unidad_medida_id: int | None = None


class StockMinimo(BaseModel):
    stock_minimo: Cantidad | None = Field(ge=0, description="null quita el mínimo (RN-14)")


class Ubicacion(BaseModel):
    """Coordenadas WGS84 (EPSG:4326). En la base: geography(Point, 4326) con índice GIST."""

    latitud: float = Field(ge=-90, le=90, examples=[4.6533])
    longitud: float = Field(ge=-180, le=180, examples=[-74.0836])


class Proveedor(BaseModel):
    id: UUID
    nombre: str
    nit: str = Field(examples=["900123456-7"])
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    ubicacion: Ubicacion | None = None
    activo: bool = True


class ProveedorCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    nit: str = Field(pattern=r"^[0-9]{6,10}-[0-9]$", description="NIT colombiano con dígito de verificación")
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    direccion: str | None = Field(default=None, max_length=200)
    ubicacion: Ubicacion | None = None


class ProveedorActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    direccion: str | None = Field(default=None, max_length=200)
    ubicacion: Ubicacion | None = None
    activo: bool | None = None

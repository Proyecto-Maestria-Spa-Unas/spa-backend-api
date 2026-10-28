"""Esquemas del contrato catalogo-v1. Cambiarlos cambia docs/openapi/catalogo-v1.yaml."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.compartido.tipos import Cantidad
from app.modulos.catalogo.domain.modelo import EstadoInventario, Magnitud


class Categoria(BaseModel):
    id: int = Field(examples=[1])
    nombre: str = Field(examples=["Esmaltes"])
    descripcion: str | None = Field(default=None, examples=["Esmaltes tradicionales y semipermanentes"])
    orden: int = Field(default=0, examples=[1], description="Posición en los filtros del frontend")
    activa: bool = Field(default=True, description="Las inactivas no aparecen en GET /categorias")


class CategoriaCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=80, examples=["Removedores"])
    descripcion: str | None = Field(default=None, max_length=200, examples=["Acetona y removedores sin acetona"])
    orden: int = Field(default=0, ge=0, examples=[2])


class CategoriaActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    orden: int | None = Field(default=None, ge=0)
    activa: bool | None = None


class UnidadMedida(BaseModel):
    id: int = Field(examples=[2])
    codigo: str = Field(examples=["ML"])
    nombre: str = Field(examples=["Mililitro"])
    magnitud: Magnitud
    admite_decimales: bool = Field(description="RN-04: si es false, las cantidades deben ser enteras")


class Producto(BaseModel):
    id: UUID = Field(examples=["0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b"])
    codigo: str = Field(examples=["REM-001"])
    nombre: str = Field(examples=["Acetona pura"])
    descripcion: str | None = Field(default=None, examples=["Presentación de galón"])
    categoria_id: int = Field(examples=[2])
    unidad_medida_id: int = Field(examples=[2])
    stock_actual: Cantidad = Field(examples=["350.000"], description="Solo cambia por movimientos (trigger de S0)")
    stock_minimo: Cantidad | None = Field(default=None, examples=["500.000"], description="null = sin alerta (RN-14)")
    estado: EstadoInventario = Field(description="Calculado por la base (RN-08..RN-11)")
    descontinuado: bool = Field(examples=[False])
    version: int = Field(description="Enviar en If-Match al actualizar (bloqueo optimista)")
    creado_en: datetime
    actualizado_en: datetime


class ProductoCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=40, description="Único (RN-01)", examples=["ESM-002"])
    nombre: str = Field(
        min_length=1, max_length=120, description="Obligatorio (RN-02)", examples=["Esmalte nude 15 ml"]
    )
    descripcion: str | None = Field(default=None, examples=["Acabado brillante"])
    categoria_id: int = Field(examples=[1])
    unidad_medida_id: int = Field(examples=[1])
    stock_minimo: Cantidad | None = Field(default=None, ge=0, examples=["6"])
    cantidad_inicial: Cantidad | None = Field(
        default=None, gt=0, description="Se registra como ENTRADA con motivo SALDO_INICIAL", examples=["24"]
    )


class ProductoActualizar(BaseModel):
    """No permite cambiar `codigo` ni `stock_actual`."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120, examples=["Esmalte nude 15 ml mate"])
    descripcion: str | None = None
    categoria_id: int | None = Field(default=None, examples=[1])
    unidad_medida_id: int | None = None


class StockMinimo(BaseModel):
    stock_minimo: Cantidad | None = Field(ge=0, description="null quita el mínimo (RN-14)", examples=["10"])


class Ubicacion(BaseModel):
    """Coordenadas WGS84 (EPSG:4326). En la base: geography(Point, 4326) con índice GIST."""

    latitud: float = Field(ge=-90, le=90, examples=[4.6533])
    longitud: float = Field(ge=-180, le=180, examples=[-74.0836])


class Proveedor(BaseModel):
    id: UUID
    nombre: str = Field(examples=["Distribuidora Belleza Total"])
    nit: str = Field(examples=["900123456-7"])
    telefono: str | None = Field(default=None, examples=["6015550101"])
    correo: str | None = Field(default=None, examples=["ventas@bellezatotal.co"])
    direccion: str | None = Field(default=None, examples=["Cl. 63 #13-20, Chapinero, Bogotá"])
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

"""Router de S2 · Catálogo. No existe DELETE /productos: FastAPI responde 405 (RN-12)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.compartido.contrato import respuestas
from app.compartido.errores import NoImplementado
from app.compartido.paginacion import Pagina, Paginacion
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, requiere
from app.modulos.catalogo.api.esquemas import (
    Categoria,
    CategoriaActualizar,
    CategoriaCrear,
    Producto,
    ProductoActualizar,
    ProductoCrear,
    Proveedor,
    ProveedorActualizar,
    ProveedorCrear,
    StockMinimo,
    UnidadMedida,
)
from app.modulos.catalogo.domain.modelo import EstadoInventario

router = APIRouter(tags=["catalogo"])


Consultor = Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_CONSULTAR))]
AdminCatalogo = Annotated[Principal, Depends(requiere(Permiso.CATALOGO_ADMINISTRAR))]
Descontinuador = Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_DESCONTINUAR))]


@router.get(
    "/categorias",
    response_model=list[Categoria],
    summary="Listar categorías activas",
    description="producto.consultar · HU-04, RF-12 · Sprint 1 (B4)",
    responses=respuestas(),
)
def listar_categorias(_: Consultor) -> list[Categoria]:
    raise NoImplementado()


@router.post(
    "/categorias",
    response_model=Categoria,
    status_code=201,
    summary="Crear categoría",
    description="catalogo.administrar · RNF-09",
    responses=respuestas(409),
)
def crear_categoria(_: AdminCatalogo, datos: CategoriaCrear) -> Categoria:
    raise NoImplementado()


@router.patch(
    "/categorias/{categoria_id}",
    response_model=Categoria,
    summary="Renombrar o desactivar categoría",
    description="catalogo.administrar · RNF-09",
    responses=respuestas(404, 409),
)
def actualizar_categoria(_: AdminCatalogo, categoria_id: int, datos: CategoriaActualizar) -> Categoria:
    raise NoImplementado()


@router.get(
    "/unidades-medida",
    response_model=list[UnidadMedida],
    summary="Unidades de medida",
    description="producto.consultar · HU-02",
    responses=respuestas(),
)
def listar_unidades(_: Consultor) -> list[UnidadMedida]:
    raise NoImplementado()


@router.get(
    "/productos",
    response_model=Pagina[Producto],
    summary="Consultar inventario vigente",
    description="producto.consultar · HU-03, HU-04, RF-03, RF-11, RF-19",
    responses=respuestas(),
)
def listar_productos(
    _: Consultor,
    pagina: Paginacion,
    categoria_id: Annotated[int | None, Query()] = None,
    estado: Annotated[EstadoInventario | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=80, description="Busca en código y nombre")] = None,
    incluir_descontinuados: Annotated[bool, Query()] = False,
) -> Pagina[Producto]:
    raise NoImplementado()


@router.get(
    "/productos/{producto_id}",
    response_model=Producto,
    summary="Detalle del producto",
    description="producto.consultar · RF-03",
    responses=respuestas(404),
)
def obtener_producto(_: Consultor, producto_id: UUID) -> Producto:
    raise NoImplementado()


@router.post(
    "/productos",
    response_model=Producto,
    status_code=201,
    summary="Crear producto",
    description="producto.crear · HU-02, RF-02, RN-01, RN-02",
    responses=respuestas(409),
)
def crear_producto(
    _: Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_CREAR))], datos: ProductoCrear
) -> Producto:
    raise NoImplementado()


@router.patch(
    "/productos/{producto_id}",
    response_model=Producto,
    summary="Actualizar producto",
    description="producto.editar · HU-05, RF-04",
    responses=respuestas(404, 412),
)
def actualizar_producto(
    _: Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_EDITAR))],
    producto_id: UUID,
    datos: ProductoActualizar,
    if_match: Annotated[int, Header(alias="If-Match", description="Versión actual del producto")],
) -> Producto:
    raise NoImplementado()


@router.put(
    "/productos/{producto_id}/stock-minimo",
    response_model=Producto,
    summary="Configurar stock mínimo",
    description="producto.configurar_minimo · RF-16, RN-14",
    responses=respuestas(404),
)
def configurar_stock_minimo(
    _: Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_CONFIGURAR_MINIMO))],
    producto_id: UUID,
    datos: StockMinimo,
) -> Producto:
    raise NoImplementado()


@router.post(
    "/productos/{producto_id}/descontinuar",
    response_model=Producto,
    summary="Descontinuar producto",
    description="producto.descontinuar · HU-12, RF-05, RN-11, RN-12",
    responses=respuestas(404, 409),
)
def descontinuar_producto(_: Descontinuador, producto_id: UUID) -> Producto:
    raise NoImplementado()


@router.post(
    "/productos/{producto_id}/reactivar",
    response_model=Producto,
    summary="Revertir la descontinuación",
    description="producto.descontinuar · HU-12",
    responses=respuestas(404, 409),
)
def reactivar_producto(_: Descontinuador, producto_id: UUID) -> Producto:
    raise NoImplementado()


@router.get(
    "/proveedores",
    response_model=list[Proveedor],
    summary="Listar proveedores",
    description="producto.consultar · reposición (RF-17)",
    responses=respuestas(),
)
def listar_proveedores(_: Consultor, incluir_inactivos: Annotated[bool, Query()] = False) -> list[Proveedor]:
    raise NoImplementado()


@router.post(
    "/proveedores",
    response_model=Proveedor,
    status_code=201,
    summary="Registrar proveedor con su ubicación",
    description="catalogo.administrar · NIT único",
    responses=respuestas(409),
)
def crear_proveedor(_: AdminCatalogo, datos: ProveedorCrear) -> Proveedor:
    raise NoImplementado()


@router.patch(
    "/proveedores/{proveedor_id}",
    response_model=Proveedor,
    summary="Actualizar o desactivar proveedor (no existe DELETE)",
    description="catalogo.administrar",
    responses=respuestas(404),
)
def actualizar_proveedor(_: AdminCatalogo, proveedor_id: UUID, datos: ProveedorActualizar) -> Proveedor:
    raise NoImplementado()

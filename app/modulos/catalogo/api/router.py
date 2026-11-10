"""Router de S2 · Catálogo."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.compartido.contrato import respuestas
from app.compartido.db import get_session
from app.compartido.errores import RecursoNoExiste
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
    Ubicacion,
    UnidadMedida,
)
from app.modulos.catalogo.domain.modelo import (
    EstadoInventario,
)
from app.modulos.catalogo.domain.modelo import (
    Producto as ProductoDominio,
)
from app.modulos.catalogo.domain.modelo import (
    Proveedor as ProveedorDominio,
)
from app.modulos.catalogo.infrastructure.proveedores_sql import ProveedoresSQL
from app.modulos.catalogo.infrastructure.repositorio_sqlalchemy import (
    CatalogoRepositorySQL,
)

router = APIRouter(tags=["catalogo"])

Consultor = Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_CONSULTAR))]
AdminCatalogo = Annotated[Principal, Depends(requiere(Permiso.CATALOGO_ADMINISTRAR))]
Descontinuador = Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_DESCONTINUAR))]


def obtener_catalogo_repository(
    session: Annotated[Session, Depends(get_session)],
) -> CatalogoRepositorySQL:
    return CatalogoRepositorySQL(session)


CatalogoRepo = Annotated[CatalogoRepositorySQL, Depends(obtener_catalogo_repository)]


def obtener_proveedores_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ProveedoresSQL:
    return ProveedoresSQL(session)


ProveedoresRepo = Annotated[ProveedoresSQL, Depends(obtener_proveedores_repository)]


def producto_a_respuesta(producto: ProductoDominio) -> Producto:
    """Convierte la entidad del dominio al esquema de respuesta de la API."""
    return Producto(
        id=producto.id,
        codigo=producto.codigo,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        categoria_id=producto.categoria_id,
        unidad_medida_id=producto.unidad_medida_id,
        stock_actual=producto.stock_actual,
        stock_minimo=producto.stock_minimo,
        estado=producto.estado,
        descontinuado=producto.descontinuado,
        version=producto.version,
        creado_en=producto.creado_en,
        actualizado_en=producto.actualizado_en,
    )


def proveedor_a_respuesta(proveedor: ProveedorDominio) -> Proveedor:
    """Convierte la entidad del dominio al esquema de respuesta de la API."""
    ubicacion = (
        Ubicacion(latitud=proveedor.latitud, longitud=proveedor.longitud)
        if proveedor.latitud is not None and proveedor.longitud is not None
        else None
    )

    return Proveedor(
        id=proveedor.id,
        nit=proveedor.nit,
        nombre=proveedor.nombre,
        telefono=proveedor.telefono,
        correo=proveedor.correo,
        direccion=proveedor.direccion,
        ubicacion=ubicacion,
        activo=proveedor.activo,
    )


@router.get(
    "/categorias",
    response_model=list[Categoria],
    summary="Listar categorías activas",
    description="producto.consultar · HU-04, RF-12 · Sprint 1 (B4)",
    responses=respuestas(),
)
def listar_categorias(_: Consultor, repositorio: CatalogoRepo) -> list[Categoria]:
    return [
        Categoria.model_validate(categoria, from_attributes=True) for categoria in repositorio.listar_categorias(True)
    ]


@router.post(
    "/categorias",
    response_model=Categoria,
    status_code=201,
    summary="Crear categoría",
    description="catalogo.administrar · RNF-09",
    responses=respuestas(409),
)
def crear_categoria(_: AdminCatalogo, datos: CategoriaCrear, repositorio: CatalogoRepo) -> Categoria:
    categoria = repositorio.crear_categoria(datos.model_dump())
    return Categoria.model_validate(categoria, from_attributes=True)


@router.patch(
    "/categorias/{categoria_id}",
    response_model=Categoria,
    summary="Renombrar o desactivar categoría",
    description="catalogo.administrar · RNF-09",
    responses=respuestas(404, 409),
)
def actualizar_categoria(
    _: AdminCatalogo,
    categoria_id: int,
    datos: CategoriaActualizar,
    repositorio: CatalogoRepo,
) -> Categoria:
    categoria = repositorio.actualizar_categoria(categoria_id, datos.model_dump(exclude_unset=True))
    return Categoria.model_validate(categoria, from_attributes=True)


@router.get(
    "/unidades-medida",
    response_model=list[UnidadMedida],
    summary="Unidades de medida",
    description="producto.consultar · HU-02",
    responses=respuestas(),
)
def listar_unidades(_: Consultor, repositorio: CatalogoRepo) -> list[UnidadMedida]:
    return [UnidadMedida.model_validate(unidad, from_attributes=True) for unidad in repositorio.listar_unidades()]


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
    repositorio: CatalogoRepo,
    categoria_id: Annotated[int | None, Query()] = None,
    estado: Annotated[EstadoInventario | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=80, description="Busca en código y nombre")] = None,
    incluir_descontinuados: Annotated[bool, Query()] = False,
) -> Pagina[Producto]:
    productos, total = repositorio.listar_productos(
        categoria_id=categoria_id,
        estado=estado,
        q=q,
        incluir_descontinuados=incluir_descontinuados,
        offset=pagina.offset,
        limite=pagina.size,
    )

    return Pagina[Producto](
        items=[producto_a_respuesta(p) for p in productos],
        total=total,
        page=pagina.page,
        size=pagina.size,
    )


@router.get(
    "/productos/{producto_id}",
    response_model=Producto,
    summary="Detalle del producto",
    description="producto.consultar · RF-03",
    responses=respuestas(404),
)
def obtener_producto(
    _: Consultor,
    producto_id: UUID,
    repositorio: CatalogoRepo,
) -> Producto:
    producto = repositorio.obtener_producto(producto_id)

    if producto is None:
        raise RecursoNoExiste("Producto no encontrado")

    return producto_a_respuesta(producto)


@router.post(
    "/productos",
    response_model=Producto,
    status_code=201,
    summary="Crear producto",
    description="producto.crear · HU-02, RF-02, RN-01, RN-02",
    responses=respuestas(409),
)
def crear_producto(
    principal: Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_CREAR))],
    datos: ProductoCrear,
    repositorio: CatalogoRepo,
) -> Producto:
    valores = datos.model_dump(exclude={"cantidad_inicial"})
    producto = repositorio.crear_producto(valores, datos.cantidad_inicial, principal.usuario_id)
    return producto_a_respuesta(producto)


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
    repositorio: CatalogoRepo,
) -> Producto:
    producto = repositorio.actualizar_producto(producto_id, if_match, datos.model_dump(exclude_unset=True))
    return producto_a_respuesta(producto)


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
    repositorio: CatalogoRepo,
) -> Producto:
    producto = repositorio.cambiar_producto(producto_id, "stock_minimo", datos.stock_minimo)
    return producto_a_respuesta(producto)


@router.post(
    "/productos/{producto_id}/descontinuar",
    response_model=Producto,
    summary="Descontinuar producto",
    description="producto.descontinuar · HU-12, RF-05, RN-11, RN-12",
    responses=respuestas(404, 409),
)
def descontinuar_producto(_: Descontinuador, producto_id: UUID, repositorio: CatalogoRepo) -> Producto:
    producto = repositorio.cambiar_producto(producto_id, "descontinuado", True)
    return producto_a_respuesta(producto)


@router.post(
    "/productos/{producto_id}/reactivar",
    response_model=Producto,
    summary="Revertir la descontinuación",
    description="producto.descontinuar · HU-12",
    responses=respuestas(404, 409),
)
def reactivar_producto(_: Descontinuador, producto_id: UUID, repositorio: CatalogoRepo) -> Producto:
    producto = repositorio.cambiar_producto(producto_id, "descontinuado", False)
    return producto_a_respuesta(producto)


@router.get(
    "/proveedores",
    response_model=list[Proveedor],
    summary="Listar proveedores",
    description="producto.consultar · reposición (RF-17)",
    responses=respuestas(),
)
def listar_proveedores(
    _: Consultor,
    repositorio: ProveedoresRepo,
    incluir_inactivos: Annotated[bool, Query()] = False,
) -> list[Proveedor]:
    proveedores = repositorio.listar(incluir_inactivos)
    return [proveedor_a_respuesta(proveedor) for proveedor in proveedores]


@router.post(
    "/proveedores",
    response_model=Proveedor,
    status_code=201,
    summary="Registrar proveedor con su ubicación",
    description="catalogo.administrar · NIT único",
    responses=respuestas(409),
)
def crear_proveedor(
    _: AdminCatalogo,
    datos: ProveedorCrear,
    repositorio: ProveedoresRepo,
) -> Proveedor:
    proveedor = repositorio.crear(datos.model_dump(mode="python"))
    return proveedor_a_respuesta(proveedor)


@router.patch(
    "/proveedores/{proveedor_id}",
    response_model=Proveedor,
    summary="Actualizar o desactivar proveedor (no existe DELETE)",
    description="catalogo.administrar",
    responses=respuestas(404),
)
def actualizar_proveedor(
    _: AdminCatalogo,
    proveedor_id: UUID,
    datos: ProveedorActualizar,
    repositorio: ProveedoresRepo,
) -> Proveedor:
    proveedor = repositorio.actualizar(
        proveedor_id,
        datos.model_dump(exclude_unset=True),
    )
    return proveedor_a_respuesta(proveedor)

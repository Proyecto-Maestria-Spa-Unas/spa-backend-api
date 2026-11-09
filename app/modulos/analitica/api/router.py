"""Router de S4 · Alertas y analítica. Solo lectura."""

from datetime import UTC, date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.compartido.contrato import respuestas
from app.compartido.db import get_session
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, requiere
from app.modulos.analitica.api.esquemas import (
    Alerta,
    Cobertura,
    ColeccionProveedores,
    ConsumoItem,
    GeometriaPunto,
    Kardex,
    LineaKardex,
    ProductoRotacion,
    PropiedadesProveedor,
    ProveedorCercano,
    ResumenAlertas,
    Tablero,
)
from app.modulos.analitica.application.alertas import ConsultarResumenAlertas, ListarAlertas
from app.modulos.analitica.application.exportacion import ExportarDatos
from app.modulos.analitica.application.kardex import ConsultarKardex
from app.modulos.analitica.application.proveedores import BuscarProveedoresCercanos, ConsultasProveedores
from app.modulos.analitica.application.puertos import Exportador
from app.modulos.analitica.application.tablero import CalcularCobertura, ConsultarConsumo, ObtenerTablero
from app.modulos.analitica.domain.modelo import AgrupacionConsumo, EstadoAlerta
from app.modulos.analitica.domain.modelo import Alerta as AlertaDominio
from app.modulos.analitica.domain.modelo import ResumenAlertas as ResumenDominio
from app.modulos.analitica.infrastructure.consultas_sql import ConsultasAnaliticasSQL
from app.modulos.analitica.infrastructure.exportador_duckdb import ExportadorDuckDB
from app.modulos.analitica.infrastructure.proveedores_sql import ProveedoresSQL

router = APIRouter(tags=["analitica"])
LectorAlertas = Annotated[Principal, Depends(requiere(Permiso.ALERTA_CONSULTAR))]
Analista = Annotated[Principal, Depends(requiere(Permiso.ANALITICA_CONSULTAR))]

# Colombia no tiene horario de verano: UTC-5 fijo (evita depender de tzdata en Windows).
BOGOTA = timezone(timedelta(hours=-5))


def hoy_bogota() -> date:
    return datetime.now(UTC).astimezone(BOGOTA).date()


def obtener_consultas(session: Annotated[Session, Depends(get_session)]) -> ConsultasAnaliticasSQL:
    return ConsultasAnaliticasSQL(session)


Consultas = Annotated[ConsultasAnaliticasSQL, Depends(obtener_consultas)]
Hoy = Annotated[date, Depends(hoy_bogota)]


def _alerta(alerta: AlertaDominio) -> Alerta:
    return Alerta(
        producto_id=alerta.producto_id,
        codigo=alerta.codigo,
        nombre=alerta.nombre,
        stock_actual=alerta.stock_actual,
        stock_minimo=alerta.stock_minimo,
        estado=alerta.estado,
        faltante=alerta.faltante,
    )


def _resumen(resumen: ResumenDominio) -> ResumenAlertas:
    return ResumenAlertas(bajo_stock=resumen.bajo_stock, agotado=resumen.agotado, total=resumen.total)


@router.get(
    "/alertas",
    response_model=list[Alerta],
    summary="Productos que requieren reposición",
    description="alerta.consultar · HU-10, HU-11, RF-17, RF-18",
    responses=respuestas(),
)
def listar_alertas(
    _: LectorAlertas,
    consultas: Consultas,
    estado: Annotated[EstadoAlerta | None, Query()] = None,
) -> list[Alerta]:
    return [_alerta(a) for a in ListarAlertas(consultas).ejecutar(estado)]


@router.get(
    "/alertas/resumen",
    response_model=ResumenAlertas,
    summary="Conteo por estado (indicador del menú)",
    description="alerta.consultar · RF-18",
    responses=respuestas(),
)
def resumen_alertas(_: LectorAlertas, consultas: Consultas) -> ResumenAlertas:
    return _resumen(ConsultarResumenAlertas(consultas).ejecutar())


@router.get(
    "/analitica/tablero",
    response_model=Tablero,
    summary="Indicadores para la toma de decisiones",
    description="analitica.consultar · RF-19",
    responses=respuestas(),
)
def tablero(_: Analista, consultas: Consultas, hoy: Hoy) -> Tablero:
    r = ObtenerTablero(consultas)(hoy)
    return Tablero(
        productos_por_estado=r.productos_por_estado,
        valor_inventario=r.valor_inventario,
        consumo_30_dias=r.consumo_30_dias,
        top_rotacion=[
            ProductoRotacion(producto_id=UUID(f.producto_id), codigo=f.codigo, nombre=f.nombre, consumo=f.consumo)
            for f in r.top_rotacion
        ],
    )


@router.get(
    "/analitica/consumo",
    response_model=list[ConsumoItem],
    summary="Consumo en un rango de fechas",
    description="analitica.consultar · RF-14",
    responses=respuestas(),
)
def consumo(
    _: Analista,
    desde: Annotated[date, Query()],
    hasta: Annotated[date, Query()],
    consultas: Consultas,
    agrupar_por: Annotated[AgrupacionConsumo, Query()] = AgrupacionConsumo.CATEGORIA,
) -> list[ConsumoItem]:
    return [
        ConsumoItem(clave=f.clave, cantidad=f.cantidad) for f in ConsultarConsumo(consultas)(desde, hasta, agrupar_por)
    ]


@router.get(
    "/analitica/cobertura",
    response_model=list[Cobertura],
    summary="Días de cobertura estimados",
    description="analitica.consultar · RF-17",
    responses=respuestas(),
)
def cobertura(_: Analista, consultas: Consultas, hoy: Hoy) -> list[Cobertura]:
    return [
        Cobertura(
            producto_id=UUID(f.producto_id),
            codigo=f.codigo,
            nombre=f.nombre,
            stock_actual=f.stock_actual,
            consumo_diario_promedio=f.consumo_diario_promedio,
            dias_cobertura=f.dias_cobertura,
        )
        for f in CalcularCobertura(consultas)(hoy)
    ]


def obtener_exportador(session: Annotated[Session, Depends(get_session)]) -> Exportador:
    return ExportadorDuckDB(session)


ExportadorDatos = Annotated[Exportador, Depends(obtener_exportador)]


@router.get(
    "/analitica/exportar",
    summary="Exportar inventario o movimientos (DuckDB)",
    description="analitica.consultar · RNF-10",
    response_class=Response,
    responses={
        **respuestas(),
        200: {"content": {"text/csv": {}, "application/vnd.apache.parquet": {}}, "description": "Archivo"},
    },
)
def exportar(
    _: Analista,
    conjunto: Annotated[Literal["inventario", "movimientos"], Query()],
    exportador: ExportadorDatos,
    hoy: Hoy,
    formato: Annotated[Literal["csv", "parquet"], Query()] = "csv",
) -> Response:
    archivo = ExportarDatos(exportador)(conjunto, formato, hoy)
    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo_mime,
        headers={
            "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
            "Cache-Control": "no-store",  # son datos del negocio: que ningún caché los guarde
        },
    )


@router.get(
    "/analitica/kardex",
    response_model=Kardex,
    summary="Kardex valorizado de un producto (costo promedio ponderado)",
    description="analitica.consultar · RF-14, DEC-11",
    responses=respuestas(404),
)
def kardex(
    _: Analista,
    producto_id: Annotated[UUID, Query()],
    consultas: Consultas,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> Kardex:
    r = ConsultarKardex(consultas)(producto_id, desde, hasta)
    return Kardex(
        producto_id=r.producto.producto_id,
        codigo=r.producto.codigo,
        nombre=r.producto.nombre,
        lineas=[
            LineaKardex(
                ocurrido_en=linea.ocurrido_en,
                tipo=linea.tipo,
                motivo_codigo=linea.motivo_codigo,
                cantidad=linea.cantidad,
                costo_unitario=linea.costo_unitario,
                costo_total=linea.costo_total,
                saldo=linea.saldo,
                costo_promedio=linea.costo_promedio,
                valor_saldo=linea.valor_saldo,
            )
            for linea in r.lineas
        ],
        saldo_final=r.saldo_final,
        valor_final=r.valor_final,
    )


def obtener_proveedores(session: Annotated[Session, Depends(get_session)]) -> ConsultasProveedores:
    return ProveedoresSQL(session)


Proveedores = Annotated[ConsultasProveedores, Depends(obtener_proveedores)]


@router.get(
    "/analitica/proveedores-cercanos",
    response_model=ColeccionProveedores,
    summary="Proveedores dentro de un radio (PostGIS ST_DWithin) en GeoJSON",
    description="alerta.consultar · reposición de productos en alerta (RF-17)",
    responses=respuestas(),
)
def proveedores_cercanos(
    _: LectorAlertas,
    proveedores: Proveedores,
    latitud: Annotated[float, Query(ge=-90, le=90)],
    longitud: Annotated[float, Query(ge=-180, le=180)],
    radio_km: Annotated[float, Query(gt=0, le=100)] = 10,
) -> ColeccionProveedores:
    # RFC 7946: las coordenadas van como [longitud, latitud].
    return ColeccionProveedores(
        features=[
            ProveedorCercano(
                geometry=GeometriaPunto(coordinates=(p.longitud, p.latitud)),
                properties=PropiedadesProveedor(
                    proveedor_id=p.proveedor_id, nombre=p.nombre, telefono=p.telefono, distancia_km=p.distancia_km
                ),
            )
            for p in BuscarProveedoresCercanos(proveedores)(latitud, longitud, radio_km)
        ]
    )

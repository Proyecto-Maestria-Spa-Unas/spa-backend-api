"""Router de S4 · Alertas y analítica. Solo lectura."""

from datetime import UTC, date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.compartido.contrato import respuestas
from app.compartido.db import get_session
from app.compartido.errores import NoImplementado
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, requiere
from app.modulos.analitica.api.esquemas import (
    Alerta,
    Cobertura,
    ColeccionProveedores,
    ConsumoItem,
    Kardex,
    LineaKardex,
    ProductoRotacion,
    ResumenAlertas,
    Tablero,
)
from app.modulos.analitica.application.kardex import ConsultarKardex
from app.modulos.analitica.application.tablero import CalcularCobertura, ConsultarConsumo, ObtenerTablero
from app.modulos.analitica.domain.modelo import AgrupacionConsumo, EstadoAlerta
from app.modulos.analitica.infrastructure.consultas_sql import ConsultasAnaliticasSQL

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


@router.get(
    "/alertas",
    response_model=list[Alerta],
    summary="Productos que requieren reposición",
    description="alerta.consultar · HU-10, HU-11, RF-17, RF-18",
    responses=respuestas(),
)
def listar_alertas(_: LectorAlertas, estado: Annotated[EstadoAlerta | None, Query()] = None) -> list[Alerta]:
    raise NoImplementado()


@router.get(
    "/alertas/resumen",
    response_model=ResumenAlertas,
    summary="Conteo por estado (indicador del menú)",
    description="alerta.consultar · RF-18",
    responses=respuestas(),
)
def resumen_alertas(_: LectorAlertas) -> ResumenAlertas:
    raise NoImplementado()


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
    formato: Annotated[Literal["csv", "parquet"], Query()] = "csv",
) -> Response:
    raise NoImplementado()


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


@router.get(
    "/analitica/proveedores-cercanos",
    response_model=ColeccionProveedores,
    summary="Proveedores dentro de un radio (PostGIS ST_DWithin) en GeoJSON",
    description="alerta.consultar · reposición de productos en alerta (RF-17)",
    responses=respuestas(),
)
def proveedores_cercanos(
    _: LectorAlertas,
    latitud: Annotated[float, Query(ge=-90, le=90)],
    longitud: Annotated[float, Query(ge=-180, le=180)],
    radio_km: Annotated[float, Query(gt=0, le=100)] = 10,
) -> ColeccionProveedores:
    raise NoImplementado()

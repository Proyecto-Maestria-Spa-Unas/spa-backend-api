"""Router de S4 · Alertas y analítica. Solo lectura."""

from datetime import date
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
    ResumenAlertas,
    Tablero,
)
from app.modulos.analitica.application.alertas import ConsultarResumenAlertas, ListarAlertas
from app.modulos.analitica.application.puertos import ConsultasAnaliticas
from app.modulos.analitica.domain.modelo import AgrupacionConsumo, EstadoAlerta
from app.modulos.analitica.domain.modelo import Alerta as AlertaDominio
from app.modulos.analitica.domain.modelo import ResumenAlertas as ResumenDominio
from app.modulos.analitica.infrastructure.consultas_sql import ConsultasAnaliticasSQL

router = APIRouter(tags=["analitica"])
LectorAlertas = Annotated[Principal, Depends(requiere(Permiso.ALERTA_CONSULTAR))]
Analista = Annotated[Principal, Depends(requiere(Permiso.ANALITICA_CONSULTAR))]


def obtener_consultas(session: Annotated[Session, Depends(get_session)]) -> ConsultasAnaliticas:
    return ConsultasAnaliticasSQL(session)


Consultas = Annotated[ConsultasAnaliticas, Depends(obtener_consultas)]


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
def tablero(_: Analista) -> Tablero:
    raise NoImplementado()


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
    agrupar_por: Annotated[AgrupacionConsumo, Query()] = AgrupacionConsumo.CATEGORIA,
) -> list[ConsumoItem]:
    raise NoImplementado()


@router.get(
    "/analitica/cobertura",
    response_model=list[Cobertura],
    summary="Días de cobertura estimados",
    description="analitica.consultar · RF-17",
    responses=respuestas(),
)
def cobertura(_: Analista) -> list[Cobertura]:
    raise NoImplementado()


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
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> Kardex:
    raise NoImplementado()


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

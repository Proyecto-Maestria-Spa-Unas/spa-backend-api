"""Router de S4 · Alertas y analítica. Solo lectura."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.compartido.contrato import respuestas
from app.compartido.errores import NoImplementado
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, requiere
from app.modulos.analitica.api.esquemas import Alerta, Cobertura, ConsumoItem, ResumenAlertas, Tablero
from app.modulos.analitica.domain.modelo import AgrupacionConsumo, EstadoAlerta

router = APIRouter(tags=["analitica"])
LectorAlertas = Annotated[Principal, Depends(requiere(Permiso.ALERTA_CONSULTAR))]
Analista = Annotated[Principal, Depends(requiere(Permiso.ANALITICA_CONSULTAR))]


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

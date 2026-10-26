"""Router de S3 · Movimientos. No existe DELETE /movimientos: responde 405 (ADR-0003).

Los POST exigen `Idempotency-Key` (UUID): un reintento con la misma clave devuelve el mismo movimiento.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.compartido.contrato import respuestas
from app.compartido.errores import NoImplementado
from app.compartido.paginacion import Pagina, Paginacion
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, requiere
from app.modulos.movimientos.api.esquemas import (
    AnulacionRegistrar,
    EntradaRegistrar,
    MotivoMovimiento,
    Movimiento,
    MovimientoRegistrado,
    SalidaRegistrar,
)
from app.modulos.movimientos.domain.modelo import TipoMovimiento

router = APIRouter(tags=["movimientos"])
Consultor = Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_CONSULTAR))]
ClaveIdempotencia = Annotated[UUID, Header(alias="Idempotency-Key", description="UUID único por intento")]


@router.get(
    "/motivos-movimiento",
    response_model=list[MotivoMovimiento],
    summary="Motivos válidos por tipo",
    description="movimiento.consultar · RF-10",
    responses=respuestas(),
)
def listar_motivos(_: Consultor, tipo: Annotated[TipoMovimiento | None, Query()] = None) -> list[MotivoMovimiento]:
    raise NoImplementado()


@router.post(
    "/movimientos/entradas",
    response_model=MovimientoRegistrado,
    status_code=201,
    summary="Registrar entrada",
    description="movimiento.registrar_entrada · HU-06, RF-06, RF-09, RF-10",
    responses=respuestas(404, 409),
)
def registrar_entrada(
    _: Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_REGISTRAR_ENTRADA))],
    datos: EntradaRegistrar,
    clave: ClaveIdempotencia,
) -> MovimientoRegistrado:
    raise NoImplementado()


@router.post(
    "/movimientos/salidas",
    response_model=MovimientoRegistrado,
    status_code=201,
    summary="Registrar salida o consumo",
    description="movimiento.registrar_salida · HU-07, HU-11, RF-07, RF-08, RF-09 · 409 STOCK_INSUFICIENTE",
    responses=respuestas(404, 409),
)
def registrar_salida(
    _: Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_REGISTRAR_SALIDA))],
    datos: SalidaRegistrar,
    clave: ClaveIdempotencia,
) -> MovimientoRegistrado:
    raise NoImplementado()


@router.get(
    "/movimientos",
    response_model=Pagina[Movimiento],
    summary="Historial de movimientos",
    description="movimiento.consultar · HU-08, RF-14, RF-15 · Manicurista: solo los propios",
    responses=respuestas(),
)
def listar_movimientos(
    principal: Consultor,
    pagina: Paginacion,
    producto_id: Annotated[UUID | None, Query()] = None,
    tipo: Annotated[TipoMovimiento | None, Query()] = None,
    usuario_id: Annotated[UUID | None, Query()] = None,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
) -> Pagina[Movimiento]:
    raise NoImplementado()


@router.get(
    "/movimientos/{movimiento_id}",
    response_model=Movimiento,
    summary="Detalle del movimiento",
    description="movimiento.consultar · HU-08",
    responses=respuestas(404),
)
def obtener_movimiento(principal: Consultor, movimiento_id: int) -> Movimiento:
    raise NoImplementado()


@router.post(
    "/movimientos/{movimiento_id}/anulaciones",
    response_model=MovimientoRegistrado,
    status_code=201,
    summary="Anular movimiento",
    description="movimiento.anular · HU-13, RF-20, RN-13",
    responses=respuestas(404, 409),
)
def anular_movimiento(
    _: Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_ANULAR))],
    movimiento_id: int,
    datos: AnulacionRegistrar,
    clave: ClaveIdempotencia,
) -> MovimientoRegistrado:
    raise NoImplementado()

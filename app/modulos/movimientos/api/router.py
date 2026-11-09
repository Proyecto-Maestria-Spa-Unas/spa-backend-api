"""Router de S3 · Movimientos. No existe DELETE /movimientos: responde 405 (ADR-0003).

Los POST exigen `Idempotency-Key` (UUID): un reintento con la misma clave devuelve el mismo movimiento.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.compartido.contrato import respuestas
from app.compartido.db import get_session
from app.compartido.errores import DatosInvalidos, NoImplementado, RecursoNoExiste
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
from app.modulos.movimientos.application.puertos import MovimientoRepository
from app.modulos.movimientos.domain.modelo import Movimiento as MovimientoDominio
from app.modulos.movimientos.domain.modelo import MovimientoRegistrado as MovimientoRegistradoDominio
from app.modulos.movimientos.domain.modelo import TipoMovimiento
from app.modulos.movimientos.infrastructure.repositorio_sqlalchemy import MovimientoRepositorySQL

router = APIRouter(tags=["movimientos"])
Consultor = Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_CONSULTAR))]
ClaveIdempotencia = Annotated[UUID, Header(alias="Idempotency-Key", description="UUID único por intento")]


def obtener_repositorio_movimientos(
    session: Annotated[Session, Depends(get_session)],
) -> MovimientoRepository:
    return MovimientoRepositorySQL(session)


MovimientosRepo = Annotated[
    MovimientoRepository,
    Depends(obtener_repositorio_movimientos),
]


def _respuesta_registro(
    registro: MovimientoRegistradoDominio,
) -> MovimientoRegistrado:
    return MovimientoRegistrado(
        movimiento=Movimiento.model_validate(
            registro.movimiento,
            from_attributes=True,
        ),
        saldo=registro.saldo,
        estado=registro.estado,
    )


def _respuesta_movimiento(movimiento: MovimientoDominio) -> Movimiento:
    return Movimiento.model_validate(movimiento, from_attributes=True)


@router.get(
    "/motivos-movimiento",
    response_model=list[MotivoMovimiento],
    summary="Motivos válidos por tipo",
    description="movimiento.consultar · RF-10",
    responses=respuestas(),
)
def listar_motivos(
    _: Consultor,
    repositorio: MovimientosRepo,
    tipo: Annotated[TipoMovimiento | None, Query()] = None,
) -> list[MotivoMovimiento]:
    motivos = repositorio.listar_motivos(tipo)

    return [
        MotivoMovimiento(
            id=motivo.id,
            codigo=motivo.codigo,
            nombre=motivo.nombre,
            aplica_a=motivo.aplica_a,
        )
        for motivo in motivos
    ]


@router.post(
    "/movimientos/entradas",
    response_model=MovimientoRegistrado,
    status_code=201,
    summary="Registrar entrada",
    description="movimiento.registrar_entrada · HU-06, RF-06, RF-09, RF-10",
    responses=respuestas(404, 409),
)
def registrar_entrada(
    principal: Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_REGISTRAR_ENTRADA))],
    datos: EntradaRegistrar,
    clave: ClaveIdempotencia,
    repositorio: MovimientosRepo,
) -> MovimientoRegistrado:
    registro = repositorio.registrar_entrada(
        producto_id=datos.producto_id,
        cantidad=datos.cantidad,
        motivo_codigo=datos.motivo_codigo,
        costo_unitario=datos.costo_unitario,
        proveedor_id=datos.proveedor_id,
        observacion=datos.observacion,
        registrado_por=principal.usuario_id,
        clave_idempotencia=clave,
    )
    return _respuesta_registro(registro)


@router.post(
    "/movimientos/salidas",
    response_model=MovimientoRegistrado,
    status_code=201,
    summary="Registrar salida o consumo",
    description="movimiento.registrar_salida · HU-07, HU-11, RF-07, RF-08, RF-09 · 409 STOCK_INSUFICIENTE",
    responses=respuestas(404, 409),
)
def registrar_salida(
    principal: Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_REGISTRAR_SALIDA))],
    datos: SalidaRegistrar,
    clave: ClaveIdempotencia,
    repositorio: MovimientosRepo,
) -> MovimientoRegistrado:
    registro = repositorio.registrar_salida(
        producto_id=datos.producto_id,
        cantidad=datos.cantidad,
        motivo_codigo=datos.motivo_codigo,
        observacion=datos.observacion,
        registrado_por=principal.usuario_id,
        clave_idempotencia=clave,
    )
    return _respuesta_registro(registro)


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
    repositorio: MovimientosRepo,
    producto_id: Annotated[UUID | None, Query()] = None,
    tipo: Annotated[TipoMovimiento | None, Query()] = None,
    usuario_id: Annotated[UUID | None, Query()] = None,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
) -> Pagina[Movimiento]:
    if desde is not None and hasta is not None and desde > hasta:
        raise DatosInvalidos("La fecha desde no puede ser posterior a la fecha hasta")
    filtro_usuario = principal.usuario_id if principal.rol == "MANICURISTA" else usuario_id
    movimientos, total = repositorio.listar(
        producto_id=producto_id,
        tipo=tipo,
        usuario_id=filtro_usuario,
        desde=desde,
        hasta=hasta,
        offset=pagina.offset,
        limite=pagina.size,
    )
    return Pagina[Movimiento](
        items=[_respuesta_movimiento(movimiento) for movimiento in movimientos],
        total=total,
        page=pagina.page,
        size=pagina.size,
    )


@router.get(
    "/movimientos/{movimiento_id}",
    response_model=Movimiento,
    summary="Detalle del movimiento",
    description="movimiento.consultar · HU-08",
    responses=respuestas(404),
)
def obtener_movimiento(principal: Consultor, movimiento_id: int, repositorio: MovimientosRepo) -> Movimiento:
    usuario_id = principal.usuario_id if principal.rol == "MANICURISTA" else None
    movimiento = repositorio.obtener(movimiento_id, usuario_id)
    if movimiento is None:
        raise RecursoNoExiste("Movimiento no encontrado")
    return _respuesta_movimiento(movimiento)


@router.post(
    "/movimientos/{movimiento_id}/anulaciones",
    response_model=MovimientoRegistrado,
    status_code=201,
    summary="Anular movimiento",
    description="movimiento.anular · HU-13, RF-20, RN-13",
    responses=respuestas(404, 409),
)
def anular_movimiento(
    principal: Annotated[Principal, Depends(requiere(Permiso.MOVIMIENTO_ANULAR))],
    movimiento_id: int,
    datos: AnulacionRegistrar,
    clave: ClaveIdempotencia,
    repositorio: MovimientosRepo,
) -> MovimientoRegistrado:
    registro = repositorio.anular(
        movimiento_id=movimiento_id,
        motivo=datos.motivo,
        registrado_por=principal.usuario_id,
        clave_idempotencia=clave,
    )
    return _respuesta_registro(registro)

"""Router del broker (#75).

- POST /broker/procesar: lo invoca el workflow programado con la cabecera `X-Broker-Token`.
  No usa el JWT de un usuario: es una llamada entre sistemas.
- GET /broker/metricas: estado de la cola por estado y prioridad. Permiso usuario.gestionar
  (administración del sistema: solo ADMINISTRADOR lo tiene).
"""

import hmac
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.compartido.config import get_settings
from app.compartido.contrato import respuestas
from app.compartido.db import get_session
from app.compartido.errores import ErrorDominio, NoAutenticado
from app.compartido.permisos import Permiso
from app.compartido.seguridad import Principal, requiere
from app.modulos.broker.api.esquemas import ConteoCola, MetricasCola, ResumenProcesamiento
from app.modulos.broker.application.alertas import NotificarAlertaStock
from app.modulos.broker.application.procesar import ProcesarCola
from app.modulos.broker.application.puertos import ColaRepository, NotificacionRepository
from app.modulos.broker.domain.modelo import TIPO_ALERTA_STOCK, EstadoTrabajo
from app.modulos.broker.infrastructure.repositorio_sqlalchemy import ColaRepositorySQL, NotificacionRepositorySQL


class BrokerNoConfigurado(ErrorDominio):
    code, status, title = "BROKER_NO_CONFIGURADO", 503, "El broker no tiene token configurado"


router = APIRouter(tags=["broker"])


def obtener_cola(session: Annotated[Session, Depends(get_session)]) -> ColaRepository:
    return ColaRepositorySQL(session)


def obtener_notificaciones(session: Annotated[Session, Depends(get_session)]) -> NotificacionRepository:
    return NotificacionRepositorySQL(session)


Cola = Annotated[ColaRepository, Depends(obtener_cola)]
Notificaciones = Annotated[NotificacionRepository, Depends(obtener_notificaciones)]


def verificar_token_broker(token: Annotated[str | None, Header(alias="X-Broker-Token")] = None) -> None:
    if not token:
        raise NoAutenticado("Falta el token del broker")
    secreto = get_settings().broker_token
    if secreto is None or not secreto.get_secret_value():
        raise BrokerNoConfigurado()
    if not hmac.compare_digest(token.encode(), secreto.get_secret_value().encode()):
        raise NoAutenticado("Token del broker inválido")


@router.post(
    "/broker/procesar",
    response_model=ResumenProcesamiento,
    summary="Procesar un lote de la cola por prioridad",
    description="Workflow programado con X-Broker-Token · #75",
    dependencies=[Depends(verificar_token_broker)],
    responses={
        401: {"description": "NO_AUTENTICADO: token del broker ausente o inválido"},
        503: {"description": "BROKER_NO_CONFIGURADO: falta BROKER_TOKEN en el entorno"},
    },
)
def procesar_cola(
    cola: Cola,
    notificaciones: Notificaciones,
    limite: Annotated[int, Query(ge=1, le=100, description="Trabajos por lote")] = 20,
) -> ResumenProcesamiento:
    manejadores = {TIPO_ALERTA_STOCK: NotificarAlertaStock(notificaciones)}
    resumen = ProcesarCola(cola, manejadores).ejecutar(limite)
    return ResumenProcesamiento(**asdict(resumen))


@router.get(
    "/broker/metricas",
    response_model=MetricasCola,
    summary="Estado de la cola por estado y prioridad",
    description="usuario.gestionar (solo ADMINISTRADOR) · #75",
    responses=respuestas(),
)
def metricas_cola(
    _: Annotated[Principal, Depends(requiere(Permiso.USUARIO_GESTIONAR))],
    cola: Cola,
) -> MetricasCola:
    conteos = cola.contar()
    return MetricasCola(
        pendientes=sum(c.cantidad for c in conteos if c.estado is EstadoTrabajo.PENDIENTE),
        fallidos=sum(c.cantidad for c in conteos if c.estado is EstadoTrabajo.FALLIDO),
        detalle=[ConteoCola(estado=c.estado, prioridad=c.prioridad, cantidad=c.cantidad) for c in conteos],
    )

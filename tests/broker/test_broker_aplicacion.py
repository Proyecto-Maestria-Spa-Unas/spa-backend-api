"""Caso de uso ProcesarCola, manejador de alertas y endpoints del broker, sin base de datos."""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from app.modulos.broker.api.router import obtener_cola, obtener_notificaciones
from app.modulos.broker.application.alertas import NotificarAlertaStock
from app.modulos.broker.application.procesar import ProcesarCola
from app.modulos.broker.domain.modelo import (
    TIPO_ALERTA_STOCK,
    ConteoCola,
    EstadoTrabajo,
    Fallo,
    Prioridad,
    Trabajo,
)

TOKEN = "token-de-prueba-del-broker-0123456789"
FabricaCabeceras = Callable[..., dict[str, str]]


# Dobles de prueba
class ColaFalsa:
    def __init__(self, trabajos: list[Trabajo] | None = None, conteos: list[ConteoCola] | None = None) -> None:
        self.trabajos = trabajos or []
        self.conteos = conteos or []
        self.hechos: list[int] = []
        self.fallos: list[tuple[int, Fallo, str]] = []
        self.limite: int | None = None

    def reclamar(self, limite: int, paso_envejecimiento_s: int) -> list[Trabajo]:
        self.limite = limite
        return self.trabajos[:limite]

    def ejecutar_aislado(self, accion: Callable[[], None]) -> Exception | None:
        try:
            accion()
        except Exception as error:
            return error
        return None

    def marcar_hecho(self, trabajo_id: int) -> None:
        self.hechos.append(trabajo_id)

    def marcar_fallo(self, trabajo_id: int, fallo: Fallo, error: str) -> None:
        self.fallos.append((trabajo_id, fallo, error))

    def contar(self) -> list[ConteoCola]:
        return self.conteos


class NotificacionesFalsas:
    def __init__(self) -> None:
        self.registradas: list[tuple[int, str | None, str]] = []

    def registrar(self, trabajo: Trabajo, producto_id: str | None, mensaje: str) -> None:
        self.registradas.append((trabajo.id, producto_id, mensaje))


def _trabajo(
    id_: int = 1,
    tipo: str = TIPO_ALERTA_STOCK,
    payload: dict[str, Any] | None = None,
    intentos: int = 0,
    max_intentos: int = 5,
) -> Trabajo:
    return Trabajo(
        id=id_,
        tipo=tipo,
        prioridad=Prioridad.ALTA,
        payload=payload if payload is not None else {},
        intentos=intentos,
        max_intentos=max_intentos,
        creado_en=datetime.now(UTC),
    )


ALERTA_AGOTADO = {"producto_id": "0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b", "nombre": "Acetona", "estado": "AGOTADO"}
ALERTA_BAJO = {"nombre": "Algodón", "estado": "BAJO_STOCK", "saldo": 2, "stock_minimo": 3}


def _fallar(_: Trabajo) -> None:
    raise RuntimeError("servicio externo caído")


# Caso de uso
def test_alerta_agotado_genera_notificacion_y_queda_hecha() -> None:
    cola = ColaFalsa([_trabajo(payload=ALERTA_AGOTADO)])
    bandeja = NotificacionesFalsas()
    resumen = ProcesarCola(cola, {TIPO_ALERTA_STOCK: NotificarAlertaStock(bandeja)}).ejecutar(10)

    assert (resumen.tomados, resumen.hechos, resumen.reintentos, resumen.fallidos) == (1, 1, 0, 0)
    assert cola.hechos == [1]
    assert bandeja.registradas == [(1, ALERTA_AGOTADO["producto_id"], "Acetona: agotado")]


def test_alerta_bajo_stock_indica_saldo_y_minimo() -> None:
    bandeja = NotificacionesFalsas()
    cola = ColaFalsa([_trabajo(payload=ALERTA_BAJO)])
    ProcesarCola(cola, {TIPO_ALERTA_STOCK: NotificarAlertaStock(bandeja)}).ejecutar(10)
    assert bandeja.registradas == [(1, None, "Algodón: bajo el mínimo (2 de 3)")]


def test_alerta_con_estado_invalido_se_reintenta() -> None:
    cola = ColaFalsa([_trabajo(payload={"estado": "OTRO"})])
    resumen = ProcesarCola(cola, {TIPO_ALERTA_STOCK: NotificarAlertaStock(NotificacionesFalsas())}).ejecutar(10)

    assert resumen.reintentos == 1
    _, fallo, error = cola.fallos[0]
    assert fallo.estado is EstadoTrabajo.PENDIENTE
    assert "estado no válido" in error


def test_fallo_con_intentos_disponibles_vuelve_a_la_cola() -> None:
    cola = ColaFalsa([_trabajo(intentos=1)])
    resumen = ProcesarCola(cola, {TIPO_ALERTA_STOCK: _fallar}).ejecutar(10)

    assert (resumen.hechos, resumen.reintentos, resumen.fallidos) == (0, 1, 0)
    _, fallo, error = cola.fallos[0]
    assert (fallo.intentos, fallo.reintentar_en_s) == (2, 60)
    assert error == "RuntimeError: servicio externo caído"


def test_fallo_al_agotar_intentos_va_a_fallidos() -> None:
    cola = ColaFalsa([_trabajo(intentos=4, max_intentos=5)])
    resumen = ProcesarCola(cola, {TIPO_ALERTA_STOCK: _fallar}).ejecutar(10)

    assert resumen.fallidos == 1
    assert cola.fallos[0][1].estado is EstadoTrabajo.FALLIDO


def test_tipo_sin_manejador_va_directo_a_fallidos() -> None:
    cola = ColaFalsa([_trabajo(tipo="desconocido")])
    resumen = ProcesarCola(cola, {}).ejecutar(10)

    assert resumen.fallidos == 1
    _, fallo, error = cola.fallos[0]
    assert fallo.estado is EstadoTrabajo.FALLIDO
    assert error == "Tipo de trabajo sin manejador: desconocido"


def test_respeta_el_limite_del_lote() -> None:
    cola = ColaFalsa([_trabajo(id_=i, payload=ALERTA_AGOTADO) for i in range(1, 6)])
    resumen = ProcesarCola(cola, {TIPO_ALERTA_STOCK: NotificarAlertaStock(NotificacionesFalsas())}).ejecutar(2)

    assert cola.limite == 2
    assert resumen.tomados == 2
    assert cola.hechos == [1, 2]


# Endpoints
@pytest.fixture
def con_token(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("BROKER_TOKEN", TOKEN)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def sin_token(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("BROKER_TOKEN", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def cola() -> Iterator[ColaFalsa]:
    falsa = ColaFalsa()
    app.dependency_overrides[obtener_cola] = lambda: falsa
    app.dependency_overrides[obtener_notificaciones] = NotificacionesFalsas
    yield falsa
    app.dependency_overrides.pop(obtener_cola, None)
    app.dependency_overrides.pop(obtener_notificaciones, None)


@pytest.mark.usefixtures("sin_token")
def test_procesar_sin_token_configurado_responde_503(cliente: TestClient, cola: ColaFalsa) -> None:
    respuesta = cliente.post("/api/v1/broker/procesar", headers={"X-Broker-Token": "x"})
    assert respuesta.status_code == 503
    assert respuesta.json()["code"] == "BROKER_NO_CONFIGURADO"


@pytest.mark.usefixtures("con_token")
def test_procesar_con_token_invalido_responde_401(cliente: TestClient, cola: ColaFalsa) -> None:
    sin_token = cliente.post("/api/v1/broker/procesar")
    assert (sin_token.status_code, sin_token.json()["detail"]) == (401, "Falta el token del broker")
    respuesta = cliente.post("/api/v1/broker/procesar", headers={"X-Broker-Token": "otro"})
    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


@pytest.mark.usefixtures("con_token")
def test_procesar_con_token_valido_procesa_el_lote(cliente: TestClient, cola: ColaFalsa) -> None:
    cola.trabajos = [_trabajo(payload=ALERTA_AGOTADO)]
    respuesta = cliente.post("/api/v1/broker/procesar?limite=5", headers={"X-Broker-Token": TOKEN})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"tomados": 1, "hechos": 1, "reintentos": 0, "fallidos": 0}
    assert cola.limite == 5


@pytest.mark.usefixtures("con_token")
def test_procesar_rechaza_limite_fuera_de_rango(cliente: TestClient, cola: ColaFalsa) -> None:
    respuesta = cliente.post("/api/v1/broker/procesar?limite=101", headers={"X-Broker-Token": TOKEN})
    assert respuesta.status_code == 422


def test_metricas_exigen_sesion(cliente: TestClient, cola: ColaFalsa) -> None:
    assert cliente.get("/api/v1/broker/metricas").status_code == 401


def test_metricas_exigen_usuario_gestionar(cliente: TestClient, cola: ColaFalsa, cabeceras: FabricaCabeceras) -> None:
    respuesta = cliente.get("/api/v1/broker/metricas", headers=cabeceras("analitica.consultar", rol="GERENTE"))
    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "SIN_PERMISO"


def test_metricas_suman_por_estado(cliente: TestClient, cola: ColaFalsa, cabeceras: FabricaCabeceras) -> None:
    cola.conteos = [
        ConteoCola(estado=EstadoTrabajo.FALLIDO, prioridad=Prioridad.NORMAL, cantidad=1),
        ConteoCola(estado=EstadoTrabajo.PENDIENTE, prioridad=Prioridad.ALTA, cantidad=2),
        ConteoCola(estado=EstadoTrabajo.PENDIENTE, prioridad=Prioridad.BAJA, cantidad=3),
    ]
    respuesta = cliente.get("/api/v1/broker/metricas", headers=cabeceras("usuario.gestionar"))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert (cuerpo["pendientes"], cuerpo["fallidos"]) == (5, 1)
    assert cuerpo["detalle"][1] == {"estado": "PENDIENTE", "prioridad": 1, "cantidad": 2}

"""X4 · Alertas de bajo stock: dominio, casos de uso y endpoints con un doble de las consultas."""

from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.main import app
from app.modulos.analitica.api.router import obtener_consultas
from app.modulos.analitica.application.alertas import ConsultarResumenAlertas, ListarAlertas
from app.modulos.analitica.domain.modelo import Alerta, EstadoAlerta, ResumenAlertas
from tests.conftest import FabricaToken

ALERTAS = f"{get_settings().api_prefix}/alertas"
RESUMEN = f"{get_settings().api_prefix}/alertas/resumen"

ACETONA = UUID("0b8e6f0a-3c4d-4e5f-8a9b-1c2d3e4f5a6b")


def _alerta(estado: EstadoAlerta, actual: str, minimo: str, codigo: str = "REM-001", producto_id: UUID | None = None):
    return Alerta(producto_id or uuid4(), codigo, f"Producto {codigo}", Decimal(actual), Decimal(minimo), estado)


class ConsultasFalsas:
    """Doble de ConsultasAnaliticas: filtra en memoria igual que la vista."""

    def __init__(self, *alertas: Alerta) -> None:
        self._alertas = list(alertas)
        self.estados_pedidos: list[EstadoAlerta | None] = []

    def alertas(self, estado: EstadoAlerta | None) -> list[Alerta]:
        self.estados_pedidos.append(estado)
        return [a for a in self._alertas if estado is None or a.estado == estado]

    def resumen_alertas(self) -> ResumenAlertas:
        return ResumenAlertas(
            bajo_stock=sum(a.estado is EstadoAlerta.BAJO_STOCK for a in self._alertas),
            agotado=sum(a.estado is EstadoAlerta.AGOTADO for a in self._alertas),
        )


@pytest.fixture
def con_consultas() -> Iterator[callable]:
    def _instalar(*alertas: Alerta) -> ConsultasFalsas:
        falsas = ConsultasFalsas(*alertas)
        app.dependency_overrides[obtener_consultas] = lambda: falsas
        return falsas

    yield _instalar
    app.dependency_overrides.clear()


# ── Dominio ────────────────────────────────────────────────────────────────


def test_faltante_es_minimo_menos_actual() -> None:
    assert _alerta(EstadoAlerta.BAJO_STOCK, "350.000", "500.000").faltante == Decimal("150.000")


def test_faltante_de_un_agotado_es_el_minimo_completo() -> None:
    assert _alerta(EstadoAlerta.AGOTADO, "0.000", "6.000").faltante == Decimal("6.000")


def test_faltante_nunca_es_negativo() -> None:
    assert _alerta(EstadoAlerta.BAJO_STOCK, "10.000", "5.000").faltante == Decimal(0)


def test_total_del_resumen_suma_los_dos_estados() -> None:
    resumen = ResumenAlertas(bajo_stock=5, agotado=2)
    assert resumen.total == 7


# ── Casos de uso ───────────────────────────────────────────────────────────


def test_listar_alertas_sin_filtro_pide_todas() -> None:
    falsas = ConsultasFalsas(_alerta(EstadoAlerta.BAJO_STOCK, "1", "5"), _alerta(EstadoAlerta.AGOTADO, "0", "5"))
    assert len(ListarAlertas(falsas).ejecutar()) == 2
    assert falsas.estados_pedidos == [None]


def test_listar_alertas_pasa_el_estado_a_la_consulta() -> None:
    falsas = ConsultasFalsas(_alerta(EstadoAlerta.BAJO_STOCK, "1", "5"), _alerta(EstadoAlerta.AGOTADO, "0", "5"))
    resultado = ListarAlertas(falsas).ejecutar(EstadoAlerta.AGOTADO)
    assert [a.estado for a in resultado] == [EstadoAlerta.AGOTADO]
    assert falsas.estados_pedidos == [EstadoAlerta.AGOTADO]


def test_resumen_sin_alertas_es_cero() -> None:
    assert ConsultarResumenAlertas(ConsultasFalsas()).ejecutar() == ResumenAlertas(0, 0)


# ── Endpoints ──────────────────────────────────────────────────────────────


def test_get_alertas_devuelve_el_contrato(cliente: TestClient, cabeceras: FabricaToken, con_consultas) -> None:
    con_consultas(_alerta(EstadoAlerta.BAJO_STOCK, "350.000", "500.000", producto_id=ACETONA))
    r = cliente.get(ALERTAS, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 200, r.text
    assert r.json() == [
        {
            "producto_id": str(ACETONA),
            "codigo": "REM-001",
            "nombre": "Producto REM-001",
            "stock_actual": "350.000",
            "stock_minimo": "500.000",
            "estado": "BAJO_STOCK",
            "faltante": "150.000",
        }
    ]


def test_get_alertas_sin_productos_en_alerta_devuelve_lista_vacia(
    cliente: TestClient, cabeceras: FabricaToken, con_consultas
) -> None:
    con_consultas()
    r = cliente.get(ALERTAS, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 200
    assert r.json() == []


def test_get_alertas_filtra_por_estado(cliente: TestClient, cabeceras: FabricaToken, con_consultas) -> None:
    falsas = con_consultas(
        _alerta(EstadoAlerta.BAJO_STOCK, "1", "5", "A"), _alerta(EstadoAlerta.AGOTADO, "0", "5", "B")
    )
    r = cliente.get(ALERTAS, params={"estado": "AGOTADO"}, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 200
    assert [a["codigo"] for a in r.json()] == ["B"]
    assert falsas.estados_pedidos == [EstadoAlerta.AGOTADO]


@pytest.mark.parametrize("estado", ["DISPONIBLE", "DESCONTINUADO", "agotado", ""])
def test_get_alertas_con_estado_invalido_responde_422(
    cliente: TestClient, cabeceras: FabricaToken, con_consultas, estado: str
) -> None:
    con_consultas()
    r = cliente.get(ALERTAS, params={"estado": estado}, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 422
    assert r.json()["code"] == "DATOS_INVALIDOS"
    assert r.json()["errors"][0]["campo"] == "query.estado"


def test_get_resumen_devuelve_conteos_y_total(cliente: TestClient, cabeceras: FabricaToken, con_consultas) -> None:
    con_consultas(
        _alerta(EstadoAlerta.BAJO_STOCK, "1", "5", "A"),
        _alerta(EstadoAlerta.BAJO_STOCK, "2", "5", "B"),
        _alerta(EstadoAlerta.AGOTADO, "0", "5", "C"),
    )
    r = cliente.get(RESUMEN, headers=cabeceras("alerta.consultar"))
    assert r.status_code == 200, r.text
    assert r.json() == {"bajo_stock": 2, "agotado": 1, "total": 3}


@pytest.mark.parametrize("ruta", [ALERTAS, RESUMEN])
def test_las_alertas_exigen_token_y_permiso(
    cliente: TestClient, cabeceras: FabricaToken, con_consultas, ruta: str
) -> None:
    con_consultas()
    sin_token = cliente.get(ruta)
    assert sin_token.status_code == 401
    assert sin_token.json()["code"] == "NO_AUTENTICADO"
    sin_permiso = cliente.get(ruta, headers=cabeceras("producto.consultar"))
    assert sin_permiso.status_code == 403
    assert sin_permiso.json()["code"] == "SIN_PERMISO"

"""Reglas puras del broker: envejecimiento, espera exponencial y decisión de reintento."""

from datetime import UTC, datetime

import pytest

from app.modulos.broker.domain.modelo import (
    EstadoTrabajo,
    Prioridad,
    Trabajo,
    espera_reintento,
    prioridad_efectiva,
    registrar_fallo,
)


def _trabajo(intentos: int = 0, max_intentos: int = 5) -> Trabajo:
    return Trabajo(
        id=1,
        tipo="alerta_stock",
        prioridad=Prioridad.BAJA,
        payload={},
        intentos=intentos,
        max_intentos=max_intentos,
        creado_en=datetime.now(UTC),
    )


def test_sin_espera_la_prioridad_no_cambia() -> None:
    assert prioridad_efectiva(3, 0) == 3
    assert prioridad_efectiva(2, 299) == 2


def test_envejecimiento_sube_un_nivel_por_cada_paso() -> None:
    assert prioridad_efectiva(3, 300) == 2
    assert prioridad_efectiva(3, 599) == 2
    assert prioridad_efectiva(3, 600) == 1


def test_envejecimiento_no_pasa_de_alta() -> None:
    assert prioridad_efectiva(3, 10_000) == 1
    assert prioridad_efectiva(1, 0) == 1


def test_espera_negativa_cuenta_como_cero() -> None:
    assert prioridad_efectiva(2, -50) == 2


def test_paso_de_envejecimiento_invalido() -> None:
    with pytest.raises(ValueError, match="positivo"):
        prioridad_efectiva(2, 10, paso_s=0)


def test_espera_exponencial_con_tope() -> None:
    assert [espera_reintento(i) for i in (1, 2, 3, 4)] == [30, 60, 120, 240]
    assert espera_reintento(20) == 3600


def test_espera_exige_al_menos_un_fallo() -> None:
    with pytest.raises(ValueError, match="primer fallo"):
        espera_reintento(0)


def test_fallo_con_intentos_disponibles_se_reintenta() -> None:
    fallo = registrar_fallo(_trabajo(intentos=0))
    assert fallo.estado is EstadoTrabajo.PENDIENTE
    assert fallo.intentos == 1
    assert fallo.reintentar_en_s == 30


def test_fallo_al_agotar_intentos_va_a_fallidos() -> None:
    fallo = registrar_fallo(_trabajo(intentos=4, max_intentos=5))
    assert fallo.estado is EstadoTrabajo.FALLIDO
    assert fallo.intentos == 5
    assert fallo.reintentar_en_s is None

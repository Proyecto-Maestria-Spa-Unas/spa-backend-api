"""Integración del broker contra PostgreSQL LOCAL (Docker). Estas pruebas escriben: nunca contra staging.

Uso (Git Bash):
    DB_URL_INTEGRACION=postgresql+psycopg://postgres:postgres@localhost:54322/postgres \
        .venv/Scripts/python -m pytest -m integracion tests/integration/broker -v
"""

import json
import os
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.modulos.broker.application.alertas import NotificarAlertaStock
from app.modulos.broker.application.procesar import ProcesarCola
from app.modulos.broker.domain.modelo import TIPO_ALERTA_STOCK, Trabajo
from app.modulos.broker.infrastructure.repositorio_sqlalchemy import ColaRepositorySQL, NotificacionRepositorySQL

URL = os.environ.get("DB_URL_INTEGRACION", "")
ES_LOCAL = any(host in URL for host in ("localhost", "127.0.0.1"))

pytestmark = [
    pytest.mark.integracion,
    pytest.mark.skipif(not ES_LOCAL, reason="Requiere DB_URL_INTEGRACION local: estas pruebas escriben"),
]


@pytest.fixture(scope="module")
def motor() -> Iterator[Engine]:
    engine = create_engine(URL, poolclass=NullPool)
    yield engine
    engine.dispose()


@pytest.fixture
def sesion(motor: Engine) -> Iterator[Session]:
    """Cada prueba corre en una transacción que se deshace al final."""
    with Session(motor) as s:
        # Aparta los pendientes que ya existan para que no interfieran con el orden esperado.
        s.execute(text("UPDATE broker.trabajo SET disponible_en = now() + interval '1 day' WHERE estado = 'PENDIENTE'"))
        yield s
        s.rollback()


def _insertar(
    s: Session,
    tipo: str,
    prioridad: int,
    hace_s: int = 0,
    payload: dict[str, Any] | None = None,
    max_intentos: int = 5,
) -> int:
    return int(
        s.execute(
            text(
                """
                INSERT INTO broker.trabajo (tipo, prioridad, payload, clave_idempotencia, max_intentos, creado_en)
                VALUES (:tipo, :prioridad, CAST(:payload AS jsonb), :clave, :max_intentos,
                        now() - make_interval(secs => :hace))
                RETURNING id
                """
            ),
            {
                "tipo": tipo,
                "prioridad": prioridad,
                "payload": json.dumps(payload or {}),
                "clave": f"prueba:{uuid4()}",
                "max_intentos": max_intentos,
                "hace": hace_s,
            },
        ).scalar_one()
    )


def _fallar(_: Trabajo) -> None:
    raise RuntimeError("falla simulada")


def test_orden_por_prioridad_con_envejecimiento(sesion: Session) -> None:
    baja_vieja = _insertar(sesion, "prueba_orden", 3, hace_s=1200)  # 20 min: efectiva 1
    alta = _insertar(sesion, "prueba_orden", 1)
    normal = _insertar(sesion, "prueba_orden", 2)
    baja_nueva = _insertar(sesion, "prueba_orden", 3)

    tomados = [t.id for t in ColaRepositorySQL(sesion).reclamar(10, 300)]

    assert tomados == [baja_vieja, alta, normal, baja_nueva]


def test_encolar_es_idempotente(sesion: Session) -> None:
    clave = f"prueba:{uuid4()}"
    consulta = text("SELECT broker.encolar('prueba_idem', 2, '{}'::jsonb, :clave)")
    primero = sesion.execute(consulta, {"clave": clave}).scalar_one()
    segundo = sesion.execute(consulta, {"clave": clave}).scalar_one()

    total = sesion.execute(
        text("SELECT count(*) FROM broker.trabajo WHERE clave_idempotencia = :clave"), {"clave": clave}
    ).scalar_one()
    assert primero == segundo
    assert total == 1


def test_fallo_reprograma_con_espera_y_luego_va_a_fallidos(sesion: Session) -> None:
    reintentable = _insertar(sesion, "prueba_fallo", 1, max_intentos=3)
    agotado = _insertar(sesion, "prueba_fallo", 1, max_intentos=1)

    resumen = ProcesarCola(ColaRepositorySQL(sesion), {"prueba_fallo": _fallar}).ejecutar(10)

    filas = {
        fila.id: fila
        for fila in sesion.execute(
            text(
                """
                SELECT id, estado, intentos, disponible_en > now() AS diferido, procesado_en IS NOT NULL AS cerrado,
                       ultimo_error
                FROM broker.trabajo WHERE id IN (:a, :b)
                """
            ),
            {"a": reintentable, "b": agotado},
        )
    }
    assert (resumen.reintentos, resumen.fallidos) == (1, 1)
    assert (filas[reintentable].estado, filas[reintentable].intentos, filas[reintentable].diferido) == (
        "PENDIENTE",
        1,
        True,
    )
    assert (filas[agotado].estado, filas[agotado].cerrado) == ("FALLIDO", True)
    assert filas[agotado].ultimo_error == "RuntimeError: falla simulada"


def test_alerta_genera_una_sola_notificacion(sesion: Session) -> None:
    trabajo_id = _insertar(sesion, TIPO_ALERTA_STOCK, 1, payload={"nombre": "Acetona", "estado": "AGOTADO"})
    manejadores = {TIPO_ALERTA_STOCK: NotificarAlertaStock(NotificacionRepositorySQL(sesion))}

    resumen = ProcesarCola(ColaRepositorySQL(sesion), manejadores).ejecutar(10)

    mensajes = sesion.execute(
        text("SELECT mensaje FROM broker.notificacion WHERE trabajo_id = :id"), {"id": trabajo_id}
    ).scalars()
    estado = sesion.execute(text("SELECT estado FROM broker.trabajo WHERE id = :id"), {"id": trabajo_id}).scalar_one()
    assert resumen.hechos == 1
    assert list(mensajes) == ["Acetona: agotado"]
    assert estado == "HECHO"


def test_salidas_que_cruzan_el_minimo_encolan_alertas_priorizadas(sesion: Session) -> None:
    usuario = sesion.execute(text("SELECT id FROM auth.users LIMIT 1")).scalar_one_or_none()
    if usuario is None:
        pytest.skip("No hay usuarios en auth.users para registrar movimientos")
    producto = sesion.execute(
        text(
            """
            INSERT INTO inventario.producto (codigo, nombre, categoria_id, unidad_medida_id, stock_minimo)
            VALUES (
              :codigo, 'Prueba broker',
              (SELECT id FROM inventario.categoria ORDER BY id LIMIT 1),
              (SELECT id FROM inventario.unidad_medida WHERE codigo = 'UND'),
              3
            )
            RETURNING id
            """
        ),
        {"codigo": f"QA-BRK-{uuid4().hex[:8]}"},
    ).scalar_one()

    def mover(tipo: str, motivo: str, cantidad: int) -> None:
        sesion.execute(
            text(
                """
                INSERT INTO inventario.movimiento (
                  producto_id, tipo, motivo_id, cantidad, registrado_por, clave_idempotencia
                ) VALUES (
                  :producto, :tipo,
                  (SELECT id FROM inventario.motivo_movimiento WHERE codigo = :motivo AND aplica_a = :aplica_a),
                  :cantidad, :usuario, :clave
                )
                """
            ),
            {
                "producto": producto,
                "tipo": tipo,
                "motivo": motivo,
                "aplica_a": tipo,  # parámetro aparte: la columna y aplica_a tienen tipos distintos
                "cantidad": cantidad,
                "usuario": usuario,
                "clave": uuid4(),
            },
        )

    mover("ENTRADA", "SALDO_INICIAL", 10)  # sube el stock: no encola
    mover("SALIDA", "CONSUMO_SERVICIO", 8)  # 10 → 2, cruza el mínimo 3: BAJO_STOCK
    mover("SALIDA", "CONSUMO_SERVICIO", 2)  # 2 → 0: AGOTADO

    alertas = sesion.execute(
        text(
            """
            SELECT prioridad, payload->>'estado' AS estado
            FROM broker.trabajo
            WHERE tipo = 'alerta_stock' AND payload->>'producto_id' = CAST(:producto AS text)
            ORDER BY id
            """
        ),
        {"producto": producto},
    ).all()
    assert [(a.prioridad, a.estado) for a in alertas] == [(2, "BAJO_STOCK"), (1, "AGOTADO")]


def test_dos_consumidores_no_toman_el_mismo_trabajo(motor: Engine) -> None:
    with Session(motor) as preparar:
        ids = {_insertar(preparar, "prueba_skip", 1) for _ in range(3)}
        preparar.commit()
    try:
        with Session(motor) as a, Session(motor) as b:
            b.execute(text("SET LOCAL lock_timeout = '3s'"))  # sin SKIP LOCKED, b esperaría a a
            tomados_a = {t.id for t in ColaRepositorySQL(a).reclamar(1, 300)}
            tomados_b = {t.id for t in ColaRepositorySQL(b).reclamar(50, 300)}
            a.rollback()
            b.rollback()
        assert len(tomados_a) == 1
        assert tomados_a.isdisjoint(tomados_b)
        assert ids <= tomados_a | tomados_b
    finally:
        with Session(motor) as limpiar:
            limpiar.execute(text("DELETE FROM broker.trabajo WHERE id = ANY(:ids)"), {"ids": list(ids)})
            limpiar.commit()

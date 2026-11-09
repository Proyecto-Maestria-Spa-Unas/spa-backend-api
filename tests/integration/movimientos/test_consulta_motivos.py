"""Pruebas de integración para la consulta de motivos de movimiento."""

import pytest
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modulos.movimientos.domain.modelo import TipoMovimiento
from app.modulos.movimientos.infrastructure.repositorio_sqlalchemy import (
    MovimientoRepositorySQL,
)

pytestmark = pytest.mark.integracion


def test_listar_motivos_activos(transaccion: Connection) -> None:
    """Consulta los motivos activos de entrada y salida."""

    with Session(bind=transaccion) as session:
        repositorio = MovimientoRepositorySQL(session)

        motivos = repositorio.listar_motivos()

        assert len(motivos) >= 6
        assert all(motivo.codigo for motivo in motivos)
        assert all(motivo.nombre for motivo in motivos)


def test_filtrar_motivos_por_tipo(transaccion: Connection) -> None:
    """Filtra los motivos según el tipo de movimiento."""

    with Session(bind=transaccion) as session:
        repositorio = MovimientoRepositorySQL(session)

        entradas = repositorio.listar_motivos(TipoMovimiento.ENTRADA)
        salidas = repositorio.listar_motivos(TipoMovimiento.SALIDA)

        assert entradas
        assert salidas
        assert all(m.aplica_a is TipoMovimiento.ENTRADA for m in entradas)
        assert all(m.aplica_a is TipoMovimiento.SALIDA for m in salidas)

"""B5 · `UsuarioRepositorySQL.roles()` contra el esquema `seguridad` de spa-database (migración D5)."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.compartido.permisos import Permiso
from app.modulos.identidad.domain.modelo import CodigoRol
from app.modulos.identidad.infrastructure.repositorio_sqlalchemy import UsuarioRepositorySQL
from tests.integration.conftest import esquema_existe

pytestmark = pytest.mark.integracion

# Permisos que siembra 20261102090000_seguridad.sql (sección 6 del documento de arquitectura).
ESPERADOS = {
    CodigoRol.ADMINISTRADOR: {p.value for p in Permiso},
    CodigoRol.MANICURISTA: {
        "producto.consultar",
        "movimiento.registrar_salida",
        "movimiento.consultar",
        "alerta.consultar",
    },
    CodigoRol.GERENTE: {
        "usuario.gestionar",
        "producto.consultar",
        "movimiento.consultar",
        "alerta.consultar",
        "analitica.consultar",
    },
}


@pytest.fixture
def repositorio(transaccion: Connection) -> UsuarioRepositorySQL:
    if not esquema_existe(transaccion, "seguridad"):
        pytest.skip("La base no tiene el esquema seguridad (migración D5)")
    return UsuarioRepositorySQL(Session(bind=transaccion))


def test_los_tres_roles_con_los_permisos_de_d5(repositorio: UsuarioRepositorySQL) -> None:
    roles = repositorio.roles()
    assert [r.codigo for r in roles] == sorted(ESPERADOS)
    for rol in roles:
        assert rol.permisos == frozenset(ESPERADOS[rol.codigo]), rol.codigo


def test_todos_los_permisos_de_la_base_existen_en_el_enum(repositorio: UsuarioRepositorySQL) -> None:
    validos = {p.value for p in Permiso}
    for rol in repositorio.roles():
        assert rol.permisos <= validos


def test_omite_roles_y_permisos_inactivos(transaccion: Connection, repositorio: UsuarioRepositorySQL) -> None:
    transaccion.execute(text("update seguridad.rol set activo = false where codigo = 'GERENTE'"))
    transaccion.execute(text("update seguridad.permiso set activo = false where codigo = 'alerta.consultar'"))
    roles = {r.codigo: r for r in repositorio.roles()}
    assert CodigoRol.GERENTE not in roles
    assert "alerta.consultar" not in roles[CodigoRol.MANICURISTA].permisos
    assert len(roles[CodigoRol.MANICURISTA].permisos) == 3

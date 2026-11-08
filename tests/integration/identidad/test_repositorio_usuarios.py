"""B5 · `UsuarioRepositorySQL.obtener()` contra el esquema `seguridad` de spa-database.

Requiere la columna seguridad.perfil.nombre_completo (spa-database#30). Si la base no la tiene,
las pruebas se omiten indicando la causa, en lugar de fallar.
"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modulos.identidad.domain.modelo import CodigoRol
from app.modulos.identidad.infrastructure.repositorio_sqlalchemy import UsuarioRepositorySQL
from tests.integration.conftest import esquema_existe

pytestmark = pytest.mark.integracion


@pytest.fixture
def repositorio(transaccion: Connection) -> UsuarioRepositorySQL:
    if not esquema_existe(transaccion, "seguridad"):
        pytest.skip("La base no tiene el esquema seguridad (migración D5)")
    columna = transaccion.execute(
        text(
            "select 1 from information_schema.columns "
            "where table_schema = 'seguridad' and table_name = 'perfil' and column_name = 'nombre_completo'"
        )
    ).first()
    if columna is None:
        pytest.skip("La base no tiene seguridad.perfil.nombre_completo (spa-database#30)")
    return UsuarioRepositorySQL(Session(bind=transaccion))


def _crear(transaccion: Connection, rol: str, activo: bool = True) -> tuple:
    usuario_id = uuid4()
    correo = f"qa-{usuario_id.hex[:8]}@spa.co"
    transaccion.execute(
        text("insert into auth.users (id, email) values (:id, :correo)"), {"id": usuario_id, "correo": correo}
    )
    transaccion.execute(
        text(
            "insert into seguridad.perfil (usuario_id, rol_id, activo, nombre_completo) "
            "select :id, id, :activo, 'Usuaria de prueba' from seguridad.rol where codigo = :rol"
        ),
        {"id": usuario_id, "rol": rol, "activo": activo},
    )
    return usuario_id, correo


def test_obtener_devuelve_correo_nombre_rol_y_permisos(transaccion: Connection, repositorio) -> None:
    usuario_id, correo = _crear(transaccion, "MANICURISTA")
    usuario = repositorio.obtener(usuario_id)
    assert usuario is not None
    assert (usuario.id, usuario.correo, usuario.nombre_completo, usuario.activo) == (
        usuario_id,
        correo,
        "Usuaria de prueba",
        True,
    )
    assert usuario.rol.codigo == CodigoRol.MANICURISTA
    assert usuario.rol.permisos == {
        "producto.consultar",
        "movimiento.registrar_salida",
        "movimiento.consultar",
        "alerta.consultar",
    }


def test_obtener_respeta_perfil_desactivado(transaccion: Connection, repositorio) -> None:
    usuario_id, _ = _crear(transaccion, "GERENTE", activo=False)
    usuario = repositorio.obtener(usuario_id)
    assert usuario is not None and usuario.activo is False


def test_obtener_usuario_sin_perfil_devuelve_none(repositorio) -> None:
    assert repositorio.obtener(uuid4()) is None


def test_rol_desactivado_no_aporta_permisos(transaccion: Connection, repositorio) -> None:
    usuario_id, _ = _crear(transaccion, "ADMINISTRADOR")
    transaccion.execute(text("update seguridad.rol set activo = false where codigo = 'ADMINISTRADOR'"))
    usuario = repositorio.obtener(usuario_id)
    assert usuario is not None and usuario.rol.permisos == frozenset()

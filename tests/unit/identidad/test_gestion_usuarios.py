"""B6 · Gestión de usuarios y roles: casos de uso y endpoints con dobles de los puertos."""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.compartido.config import get_settings
from app.compartido.errores import CodigoDuplicado, DatosInvalidos, RecursoNoExiste
from app.main import app
from app.modulos.identidad.api.router import obtener_proveedor_identidad, obtener_repositorio_usuarios
from app.modulos.identidad.application.gestion import (
    ActualizarUsuario,
    CambiarEstadoUsuario,
    CrearUsuario,
    ObtenerUsuario,
)
from app.modulos.identidad.domain.modelo import CodigoRol, Rol, Usuario
from tests.conftest import FabricaToken

API = get_settings().api_prefix
ROLES = {
    CodigoRol.ADMINISTRADOR: Rol(CodigoRol.ADMINISTRADOR, "Administrador", frozenset({"usuario.gestionar"})),
    CodigoRol.MANICURISTA: Rol(CodigoRol.MANICURISTA, "Manicurista", frozenset({"producto.consultar"})),
}


class Repo:
    """Doble en memoria de UsuarioRepository; solo conoce los roles de ROLES (GERENTE queda inactivo)."""

    def __init__(self, *usuarios: Usuario) -> None:
        self.datos = {u.id: u for u in usuarios}
        self.guardados: list[Usuario] = []

    def obtener(self, usuario_id: UUID) -> Usuario | None:
        return self.datos.get(usuario_id)

    def listar(self, activo, rol, offset, limite):
        sel = [
            u
            for u in self.datos.values()
            if (activo is None or u.activo == activo) and (rol is None or u.rol.codigo == rol)
        ]
        sel.sort(key=lambda u: u.nombre_completo)
        return sel[offset : offset + limite], len(sel)

    def guardar(self, usuario: Usuario) -> Usuario:
        self.guardados.append(usuario)
        self.datos[usuario.id] = usuario
        return usuario

    def roles(self) -> list[Rol]:
        return list(ROLES.values())


class Proveedor:
    def __init__(self, existentes: set[str] | None = None) -> None:
        self.existentes = existentes or set()
        self.creadas: list[str] = []

    def verificar_credenciales(self, correo: str, contrasena: str) -> UUID | None:
        return None

    def crear_cuenta(self, correo: str, contrasena_temporal: str) -> UUID:
        if correo in self.existentes:
            raise CodigoDuplicado("Ya existe una cuenta con ese correo")
        self.creadas.append(correo)
        return uuid4()


def _u(nombre: str, rol: CodigoRol = CodigoRol.MANICURISTA, activo: bool = True) -> Usuario:
    return Usuario(uuid4(), f"{nombre.split()[0].lower()}@spa.co", nombre, ROLES[rol], activo, datetime.now(UTC))


# ---------- casos de uso


def test_crear_usuario_crea_la_cuenta_y_el_perfil_activo() -> None:
    repo, prov = Repo(), Proveedor()
    u = CrearUsuario(prov, repo).ejecutar("nueva@spa.co", "  Camila Rojas  ", CodigoRol.MANICURISTA, "Temporal-2026")
    assert prov.creadas == ["nueva@spa.co"]
    assert (u.correo, u.nombre_completo, u.rol.codigo, u.activo) == (
        "nueva@spa.co",
        "Camila Rojas",
        CodigoRol.MANICURISTA,
        True,
    )


def test_crear_con_rol_inactivo_no_crea_la_cuenta() -> None:
    repo, prov = Repo(), Proveedor()
    with pytest.raises(DatosInvalidos):
        CrearUsuario(prov, repo).ejecutar("nueva@spa.co", "Camila Rojas", CodigoRol.GERENTE, "Temporal-2026")
    assert prov.creadas == [] and repo.guardados == []


def test_crear_con_correo_existente_es_codigo_duplicado_sin_perfil() -> None:
    repo, prov = Repo(), Proveedor({"nueva@spa.co"})
    with pytest.raises(CodigoDuplicado):
        CrearUsuario(prov, repo).ejecutar("nueva@spa.co", "Camila Rojas", CodigoRol.MANICURISTA, "Temporal-2026")
    assert repo.guardados == []


def test_actualizar_cambia_solo_lo_enviado() -> None:
    u = _u("Diana Pérez")
    repo = Repo(u)
    r = ActualizarUsuario(repo).ejecutar(u.id, None, CodigoRol.ADMINISTRADOR)
    assert (r.nombre_completo, r.rol.codigo) == ("Diana Pérez", CodigoRol.ADMINISTRADOR)
    r = ActualizarUsuario(repo).ejecutar(u.id, "Diana Pérez Ruiz", None)
    assert (r.nombre_completo, r.rol.codigo) == ("Diana Pérez Ruiz", CodigoRol.ADMINISTRADOR)


def test_cambiar_estado_desactiva_sin_borrar() -> None:
    u = _u("Diana Pérez")
    repo = Repo(u)
    assert CambiarEstadoUsuario(repo).ejecutar(u.id, False).activo is False
    assert u.id in repo.datos


@pytest.mark.parametrize("caso", ["obtener", "actualizar", "estado"])
def test_usuario_inexistente_es_recurso_no_existe(caso: str) -> None:
    repo, uid = Repo(), uuid4()
    with pytest.raises(RecursoNoExiste):
        {
            "obtener": lambda: ObtenerUsuario(repo).ejecutar(uid),
            "actualizar": lambda: ActualizarUsuario(repo).ejecutar(uid, "Otro Nombre", None),
            "estado": lambda: CambiarEstadoUsuario(repo).ejecutar(uid, False),
        }[caso]()


# ---------- endpoints


@pytest.fixture
def dobles() -> Iterator[tuple[Repo, Proveedor]]:
    repo = Repo(_u("Diana Pérez"), _u("Ana Gómez", activo=False), _u("Laura Ruiz", CodigoRol.ADMINISTRADOR))
    prov = Proveedor({"diana@spa.co"})
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repo
    app.dependency_overrides[obtener_proveedor_identidad] = lambda: prov
    yield repo, prov
    app.dependency_overrides.clear()


@pytest.fixture
def gestor(cabeceras: FabricaToken) -> dict[str, str]:
    return cabeceras("usuario.gestionar")


def test_listar_con_filtros_y_paginacion(cliente: TestClient, dobles, gestor) -> None:
    r = cliente.get(f"{API}/usuarios", headers=gestor, params={"activo": "true", "size": 1, "page": 2})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["total"], cuerpo["page"], cuerpo["size"]) == (2, 2, 1)
    assert [u["nombre_completo"] for u in cuerpo["items"]] == ["Laura Ruiz"]
    r = cliente.get(f"{API}/usuarios", headers=gestor, params={"rol": "MANICURISTA"})
    assert {u["nombre_completo"] for u in r.json()["items"]} == {"Diana Pérez", "Ana Gómez"}


def test_crear_responde_201_con_el_usuario(cliente: TestClient, dobles, gestor) -> None:
    datos = {
        "correo": "nueva@spa.co",
        "nombre_completo": "Camila Rojas",
        "rol": "MANICURISTA",
        "contrasena_temporal": "Temporal-2026",
    }
    r = cliente.post(f"{API}/usuarios", headers=gestor, json=datos)
    assert r.status_code == 201, r.text
    assert {k: r.json()[k] for k in ("correo", "nombre_completo", "rol", "activo")} == {
        "correo": "nueva@spa.co",
        "nombre_completo": "Camila Rojas",
        "rol": "MANICURISTA",
        "activo": True,
    }


def test_crear_con_correo_existente_responde_409(cliente: TestClient, dobles, gestor) -> None:
    datos = {
        "correo": "diana@spa.co",
        "nombre_completo": "Diana Otra",
        "rol": "MANICURISTA",
        "contrasena_temporal": "Temporal-2026",
    }
    r = cliente.post(f"{API}/usuarios", headers=gestor, json=datos)
    assert r.status_code == 409
    assert r.json()["code"] == "CODIGO_DUPLICADO"


def test_crear_con_rol_inactivo_responde_422(cliente: TestClient, dobles, gestor) -> None:
    datos = {
        "correo": "x@spa.co",
        "nombre_completo": "Equis Ye",
        "rol": "GERENTE",
        "contrasena_temporal": "Temporal-2026",
    }
    r = cliente.post(f"{API}/usuarios", headers=gestor, json=datos)
    assert r.status_code == 422
    assert r.json()["code"] == "DATOS_INVALIDOS"


def test_obtener_actualizar_y_desactivar(cliente: TestClient, dobles, gestor) -> None:
    repo, _ = dobles
    uid = next(u.id for u in repo.datos.values() if u.nombre_completo == "Diana Pérez")
    assert cliente.get(f"{API}/usuarios/{uid}", headers=gestor).json()["nombre_completo"] == "Diana Pérez"
    r = cliente.patch(f"{API}/usuarios/{uid}", headers=gestor, json={"rol": "ADMINISTRADOR"})
    assert r.status_code == 200 and r.json()["rol"] == "ADMINISTRADOR"
    r = cliente.patch(f"{API}/usuarios/{uid}/estado", headers=gestor, json={"activo": False})
    assert r.status_code == 200 and r.json()["activo"] is False


def test_usuario_inexistente_responde_404(cliente: TestClient, dobles, gestor) -> None:
    r = cliente.get(f"{API}/usuarios/{uuid4()}", headers=gestor)
    assert r.status_code == 404
    assert r.json()["code"] == "RECURSO_NO_EXISTE"


def test_roles_con_permisos_ordenados(cliente: TestClient, dobles, gestor) -> None:
    r = cliente.get(f"{API}/roles", headers=gestor)
    assert r.status_code == 200
    assert {x["codigo"]: x["permisos"] for x in r.json()} == {
        "ADMINISTRADOR": ["usuario.gestionar"],
        "MANICURISTA": ["producto.consultar"],
    }


def test_sin_usuario_gestionar_responde_403(cliente: TestClient, dobles, cabeceras: FabricaToken) -> None:
    r = cliente.get(f"{API}/usuarios", headers=cabeceras("producto.consultar"))
    assert r.status_code == 403

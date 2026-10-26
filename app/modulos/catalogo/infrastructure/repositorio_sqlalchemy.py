"""Adaptador SQLAlchemy de CatalogoRepository (esquema `inventario`).

TODO (B4 · Damx0611): implementar `listar_categorias` contra inventario.categoria y conectarlo a
GET /categorias (esqueleto andante del Sprint 1). Prueba de integración en
tests/integration/catalogo/ contra PostGIS (docker compose o el servicio de CI).
"""

from typing import Any

from sqlalchemy.orm import Session


class CatalogoRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_categorias(self, solo_activas: bool) -> list[Any]:
        raise NotImplementedError

    def listar_unidades(self) -> list[Any]:
        raise NotImplementedError

    def obtener_producto(self, producto_id: Any) -> Any | None:
        raise NotImplementedError

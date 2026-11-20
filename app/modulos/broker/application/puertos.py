"""Puertos del broker. Los adaptadores SQLAlchemy viven en infrastructure/."""

from collections.abc import Callable
from typing import Protocol

from app.modulos.broker.domain.modelo import ConteoCola, Fallo, Trabajo


class ColaRepository(Protocol):
    """Cola priorizada de trabajos."""

    def reclamar(self, limite: int, paso_envejecimiento_s: int) -> list[Trabajo]:
        """Toma hasta `limite` trabajos disponibles por prioridad efectiva, sin esperar los ya tomados por otro."""
        ...

    def ejecutar_aislado(self, accion: Callable[[], None]) -> Exception | None:
        """Ejecuta la acción en un punto de guardado; si falla, deshace solo esa acción y devuelve el error."""
        ...

    def marcar_hecho(self, trabajo_id: int) -> None: ...

    def marcar_fallo(self, trabajo_id: int, fallo: Fallo, error: str) -> None: ...

    def contar(self) -> list[ConteoCola]: ...


class NotificacionRepository(Protocol):
    """Bandeja de notificaciones que produce el manejador de alertas."""

    def registrar(self, trabajo: Trabajo, producto_id: str | None, mensaje: str) -> None: ...

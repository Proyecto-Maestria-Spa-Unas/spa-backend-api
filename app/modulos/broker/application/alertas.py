"""Manejador de `alerta_stock`: convierte el evento del outbox en una notificación legible."""

from app.modulos.broker.application.puertos import NotificacionRepository
from app.modulos.broker.domain.modelo import Trabajo

ESTADOS_ALERTA = frozenset({"AGOTADO", "BAJO_STOCK"})
LARGO_MAXIMO_MENSAJE = 280


class NotificarAlertaStock:
    def __init__(self, notificaciones: NotificacionRepository) -> None:
        self._notificaciones = notificaciones

    def __call__(self, trabajo: Trabajo) -> None:
        datos = trabajo.payload
        estado = str(datos.get("estado", ""))
        if estado not in ESTADOS_ALERTA:
            raise ValueError(f"Alerta de stock con estado no válido: {estado or 'vacío'}")

        nombre = str(datos.get("nombre") or datos.get("codigo") or "Producto")
        if estado == "AGOTADO":
            detalle = "agotado"
        else:
            detalle = f"bajo el mínimo ({datos.get('saldo')} de {datos.get('stock_minimo')})"

        producto = datos.get("producto_id")
        mensaje = f"{nombre}: {detalle}"[:LARGO_MAXIMO_MENSAJE]
        self._notificaciones.registrar(trabajo, str(producto) if producto else None, mensaje)

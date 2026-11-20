"""Caso de uso: procesar un lote de la cola en orden de prioridad efectiva."""

from collections.abc import Callable, Mapping
from functools import partial

from app.modulos.broker.application.puertos import ColaRepository
from app.modulos.broker.domain.modelo import (
    PASO_ENVEJECIMIENTO_S,
    EstadoTrabajo,
    Fallo,
    ResumenProcesamiento,
    Trabajo,
    registrar_fallo,
)

Manejador = Callable[[Trabajo], None]

LARGO_MAXIMO_ERROR = 500


class ProcesarCola:
    def __init__(self, cola: ColaRepository, manejadores: Mapping[str, Manejador]) -> None:
        self._cola = cola
        self._manejadores = manejadores

    def ejecutar(self, limite: int) -> ResumenProcesamiento:
        hechos = reintentos = fallidos = 0
        trabajos = self._cola.reclamar(limite, PASO_ENVEJECIMIENTO_S)
        for trabajo in trabajos:
            manejador = self._manejadores.get(trabajo.tipo)
            if manejador is None:
                # Sin manejador, reintentar no sirve: pasa directo a la cola de fallidos.
                fallo = Fallo(intentos=trabajo.intentos + 1, estado=EstadoTrabajo.FALLIDO, reintentar_en_s=None)
                self._cola.marcar_fallo(trabajo.id, fallo, f"Tipo de trabajo sin manejador: {trabajo.tipo}")
                fallidos += 1
                continue

            error = self._cola.ejecutar_aislado(partial(manejador, trabajo))
            if error is None:
                self._cola.marcar_hecho(trabajo.id)
                hechos += 1
                continue

            fallo = registrar_fallo(trabajo)
            detalle = f"{type(error).__name__}: {error}"[:LARGO_MAXIMO_ERROR]
            self._cola.marcar_fallo(trabajo.id, fallo, detalle)
            if fallo.estado is EstadoTrabajo.FALLIDO:
                fallidos += 1
            else:
                reintentos += 1

        return ResumenProcesamiento(tomados=len(trabajos), hechos=hechos, reintentos=reintentos, fallidos=fallidos)

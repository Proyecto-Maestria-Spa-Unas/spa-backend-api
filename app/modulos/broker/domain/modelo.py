"""Modelo del broker: trabajos asíncronos con prioridad, envejecimiento y reintentos (#75).

Reglas:
- Prioridad 1 alta, 2 normal, 3 baja.
- Envejecimiento: cada `PASO_ENVEJECIMIENTO_S` de espera la prioridad efectiva sube un nivel,
  sin pasar de ALTA. Así un trabajo de prioridad baja nunca espera indefinidamente (sin inanición).
- Reintentos con espera exponencial (30 s, 60 s, 120 s... con tope de una hora).
  Al agotar `max_intentos` el trabajo queda FALLIDO (cola de fallidos).

La consulta de spa-database ordena con la misma fórmula de `prioridad_efectiva`.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any

TIPO_ALERTA_STOCK = "alerta_stock"

PASO_ENVEJECIMIENTO_S = 300
ESPERA_BASE_S = 30
ESPERA_MAXIMA_S = 3600


class Prioridad(IntEnum):
    ALTA = 1
    NORMAL = 2
    BAJA = 3


class EstadoTrabajo(StrEnum):
    PENDIENTE = "PENDIENTE"
    HECHO = "HECHO"
    FALLIDO = "FALLIDO"


@dataclass(frozen=True, slots=True)
class Trabajo:
    id: int
    tipo: str
    prioridad: Prioridad
    payload: dict[str, Any]
    intentos: int
    max_intentos: int
    creado_en: datetime


@dataclass(frozen=True, slots=True)
class Fallo:
    """Resultado de un intento fallido: cuántos intentos lleva y a qué estado pasa."""

    intentos: int
    estado: EstadoTrabajo
    reintentar_en_s: int | None


@dataclass(frozen=True, slots=True)
class ResumenProcesamiento:
    tomados: int
    hechos: int
    reintentos: int
    fallidos: int


@dataclass(frozen=True, slots=True)
class ConteoCola:
    estado: EstadoTrabajo
    prioridad: Prioridad
    cantidad: int


def prioridad_efectiva(prioridad: int, espera_s: float, paso_s: int = PASO_ENVEJECIMIENTO_S) -> int:
    """Prioridad con envejecimiento: sube un nivel por cada `paso_s` de espera, sin pasar de ALTA."""
    if paso_s <= 0:
        raise ValueError("El paso de envejecimiento debe ser positivo")
    niveles = int(max(espera_s, 0) // paso_s)
    return max(int(Prioridad.ALTA), prioridad - niveles)


def espera_reintento(intentos: int, base_s: int = ESPERA_BASE_S, maximo_s: int = ESPERA_MAXIMA_S) -> int:
    """Espera exponencial antes del siguiente intento. `intentos` incluye el fallo actual (>= 1)."""
    if intentos < 1:
        raise ValueError("La espera se calcula a partir del primer fallo")
    return int(min(maximo_s, base_s * 2 ** (intentos - 1)))


def registrar_fallo(trabajo: Trabajo) -> Fallo:
    """Decide si el trabajo se reintenta más tarde o pasa a la cola de fallidos."""
    intentos = trabajo.intentos + 1
    if intentos >= trabajo.max_intentos:
        return Fallo(intentos=intentos, estado=EstadoTrabajo.FALLIDO, reintentar_en_s=None)
    return Fallo(intentos=intentos, estado=EstadoTrabajo.PENDIENTE, reintentar_en_s=espera_reintento(intentos))

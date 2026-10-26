"""Modelo del dominio de movimientos. El movimiento es un libro mayor inmutable (kardex).

Se corrige con ANULACION, nunca con UPDATE ni DELETE (ADR-0003, DEC-06).
El saldo lo actualiza el trigger `trg_movimiento_aplicar` en la misma transacción del INSERT.
"""

from enum import StrEnum


class TipoMovimiento(StrEnum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    ANULACION = "ANULACION"

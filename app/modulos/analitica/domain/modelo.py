"""Modelo del dominio de analítica. Solo lectura: S4 nunca escribe en la base."""

from enum import StrEnum


class EstadoAlerta(StrEnum):
    BAJO_STOCK = "BAJO_STOCK"
    AGOTADO = "AGOTADO"


class AgrupacionConsumo(StrEnum):
    CATEGORIA = "categoria"
    PRODUCTO = "producto"
    DIA = "dia"

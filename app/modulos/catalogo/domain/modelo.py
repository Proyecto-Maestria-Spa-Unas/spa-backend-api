"""Modelo del dominio de catálogo. Sin FastAPI ni SQLAlchemy.

TODO (B3 · Damx0611): agregar la entidad Producto y las reglas RN-08..RN-11 como funciones
puras con pruebas de frontera en tests/unit/catalogo/. La base también las garantiza
(columna generada `estado`), pero el dominio debe poder razonar sin base.
"""

from enum import StrEnum


class EstadoInventario(StrEnum):
    DISPONIBLE = "DISPONIBLE"  # RN-08
    BAJO_STOCK = "BAJO_STOCK"  # RN-09
    AGOTADO = "AGOTADO"  # RN-10
    DESCONTINUADO = "DESCONTINUADO"  # RN-11


class Magnitud(StrEnum):
    CONTEO = "CONTEO"
    VOLUMEN = "VOLUMEN"
    MASA = "MASA"

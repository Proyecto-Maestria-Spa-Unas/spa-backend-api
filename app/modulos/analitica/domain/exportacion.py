"""X5 · Exportación de inventario y movimientos (RNF-10): conjuntos, formatos y nombre del archivo."""

from dataclasses import dataclass
from datetime import date

CONJUNTOS = ("inventario", "movimientos")
FORMATOS = {"csv": "text/csv", "parquet": "application/vnd.apache.parquet"}


@dataclass(frozen=True)
class ArchivoExportado:
    contenido: bytes
    tipo_mime: str
    nombre: str


def nombre_archivo(conjunto: str, formato: str, dia: date) -> str:
    """Por ejemplo `inventario-20261108.csv`; el día es el de Bogotá."""
    return f"{conjunto}-{dia:%Y%m%d}.{formato}"

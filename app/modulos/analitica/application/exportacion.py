"""X5 · GET /analitica/exportar: descarga del inventario o de los movimientos en CSV o Parquet (RNF-10)."""

from datetime import date

from app.compartido.errores import DatosInvalidos
from app.modulos.analitica.application.puertos import Exportador
from app.modulos.analitica.domain.exportacion import CONJUNTOS, FORMATOS, ArchivoExportado, nombre_archivo


class ExportarDatos:
    def __init__(self, exportador: Exportador) -> None:
        self._exportador = exportador

    def __call__(self, conjunto: str, formato: str, hoy: date) -> ArchivoExportado:
        errores = []
        if conjunto not in CONJUNTOS:
            errores.append({"campo": "conjunto", "mensaje": f"Debe ser uno de: {', '.join(CONJUNTOS)}"})
        if formato not in FORMATOS:
            errores.append({"campo": "formato", "mensaje": f"Debe ser uno de: {', '.join(FORMATOS)}"})
        if errores:
            raise DatosInvalidos("El conjunto o el formato de la exportación no son válidos", errors=errores)
        return ArchivoExportado(
            contenido=self._exportador.exportar(conjunto, formato),
            tipo_mime=FORMATOS[formato],
            nombre=nombre_archivo(conjunto, formato, hoy),
        )

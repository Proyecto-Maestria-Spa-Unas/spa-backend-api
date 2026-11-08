"""X7 · Kardex valorizado por costo promedio ponderado (DEC-11, política de A3).

Las salidas se muestran valoradas al promedio vigente (A3 §3): costo unitario = promedio y
costo total = cantidad × promedio, igual que la tabla del ejemplo de A3.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.compartido.errores import DatosInvalidos, RecursoNoExiste
from app.modulos.analitica.application.puertos import ConsultasAnaliticas
from app.modulos.analitica.domain.modelo import LineaKardex, ProductoReferencia


@dataclass(frozen=True)
class ResultadoKardex:
    producto: ProductoReferencia
    lineas: list[LineaKardex]
    saldo_final: Decimal
    valor_final: Decimal


class ConsultarKardex:
    def __init__(self, consultas: ConsultasAnaliticas) -> None:
        self._consultas = consultas

    def __call__(self, producto_id: UUID, desde: date | None, hasta: date | None) -> ResultadoKardex:
        if desde is not None and hasta is not None and desde > hasta:
            raise DatosInvalidos(
                "La fecha 'desde' no puede ser posterior a 'hasta'",
                errors=[{"campo": "desde", "mensaje": "Debe ser anterior o igual a 'hasta'"}],
            )
        producto = self._consultas.producto(producto_id)
        if producto is None:
            raise RecursoNoExiste("El producto no existe")

        lineas = self._consultas.kardex(producto_id, desde, hasta)
        # Saldo al cierre del rango: la última línea del rango o, si no hubo movimientos en él,
        # el último movimiento anterior a 'hasta'.
        ultima = lineas[-1] if lineas else self._consultas.ultima_linea_kardex(producto_id, hasta)
        return ResultadoKardex(
            producto=producto,
            lineas=lineas,
            saldo_final=ultima.saldo if ultima else Decimal("0.000"),
            valor_final=ultima.valor_saldo if ultima else Decimal("0.0000"),
        )

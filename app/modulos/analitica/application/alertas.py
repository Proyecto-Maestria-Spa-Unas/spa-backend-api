"""Casos de uso de alertas de stock (HU-10, HU-11, RF-18). Solo lectura."""

from app.modulos.analitica.application.puertos import ConsultasAnaliticas
from app.modulos.analitica.domain.modelo import Alerta, EstadoAlerta, ResumenAlertas


class ListarAlertas:
    def __init__(self, consultas: ConsultasAnaliticas) -> None:
        self._consultas = consultas

    def ejecutar(self, estado: EstadoAlerta | None = None) -> list[Alerta]:
        return self._consultas.alertas(estado)


class ConsultarResumenAlertas:
    def __init__(self, consultas: ConsultasAnaliticas) -> None:
        self._consultas = consultas

    def ejecutar(self) -> ResumenAlertas:
        return self._consultas.resumen_alertas()

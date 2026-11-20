"""Esquemas HTTP del broker (#75)."""

from pydantic import BaseModel, Field

from app.modulos.broker.domain.modelo import EstadoTrabajo, Prioridad


class ResumenProcesamiento(BaseModel):
    tomados: int = Field(examples=[3], description="Trabajos tomados de la cola en este lote")
    hechos: int = Field(examples=[2])
    reintentos: int = Field(examples=[1], description="Fallaron y vuelven a la cola con espera exponencial")
    fallidos: int = Field(examples=[0], description="Agotaron sus intentos: quedan en la cola de fallidos")


class ConteoCola(BaseModel):
    estado: EstadoTrabajo
    prioridad: Prioridad = Field(description="1 alta · 2 normal · 3 baja")
    cantidad: int = Field(examples=[4])


class MetricasCola(BaseModel):
    pendientes: int = Field(examples=[4])
    fallidos: int = Field(examples=[0])
    detalle: list[ConteoCola]

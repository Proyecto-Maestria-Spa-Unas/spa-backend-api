"""Tipos del contrato: cantidades y costos viajan como texto decimal ("12.500") para no perder precisión."""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

Cantidad = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.3f}", return_type=str, when_used="json")]
Costo = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.4f}", return_type=str, when_used="json")]

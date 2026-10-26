"""Paginación común: `?page=1&size=20` (máximo 100) → `{items, total, page, size}`."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel


class Pagina[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int


@dataclass(frozen=True, slots=True)
class ParametrosPagina:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def _parametros(
    page: Annotated[int, Query(ge=1, description="Página, desde 1")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Tamaño de página, máximo 100")] = 20,
) -> ParametrosPagina:
    return ParametrosPagina(page=page, size=size)


Paginacion = Annotated[ParametrosPagina, Depends(_parametros)]

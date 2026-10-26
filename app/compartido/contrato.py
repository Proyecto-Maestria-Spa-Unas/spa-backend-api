"""Piezas del contrato OpenAPI comunes a los 4 servicios."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field


class ErrorCampo(BaseModel):
    campo: str
    mensaje: str


class Problema(BaseModel):
    """Cuerpo `application/problem+json` (RFC 9457) con `code` estable."""

    type: str
    title: str
    status: int
    detail: str
    code: str = Field(examples=["SIN_PERMISO"])
    errors: list[ErrorCampo] = []


REF_PROBLEMA = {"$ref": "#/components/schemas/Problema"}


def _r(descripcion: str) -> dict[str, Any]:
    return {"description": descripcion, "content": {"application/problem+json": {"schema": REF_PROBLEMA}}}


RESPUESTAS_PROTEGIDAS: dict[int | str, dict[str, Any]] = {
    401: _r("NO_AUTENTICADO: falta el token o está vencido"),
    403: _r("SIN_PERMISO: el rol no tiene el permiso del endpoint"),
    422: _r("DATOS_INVALIDOS: campos faltantes o fuera de regla"),
    501: _r("NO_IMPLEMENTADO: definido en el contrato, pendiente de implementar"),
}


def respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    """Agrega respuestas de error del dominio a las protegidas: `responses=respuestas(404, 409)`."""
    extra = {
        404: _r("RECURSO_NO_EXISTE"),
        409: _r("Conflicto de regla de negocio (ver `code`)"),
        412: _r("VERSION_CONFLICTO: If-Match no coincide con la versión actual"),
    }
    return {**RESPUESTAS_PROTEGIDAS, **{c: extra[c] for c in codigos}}


def id_operacion(ruta: APIRoute) -> str:
    """operationId = nombre de la función (`listar_categorias`): legible para los clientes del frontend."""
    return ruta.name


def instalar_openapi(app: FastAPI) -> None:
    """Agrega Problema y ErrorCampo a components.schemas (las respuestas de error los referencian)."""

    def _openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        esquema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
        definiciones = Problema.model_json_schema(ref_template="#/components/schemas/{model}")
        extras = definiciones.pop("$defs", {})
        componentes = esquema.setdefault("components", {}).setdefault("schemas", {})
        componentes.update({"Problema": definiciones, **extras})
        app.openapi_schema = esquema
        return esquema

    app.openapi = _openapi  # type: ignore[method-assign]

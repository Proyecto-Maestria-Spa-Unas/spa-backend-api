"""Errores de dominio → `application/problem+json` con un `code` estable (sección 4).

Los casos de uso lanzan estas excepciones; nunca `HTTPException`. El frontend decide qué
mostrar según `code`, no según el texto.
"""

from http import HTTPStatus
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

MEDIA_PROBLEM = "application/problem+json"


class ErrorDominio(Exception):  # noqa: N818 - nombre del dominio en español
    code: ClassVar[str] = "ERROR_INTERNO"
    status: ClassVar[int] = 500
    title: ClassVar[str] = "Error interno"

    def __init__(self, detail: str | None = None, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        self.errors = errors or []


class CredencialesInvalidas(ErrorDominio):
    code, status, title = "CREDENCIALES_INVALIDAS", 401, "Correo o contraseña incorrectos"


class NoAutenticado(ErrorDominio):
    code, status, title = "NO_AUTENTICADO", 401, "Falta el token o no es válido"


class SinPermiso(ErrorDominio):
    code, status, title = "SIN_PERMISO", 403, "El rol no tiene permiso para esta operación"


class UsuarioInactivo(ErrorDominio):
    code, status, title = "USUARIO_INACTIVO", 403, "La cuenta está desactivada"


class RecursoNoExiste(ErrorDominio):
    code, status, title = "RECURSO_NO_EXISTE", 404, "El recurso no existe"


class CodigoDuplicado(ErrorDominio):
    code, status, title = "CODIGO_DUPLICADO", 409, "El código ya está registrado"


class StockInsuficiente(ErrorDominio):
    code, status, title = "STOCK_INSUFICIENTE", 409, "La salida supera el stock disponible"


class ProductoDescontinuado(ErrorDominio):
    code, status, title = "PRODUCTO_DESCONTINUADO", 409, "El producto está descontinuado"


class MovimientoYaAnulado(ErrorDominio):
    code, status, title = "MOVIMIENTO_YA_ANULADO", 409, "El movimiento ya fue anulado"


class VersionConflicto(ErrorDominio):
    code, status, title = "VERSION_CONFLICTO", 412, "Otro usuario modificó el recurso primero"


class DatosInvalidos(ErrorDominio):
    code, status, title = "DATOS_INVALIDOS", 422, "Los datos enviados no son válidos"


class NoImplementado(ErrorDominio):
    """Marcador del andamiaje: el endpoint existe en el contrato pero aún no tiene lógica."""

    code, status, title = "NO_IMPLEMENTADO", 501, "Endpoint definido en el contrato, pendiente de implementar"


def _problema(status: int, code: str, title: str, detail: str, errors: list[Any] | None = None) -> JSONResponse:
    cuerpo = {
        "type": f"https://spa-unas/errores/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "errors": errors or [],
    }
    return JSONResponse(cuerpo, status_code=status, media_type=MEDIA_PROBLEM)


_CODIGO_HTTP = {
    401: "NO_AUTENTICADO",
    403: "SIN_PERMISO",
    404: "RECURSO_NO_EXISTE",
    405: "METODO_NO_PERMITIDO",
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDominio)
    async def _dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
        return _problema(exc.status, exc.code, exc.title, exc.detail, exc.errors)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        errores = [{"campo": ".".join(str(p) for p in e["loc"]), "mensaje": e["msg"]} for e in exc.errors()]
        return _problema(422, DatosInvalidos.code, DatosInvalidos.title, "Revise los campos indicados", errores)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _CODIGO_HTTP.get(exc.status_code, "ERROR_HTTP")
        titulo = HTTPStatus(exc.status_code).phrase
        return _problema(exc.status_code, code, titulo, str(exc.detail))

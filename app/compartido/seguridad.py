"""Autenticación y autorización (RF-01, RNF-07).

- `emitir_token` lo usa S1 al iniciar sesión.
- `usuario_actual` decodifica el Bearer en cada request.
- `requiere(Permiso.X)` protege cada endpoint: sin el permiso responde 403 aunque el
  frontend haya ocultado la opción.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.compartido.config import get_settings
from app.compartido.errores import NoAutenticado, SinPermiso
from app.compartido.permisos import Permiso

_bearer = HTTPBearer(auto_error=False, description="JWT emitido por POST /api/v1/auth/login")


@dataclass(frozen=True, slots=True)
class Principal:
    """Quién hace la petición, tomado del JWT."""

    usuario_id: UUID
    rol: str
    permisos: frozenset[str]

    def tiene(self, permiso: Permiso) -> bool:
        return permiso.value in self.permisos


def emitir_token(usuario_id: UUID, rol: str, permisos: list[str]) -> tuple[str, int]:
    """Devuelve (token, segundos de vigencia)."""
    settings = get_settings()
    vigencia = settings.jwt_expires_minutes * 60
    ahora = datetime.now(UTC)
    claims = {
        "sub": str(usuario_id),
        "rol": rol,
        "permisos": sorted(permisos),
        "iat": ahora,
        "exp": ahora + timedelta(seconds=vigencia),
    }
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)
    return token, vigencia


def decodificar_token(token: str) -> Principal:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        return Principal(
            usuario_id=UUID(str(claims["sub"])),
            rol=str(claims.get("rol", "")),
            permisos=frozenset(str(p) for p in claims.get("permisos", [])),
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise NoAutenticado("El token está vencido o no es válido") from exc


def usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise NoAutenticado()
    return decodificar_token(credenciales.credentials)


UsuarioActual = Annotated[Principal, Depends(usuario_actual)]


def requiere(permiso: Permiso) -> Callable[[Principal], Principal]:
    """Uso: `principal: Annotated[Principal, Depends(requiere(Permiso.PRODUCTO_CREAR))]`."""

    def _verificar(principal: UsuarioActual) -> Principal:
        if not principal.tiene(permiso):
            raise SinPermiso(f"Se requiere el permiso {permiso.value}")
        return principal

    _verificar.__name__ = f"requiere_{permiso.name.lower()}"
    return _verificar

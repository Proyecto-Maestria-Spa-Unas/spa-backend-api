"""Adaptador de ProveedorIdentidad sobre la API de Supabase Auth.

Verificado contra el código fuente de supabase/auth (commit a7e97d6, 30-oct-2026):
- `POST {SUPABASE_URL}/auth/v1/token?grant_type=password` con `{"email", "password"}`.
- Éxito: 200 con `access_token` y `user.id`.
- Credenciales inválidas: 400 con el código `invalid_credentials`. El campo es `error_code`
  (formato anterior) o `code` (formato de la versión de API 2024-01-01).
Según la documentación de Supabase, la clave secreta viaja en la cabecera `apikey`.

Alta de cuentas (B6), verificado contra supabase/auth (commit 35307ce, 06-nov-2026, internal/api/admin.go):
- `POST {SUPABASE_URL}/auth/v1/admin/users` con `{"email", "password", "email_confirm"}`; éxito: 200 con el usuario.
- Correo ya registrado: 422 con el código `email_exists`. Contraseña débil: 422 con `weak_password`.
Las claves nuevas (`sb_secret_...`) van solo en `apikey`, sin `Authorization` (guía de migración de
claves de Supabase). No se ha probado contra un proyecto real.

La clave `SUPABASE_SECRET_KEY` salta RLS: no la exponga fuera de este archivo.
"""

from uuid import UUID

import httpx

from app.compartido.config import get_settings
from app.compartido.errores import CodigoDuplicado, DatosInvalidos, ErrorDominio

_CREDENCIALES_INVALIDAS = "invalid_credentials"
_CORREO_EXISTE = "email_exists"
_CLAVE_DEBIL = "weak_password"


class ProveedorIdentidadNoDisponible(ErrorDominio):
    """Supabase Auth no respondió como se esperaba. Se responde 500 sin exponer el detalle."""


class ProveedorSupabaseAuth:
    def __init__(self, url: str, clave_secreta: str, cliente: httpx.Client | None = None) -> None:
        if not url or not clave_secreta:
            raise ValueError("Faltan SUPABASE_URL o SUPABASE_SECRET_KEY")
        self._url = url.rstrip("/")
        self._clave = clave_secreta
        self._cliente = cliente or httpx.Client(timeout=10.0)

    @classmethod
    def desde_configuracion(cls) -> "ProveedorSupabaseAuth":
        settings = get_settings()
        clave = settings.supabase_secret_key.get_secret_value() if settings.supabase_secret_key else ""
        return cls(settings.supabase_url or "", clave)

    def verificar_credenciales(self, correo: str, contrasena: str) -> UUID | None:
        try:
            respuesta = self._cliente.post(
                f"{self._url}/auth/v1/token",
                params={"grant_type": "password"},
                headers={"apikey": self._clave},
                json={"email": correo, "password": contrasena},
            )
        except httpx.HTTPError as exc:
            raise ProveedorIdentidadNoDisponible("No se pudo contactar el servicio de autenticación") from exc

        if respuesta.status_code == httpx.codes.OK:
            return UUID(str(respuesta.json()["user"]["id"]))

        if respuesta.status_code == httpx.codes.BAD_REQUEST and _codigo_error(respuesta) == _CREDENCIALES_INVALIDAS:
            return None

        raise ProveedorIdentidadNoDisponible(
            f"Respuesta inesperada del servicio de autenticación (HTTP {respuesta.status_code})"
        )

    def crear_cuenta(self, correo: str, contrasena_temporal: str) -> UUID:
        """Crea la cuenta ya confirmada: la administradora la da de alta, no hay correo de verificación."""
        try:
            respuesta = self._cliente.post(
                f"{self._url}/auth/v1/admin/users",
                headers={"apikey": self._clave},
                json={"email": correo, "password": contrasena_temporal, "email_confirm": True},
            )
        except httpx.HTTPError as exc:
            raise ProveedorIdentidadNoDisponible("No se pudo contactar el servicio de autenticación") from exc

        if respuesta.status_code == httpx.codes.OK:
            return UUID(str(respuesta.json()["id"]))

        codigo = _codigo_error(respuesta)
        if respuesta.status_code == httpx.codes.UNPROCESSABLE_ENTITY and codigo == _CORREO_EXISTE:
            raise CodigoDuplicado("Ya existe una cuenta con ese correo")
        if respuesta.status_code == httpx.codes.UNPROCESSABLE_ENTITY and codigo == _CLAVE_DEBIL:
            raise DatosInvalidos("La contraseña temporal no cumple la política de contraseñas")

        raise ProveedorIdentidadNoDisponible(
            f"Respuesta inesperada del servicio de autenticación (HTTP {respuesta.status_code})"
        )


def _codigo_error(respuesta: httpx.Response) -> str | None:
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return None
    if not isinstance(cuerpo, dict):
        return None
    codigo = cuerpo.get("error_code") or cuerpo.get("code")
    return codigo if isinstance(codigo, str) else None

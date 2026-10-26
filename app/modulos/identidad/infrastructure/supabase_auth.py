"""Adaptador de ProveedorIdentidad sobre la API de Supabase Auth.

TODO (S1 · ivonnelizethmoreno-cloud): implementar con httpx contra
`{SUPABASE_URL}/auth/v1/token?grant_type=password` y `/auth/v1/admin/users`.
La clave `SUPABASE_SECRET_KEY` salta RLS: no la exponga fuera de este archivo.
"""

from uuid import UUID


class ProveedorSupabaseAuth:
    def verificar_credenciales(self, correo: str, contrasena: str) -> UUID | None:
        raise NotImplementedError

    def crear_cuenta(self, correo: str, contrasena_temporal: str) -> UUID:
        raise NotImplementedError

"""Caso de uso de recuperación de contraseña (X3)."""

from app.modulos.identidad.application.puertos import RecuperacionContrasena

MENSAJE_RECUPERACION = "Si el correo está registrado, recibirá un enlace para restablecer la contraseña."


class SolicitarRecuperacion:
    """POST /auth/recuperar (HU-01).

    Pide el envío del correo y no consulta si la cuenta existe ni está activa: la respuesta es la misma
    para cualquier correo, así nadie puede averiguar qué cuentas hay (RNF-07).
    """

    def __init__(self, recuperacion: RecuperacionContrasena) -> None:
        self._recuperacion = recuperacion

    def ejecutar(self, correo: str) -> str:
        self._recuperacion.solicitar_recuperacion(correo.strip())
        return MENSAJE_RECUPERACION

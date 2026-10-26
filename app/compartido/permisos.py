"""Los 13 permisos del sistema (sección 6 del documento de arquitectura).

Se siembran en `seguridad.permiso` (spa-database) y viajan en el JWT. Usar siempre estas
constantes; nunca escribir el texto del permiso a mano en un router.
"""

from enum import StrEnum


class Permiso(StrEnum):
    USUARIO_GESTIONAR = "usuario.gestionar"
    PRODUCTO_CONSULTAR = "producto.consultar"
    PRODUCTO_CREAR = "producto.crear"
    PRODUCTO_EDITAR = "producto.editar"
    PRODUCTO_CONFIGURAR_MINIMO = "producto.configurar_minimo"
    PRODUCTO_DESCONTINUAR = "producto.descontinuar"
    CATALOGO_ADMINISTRAR = "catalogo.administrar"
    MOVIMIENTO_REGISTRAR_ENTRADA = "movimiento.registrar_entrada"
    MOVIMIENTO_REGISTRAR_SALIDA = "movimiento.registrar_salida"
    MOVIMIENTO_CONSULTAR = "movimiento.consultar"
    MOVIMIENTO_ANULAR = "movimiento.anular"
    ALERTA_CONSULTAR = "alerta.consultar"
    ANALITICA_CONSULTAR = "analitica.consultar"

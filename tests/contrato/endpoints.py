"""Inventario de los 31 endpoints del contrato con una petición mínima válida.

Si agrega o cambia un endpoint, actualice esta tabla: test_cobertura_de_la_tabla falla si
falta alguno. El permiso de cada fila debe coincidir con la sección 6 del documento.
"""

from dataclasses import dataclass, field
from typing import Any

PRODUCTO = "11111111-1111-4111-8111-111111111111"
USUARIO = "22222222-2222-4222-8222-222222222222"
IDEMPOTENCIA = {"Idempotency-Key": "33333333-3333-4333-8333-333333333333"}

PUBLICO = "publico"
AUTENTICADO = "autenticado"


@dataclass(frozen=True)
class Caso:
    metodo: str
    ruta: str  # plantilla tal como la declara el router
    permiso: str
    url: str  # ruta concreta para la petición
    json: dict[str, Any] | None = None
    params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


CASOS: list[Caso] = [
    # S1 · Identidad
    Caso("POST", "/auth/login", PUBLICO, "/auth/login", {"correo": "a@spa.co", "contrasena": "12345678"}),
    Caso("GET", "/auth/me", AUTENTICADO, "/auth/me"),
    Caso("GET", "/usuarios", "usuario.gestionar", "/usuarios"),
    Caso(
        "POST",
        "/usuarios",
        "usuario.gestionar",
        "/usuarios",
        {
            "correo": "b@spa.co",
            "nombre_completo": "Ana Ruiz",
            "rol": "MANICURISTA",
            "contrasena_temporal": "Temporal123",
        },
    ),
    Caso("GET", "/usuarios/{usuario_id}", "usuario.gestionar", f"/usuarios/{USUARIO}"),
    Caso("PATCH", "/usuarios/{usuario_id}", "usuario.gestionar", f"/usuarios/{USUARIO}", {"rol": "GERENTE"}),
    Caso(
        "PATCH", "/usuarios/{usuario_id}/estado", "usuario.gestionar", f"/usuarios/{USUARIO}/estado", {"activo": False}
    ),
    Caso("GET", "/roles", "usuario.gestionar", "/roles"),
    # S2 · Catálogo
    Caso("GET", "/categorias", "producto.consultar", "/categorias"),
    Caso("POST", "/categorias", "catalogo.administrar", "/categorias", {"nombre": "Esmaltes"}),
    Caso("PATCH", "/categorias/{categoria_id}", "catalogo.administrar", "/categorias/1", {"activa": False}),
    Caso("GET", "/unidades-medida", "producto.consultar", "/unidades-medida"),
    Caso("GET", "/productos", "producto.consultar", "/productos", params={"estado": "BAJO_STOCK"}),
    Caso("GET", "/productos/{producto_id}", "producto.consultar", f"/productos/{PRODUCTO}"),
    Caso(
        "POST",
        "/productos",
        "producto.crear",
        "/productos",
        {"codigo": "ESM-001", "nombre": "Esmalte rojo", "categoria_id": 1, "unidad_medida_id": 1},
    ),
    Caso(
        "PATCH",
        "/productos/{producto_id}",
        "producto.editar",
        f"/productos/{PRODUCTO}",
        {"nombre": "Esmalte rojo 15 ml"},
        headers={"If-Match": "1"},
    ),
    Caso(
        "PUT",
        "/productos/{producto_id}/stock-minimo",
        "producto.configurar_minimo",
        f"/productos/{PRODUCTO}/stock-minimo",
        {"stock_minimo": "5"},
    ),
    Caso(
        "POST", "/productos/{producto_id}/descontinuar", "producto.descontinuar", f"/productos/{PRODUCTO}/descontinuar"
    ),
    Caso("POST", "/productos/{producto_id}/reactivar", "producto.descontinuar", f"/productos/{PRODUCTO}/reactivar"),
    # S3 · Movimientos
    Caso("GET", "/motivos-movimiento", "movimiento.consultar", "/motivos-movimiento", params={"tipo": "SALIDA"}),
    Caso(
        "POST",
        "/movimientos/entradas",
        "movimiento.registrar_entrada",
        "/movimientos/entradas",
        {"producto_id": PRODUCTO, "cantidad": "10", "motivo_codigo": "COMPRA"},
        headers=IDEMPOTENCIA,
    ),
    Caso(
        "POST",
        "/movimientos/salidas",
        "movimiento.registrar_salida",
        "/movimientos/salidas",
        {"producto_id": PRODUCTO, "cantidad": "2", "motivo_codigo": "CONSUMO_SERVICIO"},
        headers=IDEMPOTENCIA,
    ),
    Caso("GET", "/movimientos", "movimiento.consultar", "/movimientos"),
    Caso("GET", "/movimientos/{movimiento_id}", "movimiento.consultar", "/movimientos/1"),
    Caso(
        "POST",
        "/movimientos/{movimiento_id}/anulaciones",
        "movimiento.anular",
        "/movimientos/1/anulaciones",
        {"motivo": "Registro duplicado", "confirmacion": True},
        headers=IDEMPOTENCIA,
    ),
    # S4 · Alertas y analítica
    Caso("GET", "/alertas", "alerta.consultar", "/alertas"),
    Caso("GET", "/alertas/resumen", "alerta.consultar", "/alertas/resumen"),
    Caso("GET", "/analitica/tablero", "analitica.consultar", "/analitica/tablero"),
    Caso(
        "GET",
        "/analitica/consumo",
        "analitica.consultar",
        "/analitica/consumo",
        params={"desde": "2026-10-01", "hasta": "2026-10-31"},
    ),
    Caso("GET", "/analitica/cobertura", "analitica.consultar", "/analitica/cobertura"),
    Caso("GET", "/analitica/exportar", "analitica.consultar", "/analitica/exportar", params={"conjunto": "inventario"}),
]

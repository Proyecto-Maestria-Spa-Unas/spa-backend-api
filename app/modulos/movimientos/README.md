# S3 · Movimientos

**Responsable:** Damx0611 · **Revisa:** equipo-backend · **Contrato:** `docs/openapi/movimientos-v1.yaml`

Entradas, salidas, kardex, historial y anulación controlada (HU-06..HU-08, HU-11, HU-13 · RF-06..RF-10, RF-14, RF-15, RF-20).

## Endpoints (6)

| Método | Ruta | Permiso | Sprint |
|---|---|---|---|
| GET | `/motivos-movimiento` | movimiento.consultar | 3 |
| POST | `/movimientos/entradas` (exige `Idempotency-Key`) | movimiento.registrar_entrada | 3 |
| POST | `/movimientos/salidas` (exige `Idempotency-Key`) | movimiento.registrar_salida | 3 |
| GET | `/movimientos` | movimiento.consultar (Manicurista: solo los propios) | 3 |
| GET | `/movimientos/{id}` | movimiento.consultar | 3 |
| POST | `/movimientos/{id}/anulaciones` (exige `Idempotency-Key`) | movimiento.anular | 3 |

`DELETE /movimientos` no existe y responde 405 (ADR-0003).

## Reglas clave

* El movimiento es un **libro mayor inmutable**: solo INSERT. Se corrige con ANULACION.
* El saldo lo valida y actualiza el trigger `trg_movimiento_aplicar` (S0) en la misma transacción. El adaptador traduce sus errores a `StockInsuficiente`, `ProductoDescontinuado`, `MovimientoYaAnulado`.
* Un reintento con la misma `Idempotency-Key` devuelve el movimiento ya registrado, no uno nuevo.

## Tareas

* **Sprint 3:** los 6 endpoints, con pruebas de concurrencia (dos salidas simultáneas del último stock).

## Definición de terminado

Ver la plantilla de PR.

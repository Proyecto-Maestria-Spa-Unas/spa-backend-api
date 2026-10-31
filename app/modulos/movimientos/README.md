# S3 · Movimientos

**Responsable:** Damx0611 · **Revisa:** equipo-backend · **Contrato:** `docs/openapi/movimientos-v1.yaml`

Entradas, salidas, kardex, historial y anulación controlada (HU-06..HU-08, HU-11, HU-13 · RF-06..RF-10, RF-14, RF-15, RF-20).

## Endpoints (6)

| Método | Ruta | Permiso | Entrega · responsable |
|---|---|---|---|
| GET | `/motivos-movimiento` | movimiento.consultar | **Gleidy725 (X1)** |
| POST | `/movimientos/entradas` (exige `Idempotency-Key`) | movimiento.registrar_entrada | Entrega 2 |
| POST | `/movimientos/salidas` (exige `Idempotency-Key`) | movimiento.registrar_salida | Entrega 2 |
| GET | `/movimientos` | movimiento.consultar (Manicurista: solo los propios) | Entrega 2 |
| GET | `/movimientos/{id}` | movimiento.consultar | Entrega 2 |
| POST | `/movimientos/{id}/anulaciones` (exige `Idempotency-Key`) | movimiento.anular | Entrega 2 |

`DELETE /movimientos` no existe y responde 405 (ADR-0003).

## Reglas clave

* El movimiento es un **libro mayor inmutable**: solo INSERT. Se corrige con ANULACION.
* El saldo lo valida y actualiza el trigger `trg_movimiento_aplicar` (S0) en la misma transacción. El adaptador traduce sus errores a `StockInsuficiente`, `ProductoDescontinuado`, `MovimientoYaAnulado`.
* Un reintento con la misma `Idempotency-Key` devuelve el movimiento ya registrado, no uno nuevo.

* Las entradas por `COMPRA` llevan `costo_unitario` y `proveedor_id`: el trigger recalcula el **costo promedio ponderado** (DEC-11) y lo guarda en `costo_promedio_resultante`.

## Tareas

Las fechas exactas están en cada issue (etiqueta `plan-entregas`): B10 entradas y salidas, B11 historial y anulación, B12 cierre; X1 motivos (Gleidy725). Incluya la prueba de dos salidas simultáneas del último stock.

## Definición de terminado

Ver la plantilla de PR.

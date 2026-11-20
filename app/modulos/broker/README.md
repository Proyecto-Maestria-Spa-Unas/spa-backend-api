# S5 · Broker

**Issue:** #75 · **Migración:** `spa-database/supabase/migrations/20261120170000_broker_priorizacion.sql`

Cola de trabajos asíncronos con priorización sobre PostgreSQL (Supabase), sin extensiones.

## Endpoints (2)

| Método | Ruta | Acceso |
|---|---|---|
| POST | `/broker/procesar?limite=20` | Cabecera `X-Broker-Token` (workflow programado) |
| GET | `/broker/metricas` | `usuario.gestionar` (solo ADMINISTRADOR) |

## Reglas

* **Prioridad:** 1 alta · 2 normal · 3 baja.
* **Envejecimiento:** cada 5 minutos de espera la prioridad efectiva sube un nivel (sin inanición).
* **Consumo concurrente seguro:** `FOR UPDATE SKIP LOCKED`; dos consumidores nunca toman el mismo trabajo.
* **Reintentos:** espera exponencial 30 s, 60 s, 120 s... (tope 1 h). Al agotar `max_intentos` (5) queda `FALLIDO`.
* **Idempotencia:** `clave_idempotencia` única al encolar; una notificación por trabajo.
* **Outbox:** el trigger `trg_movimiento_encolar_alerta` encola `alerta_stock` en la misma transacción del movimiento:
  `AGOTADO` → prioridad 1; `BAJO_STOCK` (al cruzar el mínimo) → prioridad 2.

## Dónde va cada cosa

| Archivo | Contenido |
|---|---|
| `domain/modelo.py` | Prioridad, estados, envejecimiento, espera exponencial, decisión de reintento |
| `application/puertos.py` | `ColaRepository`, `NotificacionRepository` |
| `application/procesar.py` | Caso de uso `ProcesarCola` |
| `application/alertas.py` | Manejador `alerta_stock` |
| `infrastructure/repositorio_sqlalchemy.py` | SQL de la cola (SKIP LOCKED, puntos de guardado) |
| `api/router.py` | Endpoints |

## Configuración

* `BROKER_TOKEN` en Vercel (API) y como secreto del repositorio (workflow `broker.yml`). Sin él, `/broker/procesar` responde 503.
* `BROKER_API_URL` como variable del repositorio: base de la API, por ejemplo `https://<api>/api/v1`.

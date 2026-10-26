# S2 · Catálogo

**Responsable:** Damx0611 · **Revisa:** equipo-backend · **Contrato:** `docs/openapi/catalogo-v1.yaml`

Productos, categorías, unidades de medida, stock mínimo y descontinuación (HU-02..HU-05, HU-12 · RF-02..RF-05, RF-11, RF-12, RF-16, RF-19).

## Endpoints (11)

| Método | Ruta | Permiso | Sprint |
|---|---|---|---|
| GET | `/categorias` | producto.consultar | **1 (esqueleto andante)** |
| POST | `/categorias` | catalogo.administrar | 2 |
| PATCH | `/categorias/{id}` | catalogo.administrar | 2 |
| GET | `/unidades-medida` | producto.consultar | 2 |
| GET | `/productos` | producto.consultar | 2 |
| GET | `/productos/{id}` | producto.consultar | 2 |
| POST | `/productos` | producto.crear | 2 |
| PATCH | `/productos/{id}` (exige `If-Match`) | producto.editar | 2 |
| PUT | `/productos/{id}/stock-minimo` | producto.configurar_minimo | 2 |
| POST | `/productos/{id}/descontinuar` | producto.descontinuar | 2 |
| POST | `/productos/{id}/reactivar` | producto.descontinuar | 2 |

`DELETE /productos` no existe y responde 405 (RN-12).

## Dónde va cada cosa

| Archivo | Qué implementar |
|---|---|
| `domain/modelo.py` | **B3:** entidad `Producto` y reglas RN-08..RN-11 (estado) como funciones puras |
| `application/puertos.py` | `CatalogoRepository` con entidades del dominio |
| `application/*.py` | Casos de uso: `ListarCategorias`, `CrearProducto`, `DescontinuarProducto`... |
| `infrastructure/repositorio_sqlalchemy.py` | **B4:** `inventario.categoria`, `unidad_medida`, `producto` y la vista `v_inventario` |
| `api/router.py` | Reemplazar `raise NoImplementado()` |

Reglas de datos: S2 **lee** `stock_actual` pero nunca lo escribe (lo actualiza el trigger de S3). `POST /productos` con `cantidad_inicial` registra la entrada `SALDO_INICIAL` en la misma transacción.

## Tareas

* **Sprint 1 · B1:** levantar `docker compose up -d` con el esquema de spa-database y documentar cualquier ajuste en el README.
* **Sprint 1 · B3:** dominio del catálogo con pruebas de frontera en `tests/unit/catalogo/`.
* **Sprint 1 · B4:** `GET /categorias` de punta a punta, con prueba en `tests/integration/catalogo/`.
* **Sprint 2:** los 10 endpoints restantes.

## Definición de terminado

Ver la plantilla de PR.

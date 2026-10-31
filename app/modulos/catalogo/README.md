# S2 · Catálogo

**Responsable:** Damx0611 · **Revisa:** equipo-backend · **Contrato:** `docs/openapi/catalogo-v1.yaml`

Productos, categorías, unidades de medida, stock mínimo y descontinuación (HU-02..HU-05, HU-12 · RF-02..RF-05, RF-11, RF-12, RF-16, RF-19).

## Endpoints (14)

| Método | Ruta | Permiso | Entrega · responsable |
|---|---|---|---|
| GET | `/categorias` | producto.consultar | Entrega 1 |
| POST | `/categorias` | catalogo.administrar | Entrega 1 |
| PATCH | `/categorias/{id}` | catalogo.administrar | Entrega 1 |
| GET | `/unidades-medida` | producto.consultar | Entrega 1 |
| GET | `/productos` | producto.consultar | Entrega 1 |
| GET | `/productos/{id}` | producto.consultar | Entrega 1 |
| POST | `/productos` | producto.crear | Entrega 1 |
| PATCH | `/productos/{id}` (exige `If-Match`) | producto.editar | Entrega 1 |
| PUT | `/productos/{id}/stock-minimo` | producto.configurar_minimo | Entrega 1 |
| POST | `/productos/{id}/descontinuar` | producto.descontinuar | Entrega 1 |
| POST | `/productos/{id}/reactivar` | producto.descontinuar | Entrega 1 |

| GET | `/proveedores` | producto.consultar | **Gleidy725 (X2)** |
| POST | `/proveedores` (NIT único, ubicación) | catalogo.administrar | **Gleidy725 (X2)** |
| PATCH | `/proveedores/{id}` | catalogo.administrar | **Gleidy725 (X2)** |

`DELETE /productos` no existe y responde 405 (RN-12).

**Proveedores (Gleidy725):** viven en este módulo pero en archivos propios (`application/proveedores.py`, `infrastructure/proveedores_sql.py`). La ubicación se guarda en `geography(Point, 4326)` (PostGIS); conviértala con `ST_MakePoint(longitud, latitud)` y léala con `ST_X`/`ST_Y`.

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

Las fechas exactas están en cada issue (etiqueta `plan-entregas`): B1 Docker, B3 dominio, B4 categorías y unidades, B8 consulta de productos, B9 escritura del catálogo, X2 proveedores (Gleidy725).

## Definición de terminado

Ver la plantilla de PR.

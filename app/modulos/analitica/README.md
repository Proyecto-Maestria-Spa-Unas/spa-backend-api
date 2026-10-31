# S4 · Alertas y analítica

**Responsable:** ivonnelizethmoreno-cloud · **Revisa:** equipo-backend y equipo-analistas · **Contrato:** `docs/openapi/analitica-v1.yaml`

Alertas de bajo stock y agotados, tablero de decisiones, consumo, cobertura y exportación (HU-10, HU-11 · RF-14, RF-17, RF-18, RF-19 · RNF-10). **Solo lectura.**

## Endpoints (8)

| Método | Ruta | Permiso | Entrega · responsable |
|---|---|---|---|
| GET | `/alertas` | alerta.consultar | **Estefa44445 (X4)** |
| GET | `/alertas/resumen` | alerta.consultar | **Estefa44445 (X4)** |
| GET | `/analitica/tablero` | analitica.consultar | ivonnelizethmoreno-cloud (B14) |
| GET | `/analitica/consumo` | analitica.consultar | ivonnelizethmoreno-cloud (B14) |
| GET | `/analitica/cobertura` | analitica.consultar | ivonnelizethmoreno-cloud (B14) |
| GET | `/analitica/kardex` | analitica.consultar | ivonnelizethmoreno-cloud (X7) |
| GET | `/analitica/proveedores-cercanos` (GeoJSON) | alerta.consultar | **Estefa44445 (X6)** |
| GET | `/analitica/exportar` | analitica.consultar | **Estefa44445 (X5)** |

## Dónde va cada cosa

| Archivo | Qué implementar |
|---|---|
| `infrastructure/consultas_sql.py` | SELECT sobre las vistas `v_alerta_stock`, `v_inventario` y la tabla `movimiento` |
| `infrastructure/exportador_duckdb.py` (crear) | CSV y Parquet con DuckDB en memoria |
| `application/*.py` | Cálculo de cobertura (stock ÷ consumo diario promedio de 30 días) y del tablero |

Al implementar el tablero o la exportación, agregue `pandas` y `duckdb` **a la vez** en `pyproject.toml` y `requirements.txt` (la prueba `tests/test_dependencias.py` lo exige).

* **Kardex valorizado (X7):** método costo promedio ponderado (NIIF para Pymes, Sección 13), leído de `costo_promedio_resultante` de cada movimiento.
* **Proveedores cercanos (X6):** función de S0 basada en `ST_DWithin` sobre `geography`; la respuesta es GeoJSON (RFC 7946) y la abre Leaflet, QGIS o ArcGIS sin conversión.
* `valor_inventario` del tablero = Σ stock_actual × costo_promedio.

## Definición de terminado

Ver la plantilla de PR.

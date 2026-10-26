# S4 · Alertas y analítica

**Responsable:** ivonnelizethmoreno-cloud · **Revisa:** equipo-backend y equipo-analistas · **Contrato:** `docs/openapi/analitica-v1.yaml`

Alertas de bajo stock y agotados, tablero de decisiones, consumo, cobertura y exportación (HU-10, HU-11 · RF-14, RF-17, RF-18, RF-19 · RNF-10). **Solo lectura.**

## Endpoints (6)

| Método | Ruta | Permiso | Sprint |
|---|---|---|---|
| GET | `/alertas` | alerta.consultar | 3 |
| GET | `/alertas/resumen` | alerta.consultar | 3 |
| GET | `/analitica/tablero` | analitica.consultar | 4 |
| GET | `/analitica/consumo` | analitica.consultar | 4 |
| GET | `/analitica/cobertura` | analitica.consultar | 4 |
| GET | `/analitica/exportar` | analitica.consultar | 4 |

## Dónde va cada cosa

| Archivo | Qué implementar |
|---|---|
| `infrastructure/consultas_sql.py` | SELECT sobre las vistas `v_alerta_stock`, `v_inventario` y la tabla `movimiento` |
| `infrastructure/exportador_duckdb.py` (crear) | CSV y Parquet con DuckDB en memoria |
| `application/*.py` | Cálculo de cobertura (stock ÷ consumo diario promedio de 30 días) y del tablero |

Al implementar el tablero o la exportación, agregue `pandas` y `duckdb` **a la vez** en `pyproject.toml` y `requirements.txt` (la prueba `tests/test_dependencias.py` lo exige).

`valor_inventario` responde `null` mientras el grupo no decida DEC-11 (costo promedio ponderado).

## Definición de terminado

Ver la plantilla de PR.

# Arquitectura · Monolito modular hexagonal (ADR-0009)

```
app/
├── main.py                     # Crea FastAPI e incluye los 4 routers bajo /api/v1
├── compartido/                 # Transversal (no importa ningún módulo)
│   ├── config.py               # Pydantic Settings: DB_URL, JWT_*, CORS_ORIGINS, SUPABASE_*
│   ├── db.py                   # Engine (NullPool, prepare_threshold=None) y get_session por request
│   ├── seguridad.py            # emitir_token, usuario_actual y requiere(Permiso.X)
│   ├── permisos.py             # Los 13 permisos (StrEnum)
│   ├── errores.py              # Errores de dominio → application/problem+json con code
│   ├── contrato.py             # Respuestas de error comunes y operationId legibles
│   ├── paginacion.py           # ?page&size → {items,total,page,size}
│   ├── tipos.py                # Cantidad y Costo: decimales que viajan como texto
│   └── salud.py                # /health y /health/ready
└── modulos/
    ├── identidad/              # S1
    ├── catalogo/               # S2
    ├── movimientos/            # S3
    └── analitica/              # S4
        ├── domain/             # Reglas puras (sin FastAPI, SQLAlchemy ni Pydantic)
        ├── application/        # Casos de uso + puertos (Protocol)
        ├── infrastructure/     # Adaptadores: SQLAlchemy, Supabase Auth, DuckDB
        └── api/                # router.py + esquemas.py (el contrato)
```

## Reglas (las verifica `tests/test_arquitectura.py` con import-linter)

1. Los 4 módulos son **independientes**: ninguno importa a otro. Si S4 necesita datos de S2, los lee de las vistas que publica S0 (`v_inventario`, `v_alerta_stock`).
2. Capas dentro de cada módulo: `api → infrastructure → application → domain`. Una capa solo importa capas inferiores.
3. `domain/` no importa `fastapi`, `sqlalchemy`, `pydantic` ni `app.compartido`.
4. `compartido/` no importa `app.modulos`.

## Cómo implementar un endpoint (ejemplo: GET /categorias)

1. **Dominio** `catalogo/domain/`: entidad `Categoria` (dataclass) y reglas.
2. **Puerto** `catalogo/application/puertos.py`: `CatalogoRepository.listar_categorias()` devuelve entidades del dominio.
3. **Caso de uso** `catalogo/application/listar_categorias.py`: recibe el puerto por constructor.
4. **Adaptador** `catalogo/infrastructure/repositorio_sqlalchemy.py`: consulta `inventario.categoria` con la `Session`.
5. **Router** `catalogo/api/router.py`: reemplazar `raise NoImplementado()` por:

```python
def listar_categorias(_: Consultor, session: Annotated[Session, Depends(get_session)]) -> list[Categoria]:
    caso = ListarCategorias(CatalogoRepositorySQL(session))
    return [Categoria.model_validate(c, from_attributes=True) for c in caso.ejecutar()]
```

6. **Pruebas**: unitaria del caso de uso con un repositorio falso en `tests/unit/catalogo/`, e integración contra PostGIS en `tests/integration/catalogo/` marcada con `@pytest.mark.integracion`.

## Errores

Los casos de uso lanzan errores de `app.compartido.errores` (`StockInsuficiente`, `CodigoDuplicado`...). Nunca `HTTPException`. El manejador común los convierte en problem+json con su `code`.

## Base de datos

El esquema es propiedad de **S0 · Datos** (`spa-database`). Este repositorio no ejecuta DDL. Cada módulo solo lee y escribe sus tablas (sección 3 del documento de arquitectura). En el Sprint 4 cada servicio tendrá su propio rol de base con permisos mínimos.

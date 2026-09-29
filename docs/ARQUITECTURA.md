# Arquitectura hexagonal (puertos y adaptadores)

```
app/
├── domain/              # Entidades y reglas puras: Producto, Movimiento, EstadoInventario (RN-01..RN-14)
├── application/
│   ├── ports/           # Interfaces: ProductoRepository, MovimientoRepository, UsuarioRepository, PasswordHasher
│   └── <caso_uso>.py    # RegistrarSalida, RegistrarEntrada, DescontinuarProducto, ConsultarAlertas...
├── infrastructure/
│   ├── db/              # Adaptadores SQLAlchemy → PostgreSQL/Supabase (implementan los puertos)
│   └── security/        # JWT (python-jose), hashing de contraseñas, RBAC
├── api/v1/              # Adaptadores de entrada HTTP (routers FastAPI + esquemas Pydantic)
└── core/                # Configuración (pydantic-settings), logging, dependencias
```

Regla de dependencias: `api → application → domain` y `infrastructure → application/domain`.
El dominio no importa FastAPI, SQLAlchemy ni Pydantic.

El esquema de base de datos es propiedad del repositorio `spa-database` (migraciones Supabase);
este servicio **no** crea ni altera tablas.

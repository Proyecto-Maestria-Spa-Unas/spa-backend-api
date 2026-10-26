"""Los 4 servicios de dominio. Ninguno importa a otro (lo verifica import-linter).

Cada uno tiene 4 capas hexagonales:
    domain/          reglas puras, sin FastAPI ni SQLAlchemy
    application/     casos de uso y puertos (interfaces)
    infrastructure/  adaptadores: SQLAlchemy, Supabase Auth, DuckDB...
    api/             router, esquemas Pydantic y dependencias HTTP
"""

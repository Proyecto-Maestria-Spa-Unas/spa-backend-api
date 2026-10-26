"""Conexión a PostgreSQL (Supabase) con SQLAlchemy 2.

- `prepare_threshold=None`: el pooler de transacciones de Supabase (Supavisor, puerto 6543)
  no admite sentencias preparadas del lado del servidor.
- `NullPool`: en Vercel cada invocación es efímera; el pool lo mantiene Supavisor, no la función.
- Una sesión por request (`get_session`), con commit al final y rollback ante cualquier error.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.compartido.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.db_url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None, "connect_timeout": 5},
    )


@lru_cache
def _fabrica_sesiones() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: `session: Session = Depends(get_session)`."""
    session = _fabrica_sesiones()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def base_disponible() -> bool:
    """SELECT 1 contra la base. Lo usa /health/ready."""
    try:
        with get_engine().connect() as conexion:
            conexion.execute(text("select 1"))
    except Exception:
        return False
    return True

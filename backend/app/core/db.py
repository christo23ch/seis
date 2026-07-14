"""Capa de acceso a datos. JSONB en PostgreSQL con variante JSON para SQLite (tests)."""
from collections.abc import Generator

from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Tipo JSON portable: JSONB en Postgres, JSON en el resto (P8: módulos sustituibles).
PortableJSON = JSON().with_variant(JSONB(), "postgresql")

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

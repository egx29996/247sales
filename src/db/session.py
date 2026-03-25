"""Database engine and session management."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base

_engine = None
_SessionLocal = None


def init_db(database_url: str) -> None:
    """Initialize the database engine and create tables."""
    global _engine, _SessionLocal
    _engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        echo=False,
    )
    _SessionLocal = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    """Return a new database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal()

"""Single shared synchronous SQLAlchemy engine for legacy sync API routes (psycopg2 / default ``postgresql://``)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def _sync_database_url(url: str) -> str:
    u = (url or "").strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    if "+asyncpg" in u:
        u = u.replace("postgresql+asyncpg://", "postgresql://", 1)
    return u


def _ensure_engine() -> None:
    global _engine, _session_factory
    if _engine is None:
        _engine = create_engine(_sync_database_url(settings.database_url), pool_pre_ping=True)
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@contextmanager
def sync_session() -> Generator[Session, None, None]:
    _ensure_engine()
    assert _session_factory is not None
    with _session_factory() as session:
        yield session

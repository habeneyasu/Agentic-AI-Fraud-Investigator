"""Async SQLAlchemy engine (PostgreSQL + asyncpg); tables created on startup via ``create_all``."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.models.db_base import Base

# Import ORM modules so ``Base.metadata`` is populated before ``create_all``.
import app.models.orm_tables  # noqa: F401

logger = get_logger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _async_postgres_url(url: str) -> tuple[str, dict[str, Any]]:
    """Return asyncpg DSN and connect_args (honours ``sslmode`` query param)."""
    u = url.strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    parsed = urlparse(u)
    q: dict[str, str] = {}
    sslmode = ""
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        lk = k.lower()
        if lk == "sslmode":
            sslmode = (v or "").lower()
        elif lk in ("ssl", "channel_binding"):
            continue
        else:
            q[k] = v
    new_query = urlencode(list(q.items()))
    clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", new_query, ""))

    connect_args: dict[str, Any] = {}
    if sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True
    elif sslmode == "prefer":
        connect_args["ssl"] = "prefer"

    if "+asyncpg" not in clean and clean.startswith("postgresql://"):
        clean = clean.replace("postgresql://", "postgresql+asyncpg://", 1)
    return clean, connect_args


def _init_failure_message(exc: BaseException, target: str) -> str:
    text = str(exc).lower()
    name = type(exc).__name__
    if "password" in text or "authentication failed" in text or "invalidpassword" in name.lower():
        return (
            f"PostgreSQL authentication failed at {target} ({name}). "
            "Check DATABASE_URL user and password. SKIP_DATABASE_INIT=1 to run without ORM; "
            "REQUIRE_DATABASE=1 to fail startup."
        )
    if "refused" in text or name == "ConnectionRefusedError":
        return (
            f"PostgreSQL not reachable at {target} ({name}). "
            "Start the server and verify host/port. SKIP_DATABASE_INIT=1 or REQUIRE_DATABASE=1."
        )
    return f"PostgreSQL ORM init failed at {target} ({name}: {exc}). SKIP_DATABASE_INIT=1 or REQUIRE_DATABASE=1."


def _postgres_target_for_log(url: str) -> str:
    """Host:port for logs (no credentials)."""
    u = url.strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    try:
        p = urlparse(u)
        host = p.hostname or "?"
        port = p.port or 5432
        return f"{host}:{port}"
    except Exception:
        return "?"


async def init_database() -> bool:
    """Connect to Postgres and run ``create_all``. Returns False if skipped or on recoverable errors (unless REQUIRE_DATABASE)."""
    global _engine, _session_factory
    if _engine is not None:
        return True
    if settings.skip_database_init:
        logger.info("Database init skipped (SKIP_DATABASE_INIT is set)")
        return False

    dsn, connect_args = _async_postgres_url(settings.database_url)
    eng: Optional[AsyncEngine] = None
    try:
        eng = create_async_engine(
            dsn,
            echo=settings.debug,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _engine = eng
        eng = None
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
        logger.info(
            "SQLAlchemy ORM tables ensured (PostgreSQL)",
            tables=sorted(Base.metadata.tables.keys()),
        )
        return True
    except Exception as e:
        if eng is not None:
            await eng.dispose()
        target = _postgres_target_for_log(settings.database_url)
        msg = _init_failure_message(e, target)
        if settings.require_database:
            logger.error(msg)
            raise
        logger.info(msg)
        return False


async def shutdown_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError(
            "PostgreSQL ORM engine is not available. "
            "ORM init did not complete — check DATABASE_URL and that Postgres is running, "
            "or set SKIP_DATABASE_INIT=1."
        )
    return _engine


def is_orm_enabled() -> bool:
    """True if ``init_database()`` completed and sessions are available."""
    return _engine is not None


def session_maker() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError(
            "Database session factory is not available (PostgreSQL ORM init did not complete)."
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: ``async with`` session scope per request."""
    factory = session_maker()
    async with factory() as session:
        yield session

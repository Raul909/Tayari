"""
Database layer — async SQLAlchemy engine + session for Tayari.

Works with two backends, chosen entirely by the DATABASE_URL env var:

- **Local dev (default):** SQLite via aiosqlite — zero setup, a file on disk.
- **Production:** Neon (serverless Postgres) via asyncpg — durable, shared by
  the web dashboard and the mobile app through the same FastAPI backend.

Both the web app and the Flutter app talk to this backend over HTTP; neither
connects to the database directly (embedding DB credentials in a public web
bundle or a distributed APK would be unsafe). So a report submitted from a
phone lands in the *same* Neon database the dashboard reads from, and vice
versa — that is what "one database for both apps" means here.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _normalize_db_url(url: str) -> tuple[str, dict]:
    """
    Normalize a database URL for SQLAlchemy's async drivers and return the URL
    plus any connect_args it needs.

    Neon (and most managed Postgres) hand out a libpq-style URL like
    ``postgresql://user:pass@host/db?sslmode=require``. SQLAlchemy's async
    engine needs the ``+asyncpg`` driver, and asyncpg does not understand the
    libpq ``sslmode``/``channel_binding`` query params — TLS is passed via
    connect_args instead. We rewrite the URL accordingly so operators can paste
    the connection string Neon gives them verbatim into DATABASE_URL.
    """
    connect_args: dict = {}

    # Postgres → force the asyncpg driver.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):  # some providers use the shorter scheme
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    if url.startswith("postgresql+asyncpg://"):
        # Strip libpq-only query params; enable TLS via asyncpg's own flag.
        base, _, query = url.partition("?")
        libpq_ssl = any(
            tok.startswith(("sslmode", "channel_binding"))
            for tok in query.split("&")
        )
        url = base
        if libpq_ssl or query:
            connect_args["ssl"] = True

    # SQLite (default) needs no special handling beyond the aiosqlite driver,
    # which the default DATABASE_URL already specifies.
    return url, connect_args


_db_url, _connect_args = _normalize_db_url(settings.database_url)

engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,  # recycle stale Neon connections transparently
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables if they don't exist. Called once on startup."""
    # Import models so they're registered on Base.metadata before create_all.
    from app.models import db_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    backend = "Neon/Postgres" if "asyncpg" in _db_url else "SQLite"
    logger.info(f"   Database: {backend} ready ({_db_url.split('@')[-1]})")


async def close_db() -> None:
    """Dispose of the engine's connection pool on shutdown."""
    await engine.dispose()

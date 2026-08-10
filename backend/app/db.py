"""
Database layer — async SQLAlchemy engine + session for Tayari.

Works with two backends, chosen entirely by the DATABASE_URL env var:

- **Local dev (default):** SQLite via aiosqlite — zero setup, a file on disk.
- **Production:** Supabase (managed Postgres) via asyncpg — durable, shared by
  the web dashboard and the mobile app through the same FastAPI backend.

Both the web app and the Flutter app talk to this backend over HTTP; neither
connects to the database directly (embedding DB credentials in a public web
bundle or a distributed APK would be unsafe). So a report submitted from a
phone lands in the *same* Supabase database the dashboard reads from, and vice
versa — that is what "one database for both apps" means here.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
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
    # Guard: catch the common mistake of pasting a Supabase/Neon *REST API*
    # URL (https://…) instead of the Postgres *connection string*.  Without
    # this, SQLAlchemy throws a confusing "Can't load plugin: …:https".
    if url.startswith("https://") or url.startswith("http://"):
        raise ValueError(
            f"DATABASE_URL looks like an HTTP(S) URL, not a database "
            f"connection string.  Expected something like "
            f"'postgresql://user:pass@host:5432/db', got: {url[:80]}…"
        )

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
    """
    Yield a database session, turning connectivity failures into a clear 503.

    The failure surfaces as a raw `socket.gaierror` rather than a SQLAlchemy
    error, because a paused Supabase project loses its DNS entirely and the
    connect fails before SQLAlchemy has anything to wrap. It also surfaces when
    the endpoint runs its query, not when the session is opened, since the
    engine connects lazily — so it is caught here at the yield rather than
    around the session construction.

    Without this the endpoint returns a bare 500 that tells a user nothing and
    points a developer at the wrong thing. 503 with the reason says what is
    actually wrong and marks it transient.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except (OSError, SQLAlchemyError) as e:
            logger.warning(f"Database unavailable: {type(e).__name__}: {e}")
            raise HTTPException(
                status_code=503,
                detail=(
                    "The database is temporarily unavailable, so stored records "
                    "(alert history, community reports) cannot be read right now. "
                    "Hazard assessment and advisories are unaffected."
                ),
            ) from e


async def get_optional_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Yield a session, or None when the database cannot be reached.

    For endpoints whose real job does not need the database. Sending a warning
    to a phone is the clearest case: the database records that it happened and
    stops it being sent twice — both worth having, neither worth withholding a
    warning over. With Supabase paused, every alert request came back "Server
    busy" and no SMS went out, which is an early-warning system silenced by its
    own analytics store.

    Unlike `get_session` this does NOT convert a failure into a 503 — that is
    the whole point. It hands over a session and lets the caller guard its own
    queries, so a database problem degrades the endpoint instead of ending it.

    Callers must handle both a None session and a query that raises, and must
    say so in their response rather than quietly dropping the bookkeeping.
    """
    try:
        session = SessionLocal()
    except Exception as e:  # noqa: BLE001 — construction should never fail, but
        logger.warning(f"Could not open a database session ({type(e).__name__}: {e})")
        yield None
        return

    # Deliberately no try/except around the yield: swallowing an exception
    # raised by the endpoint would suppress its error handling rather than
    # degrade it, which is a different and worse behaviour.
    async with session:
        yield session


async def init_db() -> None:
    """Create tables if they don't exist. Called once on startup.

    Retries up to 3 times with exponential backoff so a transient network
    blip (common on Render free tier waking up) doesn't kill the whole
    process.  If the DB is genuinely unreachable after all retries, the
    app still starts — the /health endpoint keeps Render happy, and
    requests that need the DB will fail individually with 503s.
    """
    # Import models so they're registered on Base.metadata before create_all.
    from app.models import db_models  # noqa: F401

    backend = "Supabase/Postgres" if "asyncpg" in _db_url else "SQLite"
    last_err = None
    for attempt in range(1, 4):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info(f"   Database: {backend} ready ({_db_url.split('@')[-1]})")
            return
        except Exception as exc:
            last_err = exc
            wait = 2 ** attempt  # 2, 4, 8 seconds
            logger.warning(
                f"   DB init attempt {attempt}/3 failed: {exc!r}  "
                f"— retrying in {wait}s…"
            )
            await asyncio.sleep(wait)

    # All retries exhausted — log loudly but let the app start so Render's
    # /health probe doesn't trigger an infinite crash-restart loop.
    logger.error(
        f"   Database: {backend} UNREACHABLE after 3 attempts "
        f"({_db_url.split('@')[-1]}). Last error: {last_err!r}.  "
        f"The app will start without DB — endpoints needing it will return 503."
    )


async def close_db() -> None:
    """Dispose of the engine's connection pool on shutdown."""
    await engine.dispose()

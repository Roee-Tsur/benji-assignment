"""SQLite engine setup. The database is both the store and the delivery queue (ADR 0001).

Transactions: the sqlite3 driver only opens a transaction at the first INSERT/UPDATE/DELETE, so
every write transaction takes the write lock with its first statement and waits up to
`busy_timeout` for it. Reads before that statement are not isolated from concurrent writers, so
decisions that must be atomic go into a single conditional statement (`UPDATE … WHERE …`) or a
unique constraint, never a read followed by a write.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Dialect, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

from webhooks.settings import Settings


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC (so SQLite compares them as strings correctly), returns aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetimes are ambiguous; pass an aware UTC datetime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    type_annotation_map = {datetime: UTCDateTime}  # noqa: RUF012


def create_engine(settings: Settings) -> AsyncEngine:
    engine = create_async_engine(settings.database_url)

    @event.listens_for(engine.sync_engine, "connect")
    def configure_connection(dbapi_connection: Any, _record: Any) -> None:  # pyright: ignore[reportUnusedFunction]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={int(settings.sqlite_busy_timeout_ms)}")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # Objects stay readable after commit; services return them to routers.
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    # No migrations: the plan cuts Alembic, so the schema is created on startup.
    import webhooks.models  # noqa: F401  # pyright: ignore[reportUnusedImport]  (registers tables)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

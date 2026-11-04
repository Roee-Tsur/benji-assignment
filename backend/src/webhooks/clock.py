from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Injected wherever time matters, so tests control it."""

    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

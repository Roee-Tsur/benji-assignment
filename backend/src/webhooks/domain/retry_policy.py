"""When a delivery is tried again, and whether it should be. Pure: no I/O, randomness injected."""

import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

type Verdict = Literal["success", "retryable", "endpoint_gone"]
type Uniform = Callable[[float, float], float]

_DELTA_SECONDS = re.compile(r"[0-9]+")
# Longer values saturate here rather than hit `int()`'s digit limit; any cap is far below it.
_MAX_RETRY_AFTER_DIGITS = 18
# 2**62 seconds is far past any cap, and keeps the float math from overflowing.
_MAX_EXPONENT = 62


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    base_seconds: float
    cap_seconds: float

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.base_seconds <= 0 or self.cap_seconds < self.base_seconds:
            raise ValueError(f"nonsensical retry policy: {self}")

    def backoff(self, attempts_used: int, *, uniform: Uniform = random.uniform) -> timedelta:
        """Exponential backoff with full jitter: uniform in [0, min(cap, base * 2^(n-1))]."""
        exponent = min(max(attempts_used - 1, 0), _MAX_EXPONENT)
        ceiling = min(self.cap_seconds, self.base_seconds * 2**exponent)
        return timedelta(seconds=uniform(0, ceiling))

    def retry_delay(
        self, attempts_used: int, retry_after: str | None, *, uniform: Uniform = random.uniform
    ) -> timedelta:
        """The receiver's usable `Retry-After` (clamped to the cap), else backoff."""
        seconds = parse_retry_after(retry_after)
        if seconds is None:
            return self.backoff(attempts_used, uniform=uniform)
        return timedelta(seconds=min(seconds, self.cap_seconds))


def classify(response_status: int | None) -> Verdict:
    """`None` means there was no response: a timeout, connection error, or interrupted attempt.

    3xx is retryable because redirects aren't followed. 410 means the endpoint is gone for good.
    """
    if response_status is None:
        return "retryable"
    if 200 <= response_status < 300:
        return "success"
    if response_status == 410:
        return "endpoint_gone"
    return "retryable"


def parse_retry_after(header: str | None) -> int | None:
    """Seconds from the delta-seconds form. The HTTP-date form and anything malformed: `None`."""
    if header is None:
        return None
    value = header.strip()
    if not _DELTA_SECONDS.fullmatch(value):
        return None
    return int(value) if len(value) <= _MAX_RETRY_AFTER_DIGITS else 10**_MAX_RETRY_AFTER_DIGITS

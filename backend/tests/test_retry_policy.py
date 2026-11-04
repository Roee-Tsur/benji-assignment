import random
from datetime import timedelta

import pytest

from webhooks.domain.retry_policy import RetryPolicy, Verdict, classify, parse_retry_after
from webhooks.settings import Settings

POLICY = RetryPolicy(max_attempts=6, base_seconds=2, cap_seconds=300)


def upper(_low: float, high: float) -> float:
    return high


def lower(low: float, _high: float) -> float:
    return low


@pytest.mark.parametrize(
    ("attempts_used", "ceiling"),
    [(1, 2), (2, 4), (3, 8), (4, 16), (5, 32), (6, 64), (8, 256), (9, 300), (50, 300)],
)
def test_backoff_ceiling_doubles_up_to_the_cap(attempts_used: int, ceiling: float) -> None:
    assert POLICY.backoff(attempts_used, uniform=upper) == timedelta(seconds=ceiling)
    assert POLICY.backoff(attempts_used, uniform=lower) == timedelta(0)


def test_backoff_survives_absurd_attempt_counts() -> None:
    assert POLICY.backoff(10_000, uniform=upper) == timedelta(seconds=300)


@pytest.mark.parametrize("attempts_used", [1, 3, 6, 20])
def test_full_jitter_stays_within_zero_and_the_ceiling(attempts_used: int) -> None:
    rng = random.Random(attempts_used)
    ceiling = POLICY.backoff(attempts_used, uniform=upper)

    delays = [POLICY.backoff(attempts_used, uniform=rng.uniform) for _ in range(500)]

    assert all(timedelta(0) <= delay <= ceiling for delay in delays)
    assert len(set(delays)) > 1  # jittered, not a fixed schedule


@pytest.mark.parametrize(
    ("response_status", "verdict"),
    [
        (200, "success"),
        (201, "success"),
        (204, "success"),
        (299, "success"),
        (410, "endpoint_gone"),
        (301, "retryable"),  # redirects aren't followed
        (304, "retryable"),
        (400, "retryable"),
        (404, "retryable"),
        (429, "retryable"),
        (500, "retryable"),
        (503, "retryable"),
        (100, "retryable"),
        (None, "retryable"),  # no response: timeout, connection error, interrupted
    ],
)
def test_classifies_outcomes(response_status: int | None, verdict: Verdict) -> None:
    assert classify(response_status) == verdict


@pytest.mark.parametrize(
    ("header", "seconds"),
    [
        ("0", 0),
        ("120", 120),
        (" 30 ", 30),
        (None, None),
        ("", None),
        ("-5", None),
        ("1.5", None),
        ("abc", None),
        ("٣", None),  # a non-ASCII digit
        ("9" * 10, None),  # absurdly long, and never near int()'s digit limit
        ("9" * 5000, None),
        ("Wed, 21 Oct 2026 07:28:00 GMT", None),  # HTTP-date form is ignored
    ],
)
def test_parses_retry_after_delta_seconds_only(header: str | None, seconds: int | None) -> None:
    assert parse_retry_after(header) == seconds


@pytest.mark.parametrize(
    ("header", "delay"),
    [
        ("45", 45),
        ("300", 300),
        ("301", 300),  # clamped to the cap
        ("999999999", 300),
    ],
)
def test_retry_delay_honors_retry_after_clamped_to_the_cap(header: str, delay: float) -> None:
    assert POLICY.retry_delay(3, header, uniform=upper) == timedelta(seconds=delay)


@pytest.mark.parametrize("header", [None, "Wed, 21 Oct 2026 07:28:00 GMT", "soon"])
def test_retry_delay_falls_back_to_backoff(header: str | None) -> None:
    assert POLICY.retry_delay(3, header, uniform=upper) == timedelta(seconds=8)


@pytest.mark.parametrize(("base", "cap", "max_attempts"), [(0, 10, 6), (2, 1, 6), (2, 10, 0)])
def test_rejects_nonsensical_policies(base: float, cap: float, max_attempts: int) -> None:
    with pytest.raises(ValueError, match="retry policy"):
        RetryPolicy(max_attempts=max_attempts, base_seconds=base, cap_seconds=cap)


def test_settings_reject_a_nonsensical_policy_at_startup() -> None:
    with pytest.raises(ValueError, match="retry policy"):
        Settings(
            _env_file=None,  # pyright: ignore[reportCallIssue]
            webhook_retry_base_seconds=10,
            webhook_retry_cap_seconds=5,
        )

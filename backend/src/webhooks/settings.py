from typing import Self

from pydantic import PositiveInt, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from webhooks.domain.retry_policy import RetryPolicy


class Settings(BaseSettings):
    """Read from the environment (or `.env`); names match the env vars, case-insensitively."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./webhooks.db"
    sqlite_busy_timeout_ms: int = 5000

    mock_receiver_enabled: bool = True
    worker_enabled: bool = True
    worker_poll_interval_seconds: float = 0.5
    worker_concurrency: PositiveInt = 10  # attempts in flight at once
    # How long shutdown waits for in-flight attempts. Unset: as long as a request may take.
    worker_shutdown_timeout_seconds: float | None = None

    webhook_request_timeout_seconds: float = 10.0
    webhook_lease_seconds: float = 30.0
    webhook_retry_max_attempts: int = 6
    webhook_retry_base_seconds: float = 2.0
    webhook_retry_cap_seconds: float = 300.0

    @model_validator(mode="after")
    def _check_retry_policy(self) -> Self:
        self.retry_policy  # noqa: B018  # fail at startup, not on the first submit
        return self

    @model_validator(mode="after")
    def _check_lease_outlasts_a_request(self) -> Self:
        # Otherwise a slow attempt is reclaimed while still in flight, and sent again.
        if self.webhook_lease_seconds <= self.webhook_request_timeout_seconds:
            raise ValueError("webhook_lease_seconds must exceed webhook_request_timeout_seconds")
        return self

    @property
    def worker_shutdown_timeout(self) -> float:
        if self.worker_shutdown_timeout_seconds is None:
            return self.webhook_request_timeout_seconds
        return self.worker_shutdown_timeout_seconds

    @property
    def retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            max_attempts=self.webhook_retry_max_attempts,
            base_seconds=self.webhook_retry_base_seconds,
            cap_seconds=self.webhook_retry_cap_seconds,
        )

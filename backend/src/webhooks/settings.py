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

    webhook_request_timeout_seconds: float = 10.0
    webhook_lease_seconds: float = 30.0
    webhook_retry_max_attempts: int = 6
    webhook_retry_base_seconds: float = 2.0
    webhook_retry_cap_seconds: float = 300.0

    @property
    def retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            max_attempts=self.webhook_retry_max_attempts,
            base_seconds=self.webhook_retry_base_seconds,
            cap_seconds=self.webhook_retry_cap_seconds,
        )

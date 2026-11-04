import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from webhooks.main import create_app
from webhooks.runtime import runtime_of
from webhooks.settings import Settings
from webhooks.worker import DeliveryWorker

MOCK_OK = "http://test/mock/ok"
RECEIVER = "https://receiver.example/hook"
# Past any backoff the default policy can pick (its cap is 300s), so a retry is due.
PAST_ANY_BACKOFF = 301

Handler = Callable[[httpx.Request], Coroutine[Any, Any, httpx.Response]]


class FakeClock:
    """Stands still until a test moves it, so due times and leases are under the test's control."""

    def __init__(self, start: datetime = datetime(2026, 1, 1, tzinfo=UTC)) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        worker_enabled=False,
        mock_receiver_enabled=True,
    )


@pytest.fixture
async def app(settings: Settings, clock: FakeClock) -> AsyncIterator[FastAPI]:
    app = create_app(settings, clock)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client


@pytest.fixture
def worker(app: FastAPI, client: AsyncClient) -> DeliveryWorker:
    """A worker whose HTTP calls are routed into the app, so `http://test/mock/*` works."""
    runtime = runtime_of(app)
    return DeliveryWorker(runtime.sessions, client, runtime.clock, runtime.settings)


def worker_with_transport(app: FastAPI, handler: Handler, **settings: Any) -> DeliveryWorker:
    """A worker that sends to `handler` instead; `settings` overrides the app's."""
    runtime = runtime_of(app)
    http = AsyncClient(transport=httpx.MockTransport(handler))
    return DeliveryWorker(
        runtime.sessions, http, runtime.clock, runtime.settings.model_copy(update=settings)
    )


def responses(*statuses: int) -> Handler:
    """A receiver that answers with these statuses in turn."""
    remaining = list(statuses)

    async def receiver(request: httpx.Request) -> httpx.Response:
        return httpx.Response(remaining.pop(0))

    return receiver


async def create_endpoint(
    client: AsyncClient,
    url: str = MOCK_OK,
    event_types: list[str] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        "/endpoints",
        json={"url": url, "event_types": event_types or ["reward_transaction_created"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def submit_event(
    client: AsyncClient,
    key: str = "key-1",
    event_type: str = "reward_transaction_created",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        "/events",
        json={"type": event_type, "data": data if data is not None else {"points": 10}},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


async def list_deliveries(client: AsyncClient, **params: Any) -> list[dict[str, Any]]:
    """The first page's deliveries; `params` are the list's query parameters."""
    response = await client.get("/deliveries", params=params)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def only_delivery(client: AsyncClient) -> dict[str, Any]:
    [delivery] = await list_deliveries(client)
    return (await client.get(f"/deliveries/{delivery['id']}")).json()


async def eventually(predicate: Callable[[], bool], within: float = 2.0) -> None:
    """Waits (in real time) until `predicate` holds, for tests that run the worker loop."""
    async with asyncio.timeout(within):
        while not predicate():  # noqa: ASYNC110  # polling a plain predicate is the point
            await asyncio.sleep(0.005)

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, update

from tests.conftest import (
    PAST_ANY_BACKOFF,
    RECEIVER,
    FakeClock,
    Handler,
    create_endpoint,
    eventually,
    list_deliveries,
    only_delivery,
    responses,
    submit_event,
    worker_with_transport,
)
from webhooks.domain import signing
from webhooks.main import create_app
from webhooks.models import Delivery, Endpoint
from webhooks.runtime import runtime_of
from webhooks.services import deliveries as deliveries_service
from webhooks.settings import Settings
from webhooks.worker import DeliveryWorker


async def lease_token(app: FastAPI, delivery_id: str) -> str | None:
    async with runtime_of(app).sessions() as session:
        return await session.scalar(select(Delivery.lease_token).where(Delivery.id == delivery_id))


async def claim_and_abandon(app: FastAPI, clock: FakeClock) -> None:
    """What a worker that crashes mid-attempt leaves behind: a claim that is never written back."""
    runtime = runtime_of(app)
    lease = timedelta(seconds=runtime.settings.webhook_lease_seconds)
    async with runtime.sessions() as session:
        assert await deliveries_service.claim_next(session, now=clock.now(), lease_duration=lease)


def at(value: str) -> datetime:
    return datetime.fromisoformat(value)


# One attempt


async def test_delivery_to_the_mock_receiver_succeeds_with_one_attempt(
    client: AsyncClient, worker: DeliveryWorker
) -> None:
    await create_endpoint(client)
    await submit_event(client)

    assert await worker.run_once() is True

    [delivery] = await list_deliveries(client)
    assert delivery["status"] == "succeeded"
    assert delivery["attempt_count"] == 1
    assert delivery["attempts_used"] == 1
    detail = (await client.get(f"/deliveries/{delivery['id']}")).json()
    [attempt] = detail["attempts"]
    assert attempt["number"] == 1
    assert attempt["outcome"] == "response"
    assert attempt["response_status"] == 200
    assert attempt["request_headers"]["webhook-id"] == delivery["id"]
    assert attempt["started_at"] <= attempt["finished_at"]


async def test_nothing_due_means_no_work(worker: DeliveryWorker) -> None:
    assert await worker.run_once() is False


async def test_sends_the_stored_envelope_bytes_signed_with_the_endpoint_secret(
    app: FastAPI, client: AsyncClient
) -> None:
    endpoint = await create_endpoint(client, url=RECEIVER)
    event = await submit_event(client, data={"note": "café"})
    sent: list[httpx.Request] = []

    async def receiver(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(204)

    await worker_with_transport(app, receiver).run_once()

    [request] = sent
    assert str(request.url) == RECEIVER
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {
        "id": event["id"],
        "type": "reward_transaction_created",
        "timestamp": event["created_at"],
        "data": {"note": "café"},
    }
    assert b" " not in request.content.replace(b"caf\xc3\xa9", b"")  # compact, UTF-8
    signing.verify(
        endpoint["secret"], request.headers, request.content, now=runtime_of(app).clock.now()
    )


async def test_the_stored_response_body_is_truncated_to_2kb(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="x" * 5000)

    await worker_with_transport(app, receiver).run_once()

    [attempt] = (await only_delivery(client))["attempts"]
    assert attempt["response_body"] == "x" * 2048


async def test_connection_error_is_recorded_as_an_attempt(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    await worker_with_transport(app, receiver).run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "pending"
    [attempt] = delivery["attempts"]
    assert attempt["outcome"] == "connection_error"
    assert attempt["response_status"] is None
    assert "connection refused" in attempt["error"]


async def test_timeout_is_recorded_as_an_attempt(app: FastAPI, client: AsyncClient) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    await worker_with_transport(app, receiver).run_once()

    [attempt] = (await only_delivery(client))["attempts"]
    assert attempt["outcome"] == "timeout"


async def test_the_timeout_bounds_the_whole_request(app: FastAPI, client: AsyncClient) -> None:
    """httpx's timeout is per read, so a receiver that keeps trickling bytes needs its own cap."""
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200)

    worker = worker_with_transport(app, receiver, webhook_request_timeout_seconds=0.05)
    async with asyncio.timeout(2):
        await worker.run_once()

    [attempt] = (await only_delivery(client))["attempts"]
    assert attempt["outcome"] == "timeout"


async def test_any_request_error_is_recorded_rather_than_stranding_the_delivery(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        raise httpx.DecodingError("bad gzip", request=request)

    await worker_with_transport(app, receiver).run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "pending"
    [attempt] = delivery["attempts"]
    assert attempt["outcome"] == "connection_error"


async def test_no_transaction_is_held_open_during_the_http_call(
    app: FastAPI, client: AsyncClient
) -> None:
    """If the claim's write transaction were still open, this write would be locked out."""
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    sessions = runtime_of(app).sessions

    async def receiver(request: httpx.Request) -> httpx.Response:
        async with sessions() as session:
            await session.execute(
                update(Endpoint).where(Endpoint.id == endpoint["id"]).values(url="https://x.test")
            )
            await session.commit()
        return httpx.Response(200)

    await worker_with_transport(app, receiver).run_once()

    [delivery] = await list_deliveries(client)
    assert delivery["status"] == "succeeded"


async def test_each_delivery_is_claimed_once(client: AsyncClient, worker: DeliveryWorker) -> None:
    await create_endpoint(client)
    await create_endpoint(client)
    await submit_event(client)

    assert await worker.run_once() is True
    assert await worker.run_once() is True
    assert await worker.run_once() is False

    deliveries = await list_deliveries(client)
    assert [d["attempt_count"] for d in deliveries] == [1, 1]


# Retries


async def test_a_failed_attempt_is_retried_after_backoff(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    await worker_with_transport(app, responses(500)).run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "pending"
    assert delivery["failure_reason"] is None
    assert delivery["attempts_used"] == 1
    [attempt] = delivery["attempts"]
    assert attempt["response_status"] == 500
    # Full jitter on the first retry: anywhere in [0, base].
    base = timedelta(seconds=runtime_of(app).settings.webhook_retry_base_seconds)
    assert clock.now() <= at(delivery["next_attempt_at"]) <= clock.now() + base


async def test_a_retry_waits_until_it_is_due(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    worker = worker_with_transport(app, responses(503, 200), webhook_retry_base_seconds=10)
    await worker.run_once()
    due = at((await only_delivery(client))["next_attempt_at"])

    clock.advance((due - clock.now()).total_seconds() - 0.001)
    ran_early = await worker.run_once()
    clock.advance(0.001)

    assert ran_early is False
    assert await worker.run_once() is True


async def test_retries_until_success(app: FastAPI, client: AsyncClient, clock: FakeClock) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    worker = worker_with_transport(app, responses(500, 503, 200))

    for _ in range(3):
        assert await worker.run_once() is True
        clock.advance(PAST_ANY_BACKOFF)

    delivery = await only_delivery(client)
    assert delivery["status"] == "succeeded"
    assert delivery["attempts_used"] == 3
    assert [a["number"] for a in delivery["attempts"]] == [1, 2, 3]
    assert [a["response_status"] for a in delivery["attempts"]] == [500, 503, 200]


async def test_retries_until_the_attempt_budget_is_exhausted(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    budget = runtime_of(app).settings.webhook_retry_max_attempts
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    worker = worker_with_transport(app, responses(*[500] * budget))

    for _ in range(budget):
        assert await worker.run_once() is True
        clock.advance(PAST_ANY_BACKOFF)
    assert await worker.run_once() is False

    delivery = await only_delivery(client)
    assert delivery["status"] == "failed"
    assert delivery["failure_reason"] == "attempts_exhausted"
    assert delivery["attempts_used"] == budget
    assert len(delivery["attempts"]) == budget


async def test_410_fails_at_once_as_endpoint_gone(app: FastAPI, client: AsyncClient) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    await worker_with_transport(app, responses(410)).run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "failed"
    assert delivery["failure_reason"] == "endpoint_gone"
    assert delivery["attempts_used"] == 1


async def test_retry_after_is_honored(app: FastAPI, client: AsyncClient, clock: FakeClock) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, headers={"retry-after": "120"})

    await worker_with_transport(app, receiver).run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "pending"
    assert at(delivery["next_attempt_at"]) == clock.now() + timedelta(seconds=120)


async def test_every_attempt_is_signed_afresh_with_the_same_webhook_id(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    sent: list[httpx.Request] = []

    async def receiver(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(500 if len(sent) == 1 else 200)

    worker = worker_with_transport(app, receiver)
    await worker.run_once()
    clock.advance(PAST_ANY_BACKOFF)
    await worker.run_once()

    first, second = sent
    delivery = await only_delivery(client)
    assert first.headers["webhook-id"] == second.headers["webhook-id"] == delivery["id"]
    assert int(second.headers["webhook-timestamp"]) > int(first.headers["webhook-timestamp"])
    assert first.headers["webhook-signature"] != second.headers["webhook-signature"]
    assert first.content == second.content
    signing.verify(endpoint["secret"], second.headers, second.content, now=clock.now())


# Leases


async def test_an_expired_lease_is_reclaimed_as_interrupted(
    app: FastAPI, client: AsyncClient, clock: FakeClock, worker: DeliveryWorker
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    await claim_and_abandon(app, clock)

    clock.advance(runtime_of(app).settings.webhook_lease_seconds)
    assert await worker.reclaim_expired() == 1

    delivery = await only_delivery(client)
    assert delivery["status"] == "pending"
    assert delivery["attempts_used"] == 1
    [attempt] = delivery["attempts"]
    assert attempt["number"] == 1
    assert attempt["outcome"] == "interrupted"
    assert attempt["response_status"] is None
    assert await lease_token(app, delivery["id"]) is None


async def test_a_live_lease_is_not_reclaimed(
    app: FastAPI, client: AsyncClient, clock: FakeClock, worker: DeliveryWorker
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    await claim_and_abandon(app, clock)

    clock.advance(runtime_of(app).settings.webhook_lease_seconds - 1)

    assert await worker.reclaim_expired() == 0
    assert (await only_delivery(client))["status"] == "in_progress"


async def test_interrupted_attempts_spend_the_budget(
    app: FastAPI, client: AsyncClient, clock: FakeClock, worker: DeliveryWorker
) -> None:
    """A delivery that kills its worker every time can't loop forever."""
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    settings = runtime_of(app).settings

    for _ in range(settings.webhook_retry_max_attempts):
        await claim_and_abandon(app, clock)
        clock.advance(settings.webhook_lease_seconds)
        assert await worker.reclaim_expired() == 1
        clock.advance(PAST_ANY_BACKOFF)

    delivery = await only_delivery(client)
    assert delivery["status"] == "failed"
    assert delivery["failure_reason"] == "attempts_exhausted"
    assert {a["outcome"] for a in delivery["attempts"]} == {"interrupted"}


async def test_a_stale_lease_write_is_discarded(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    """A slow attempt loses its lease, a newer attempt succeeds, then the slow one reports back."""
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    lease_seconds = runtime_of(app).settings.webhook_lease_seconds
    calls = 0

    async def receiver(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:  # the slow attempt: meanwhile its lease expires and a newer one runs
            clock.advance(lease_seconds)
            assert await worker.reclaim_expired() == 1
            clock.advance(PAST_ANY_BACKOFF)
            assert await worker.run_once() is True
            return httpx.Response(500)
        return httpx.Response(200)

    worker = worker_with_transport(app, receiver)
    await worker.run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "succeeded"
    assert delivery["attempt_count"] == 2
    assert [(a["number"], a["outcome"], a["response_status"]) for a in delivery["attempts"]] == [
        (1, "interrupted", None),
        (2, "response", 200),
    ]


# The pool and shutdown


def blocking_receiver() -> tuple[Handler, list[asyncio.Event]]:
    """Each request waits until the test sets its gate; `gates` shows how many have arrived."""
    gates: list[asyncio.Event] = []

    async def receiver(request: httpx.Request) -> httpx.Response:
        gate = asyncio.Event()
        gates.append(gate)
        await gate.wait()
        return httpx.Response(200)

    return receiver, gates


async def test_the_pool_keeps_10_in_flight_and_claims_as_soon_as_one_finishes(
    app: FastAPI, client: AsyncClient
) -> None:
    for _ in range(12):
        await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    receiver, gates = blocking_receiver()
    # The poll never comes around, so only a finished attempt can wake the loop to claim more.
    worker = worker_with_transport(app, receiver, worker_poll_interval_seconds=3600)
    task = asyncio.create_task(worker.run())

    await eventually(lambda: len(gates) == 10)
    await asyncio.sleep(0.05)
    assert len(gates) == 10
    gates[0].set()
    await eventually(lambda: len(gates) == 11)
    gates[1].set()
    await eventually(lambda: len(gates) == 12)

    for gate in gates:
        gate.set()
    worker.stop()
    await task
    assert {d["status"] for d in await list_deliveries(client)} == {"succeeded"}


async def test_shutdown_lets_in_flight_attempts_finish(app: FastAPI, client: AsyncClient) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    receiver, gates = blocking_receiver()
    worker = worker_with_transport(app, receiver)
    task = asyncio.create_task(worker.run())
    await eventually(lambda: len(gates) == 1)

    worker.stop()
    gates[0].set()
    await task

    assert (await only_delivery(client))["status"] == "succeeded"


async def test_shutdown_releases_the_leases_of_attempts_that_do_not_finish(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    receiver, gates = blocking_receiver()
    worker = worker_with_transport(app, receiver, worker_shutdown_timeout_seconds=0.05)
    task = asyncio.create_task(worker.run())
    await eventually(lambda: len(gates) == 1)

    worker.stop()
    async with asyncio.timeout(2):
        await task

    delivery = await only_delivery(client)
    assert delivery["status"] == "pending"
    assert delivery["attempts_used"] == 1
    [attempt] = delivery["attempts"]
    assert attempt["outcome"] == "interrupted"
    assert await lease_token(app, delivery["id"]) is None


async def test_shutdown_stops_claiming(app: FastAPI, client: AsyncClient) -> None:
    await create_endpoint(client, url=RECEIVER)
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    receiver, gates = blocking_receiver()
    worker = worker_with_transport(app, receiver, worker_concurrency=1)
    task = asyncio.create_task(worker.run())
    await eventually(lambda: len(gates) == 1)

    worker.stop()
    gates[0].set()
    await task

    assert sorted(d["status"] for d in await list_deliveries(client)) == ["pending", "succeeded"]
    assert len(gates) == 1


async def test_app_shutdown_stops_the_worker(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"worker_enabled": True}))

    async with asyncio.timeout(2), app.router.lifespan_context(app):
        pass


async def test_one_failed_release_does_not_stop_shutdown_releasing_the_rest(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    receiver, gates = blocking_receiver()
    worker = worker_with_transport(app, receiver, worker_shutdown_timeout_seconds=0.05)
    task = asyncio.create_task(worker.run())
    await eventually(lambda: len(gates) == 2)
    record_attempt = deliveries_service.record_attempt
    releases = 0

    async def first_release_fails(*args: Any, **kwargs: Any) -> Any:
        nonlocal releases
        releases += 1
        if releases == 1:
            raise RuntimeError("database is locked")
        return await record_attempt(*args, **kwargs)

    monkeypatch.setattr(deliveries_service, "record_attempt", first_release_fails)
    worker.stop()
    async with asyncio.timeout(2):
        await task

    assert releases == 2
    assert sorted(d["status"] for d in await list_deliveries(client)) == [
        "in_progress",  # left for lease reclaim
        "pending",
    ]


def test_settings_reject_a_lease_that_a_request_can_outlast() -> None:
    with pytest.raises(ValueError, match="lease"):
        Settings(
            _env_file=None,  # pyright: ignore[reportCallIssue]
            webhook_request_timeout_seconds=30,
            webhook_lease_seconds=30,
        )


def test_shutdown_waits_as_long_as_a_request_may_take_by_default(settings: Settings) -> None:
    slow = settings.model_copy(update={"webhook_request_timeout_seconds": 25})
    assert slow.worker_shutdown_timeout == 25

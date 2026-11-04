import json
from collections.abc import Callable, Coroutine
from typing import Any

import httpx
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import update

from tests.conftest import create_endpoint, list_deliveries, submit_event
from webhooks.domain import signing
from webhooks.models import Endpoint
from webhooks.runtime import runtime_of
from webhooks.worker import DeliveryWorker

Handler = Callable[[httpx.Request], Coroutine[Any, Any, httpx.Response]]


def worker_with_transport(app: FastAPI, handler: Handler) -> DeliveryWorker:
    runtime = runtime_of(app)
    http = AsyncClient(transport=httpx.MockTransport(handler))
    return DeliveryWorker(runtime.sessions, http, runtime.clock, runtime.settings)


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
    endpoint = await create_endpoint(client, url="https://receiver.example/hook")
    event = await submit_event(client, data={"note": "café"})
    sent: list[httpx.Request] = []

    async def receiver(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(204)

    await worker_with_transport(app, receiver).run_once()

    [request] = sent
    assert str(request.url) == "https://receiver.example/hook"
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


async def test_non_2xx_response_fails_the_delivery(app: FastAPI, client: AsyncClient) -> None:
    await create_endpoint(client, url="https://receiver.example/hook")
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="x" * 5000)

    await worker_with_transport(app, receiver).run_once()

    [delivery] = await list_deliveries(client)
    assert delivery["status"] == "failed"
    detail = (await client.get(f"/deliveries/{delivery['id']}")).json()
    [attempt] = detail["attempts"]
    assert attempt["response_status"] == 500
    assert len(attempt["response_body"]) == 2048


async def test_connection_error_is_recorded_as_an_attempt(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client, url="https://receiver.example/hook")
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    await worker_with_transport(app, receiver).run_once()

    [delivery] = await list_deliveries(client)
    assert delivery["status"] == "failed"
    [attempt] = (await client.get(f"/deliveries/{delivery['id']}")).json()["attempts"]
    assert attempt["outcome"] == "connection_error"
    assert attempt["response_status"] is None
    assert "connection refused" in attempt["error"]


async def test_timeout_is_recorded_as_an_attempt(app: FastAPI, client: AsyncClient) -> None:
    await create_endpoint(client, url="https://receiver.example/hook")
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    await worker_with_transport(app, receiver).run_once()

    [delivery] = await list_deliveries(client)
    [attempt] = (await client.get(f"/deliveries/{delivery['id']}")).json()["attempts"]
    assert attempt["outcome"] == "timeout"


async def test_no_transaction_is_held_open_during_the_http_call(
    app: FastAPI, client: AsyncClient
) -> None:
    """If the claim's write transaction were still open, this write would be locked out."""
    endpoint = await create_endpoint(client, url="https://receiver.example/hook")
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


async def test_any_request_error_is_recorded_rather_than_stranding_the_delivery(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client, url="https://receiver.example/hook")
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        raise httpx.DecodingError("bad gzip", request=request)

    await worker_with_transport(app, receiver).run_once()

    [delivery] = await list_deliveries(client)
    assert delivery["status"] == "failed"
    [attempt] = (await client.get(f"/deliveries/{delivery['id']}")).json()["attempts"]
    assert attempt["outcome"] == "connection_error"

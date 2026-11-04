"""Disabling an endpoint (ADR 0003): pending deliveries fail at once, in-flight attempts finish."""

from datetime import datetime

import httpx
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import update

from tests.conftest import (
    RECEIVER,
    FakeClock,
    create_endpoint,
    list_deliveries,
    only_delivery,
    responses,
    submit_event,
    worker_with_transport,
)
from webhooks.models import Endpoint
from webhooks.runtime import runtime_of


async def disable(client: AsyncClient, endpoint_id: str) -> httpx.Response:
    response = await client.patch(f"/endpoints/{endpoint_id}", json={"enabled": False})
    assert response.status_code == 200, response.text
    return response


async def flip_enabled_only(app: FastAPI, endpoint_id: str, *, enabled: bool) -> None:
    """Flips the flag without the rest of the disable, leaving a pending delivery behind."""
    async with runtime_of(app).sessions() as session:
        await session.execute(
            update(Endpoint).where(Endpoint.id == endpoint_id).values(enabled=enabled)
        )
        await session.commit()


async def test_disabling_fails_pending_deliveries(client: AsyncClient, clock: FakeClock) -> None:
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    clock.advance(5)

    await disable(client, endpoint["id"])

    delivery = await only_delivery(client)
    assert delivery["status"] == "failed"
    assert delivery["failure_reason"] == "endpoint_disabled"
    assert delivery["attempts"] == []
    assert datetime.fromisoformat(delivery["updated_at"]) == clock.now()


async def test_disabling_leaves_other_endpoints_and_settled_deliveries_alone(
    app: FastAPI, client: AsyncClient
) -> None:
    disabled = await create_endpoint(client, url=RECEIVER, event_types=["campaign_updated"])
    other = await create_endpoint(client, url=RECEIVER, event_types=["campaign_updated"])
    await submit_event(client, key="a", event_type="campaign_updated")
    await worker_with_transport(app, responses(200)).run_once()  # one of the two succeeds
    [succeeded] = [d for d in await list_deliveries(client) if d["status"] == "succeeded"]

    await disable(client, succeeded["endpoint_id"])

    by_endpoint = {d["endpoint_id"]: d for d in await list_deliveries(client)}
    assert by_endpoint[succeeded["endpoint_id"]]["status"] == "succeeded"
    pending_id = ({disabled["id"], other["id"]} - {succeeded["endpoint_id"]}).pop()
    assert by_endpoint[pending_id]["status"] == "pending"


async def test_reenabling_delivers_nothing(app: FastAPI, client: AsyncClient) -> None:
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    await disable(client, endpoint["id"])

    enabled = await client.patch(f"/endpoints/{endpoint['id']}", json={"enabled": True})

    assert enabled.json()["enabled"] is True
    assert await worker_with_transport(app, responses()).run_once() is False
    assert (await only_delivery(client))["failure_reason"] == "endpoint_disabled"


async def test_an_attempt_in_flight_when_its_endpoint_is_disabled_finishes(
    app: FastAPI, client: AsyncClient
) -> None:
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        await disable(client, endpoint["id"])
        return httpx.Response(200)

    await worker_with_transport(app, receiver).run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "succeeded"
    assert [a["response_status"] for a in delivery["attempts"]] == [200]


async def test_an_in_flight_attempt_that_would_retry_fails_once_its_endpoint_is_disabled(
    app: FastAPI, client: AsyncClient
) -> None:
    """Going back to pending would show a retry that the endpoint will never get."""
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)

    async def receiver(request: httpx.Request) -> httpx.Response:
        await disable(client, endpoint["id"])
        return httpx.Response(500)

    await worker_with_transport(app, receiver).run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "failed"
    assert delivery["failure_reason"] == "endpoint_disabled"
    assert [a["response_status"] for a in delivery["attempts"]] == [500]


async def test_the_claim_rechecks_the_endpoint_and_sends_nothing_to_a_disabled_one(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    """A pending delivery whose endpoint is disabled is failed at claim, and the claim moves on."""
    disabled = await create_endpoint(client, url=RECEIVER, event_types=["campaign_updated"])
    await submit_event(client, key="a", event_type="campaign_updated")
    clock.advance(1)
    enabled = await create_endpoint(client, url="https://other.example/hook")
    await submit_event(client, key="b")
    await flip_enabled_only(app, disabled["id"], enabled=False)
    sent: list[httpx.Request] = []

    async def receiver(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200)

    assert await worker_with_transport(app, receiver).run_once() is True

    assert [str(request.url) for request in sent] == [enabled["url"]]
    by_endpoint = {d["endpoint_id"]: d for d in await list_deliveries(client)}
    assert by_endpoint[disabled["id"]]["status"] == "failed"
    assert by_endpoint[disabled["id"]]["failure_reason"] == "endpoint_disabled"
    assert by_endpoint[enabled["id"]]["status"] == "succeeded"

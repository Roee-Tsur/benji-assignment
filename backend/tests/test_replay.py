from datetime import datetime

import httpx
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import (
    PAST_ANY_BACKOFF,
    RECEIVER,
    FakeClock,
    create_endpoint,
    list_deliveries,
    only_delivery,
    responses,
    submit_event,
    worker_with_transport,
)
from webhooks.runtime import runtime_of
from webhooks.worker import DeliveryWorker


async def fail_every_delivery(app: FastAPI) -> None:
    """A 410 fails a delivery in one attempt."""
    while await worker_with_transport(app, responses(410)).run_once():
        pass


async def replay(client: AsyncClient, delivery_id: str) -> httpx.Response:
    return await client.post(f"/deliveries/{delivery_id}/replay")


# One delivery


async def test_replay_returns_a_failed_delivery_to_pending_with_a_fresh_budget(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    await fail_every_delivery(app)
    clock.advance(60)
    failed = await only_delivery(client)

    response = await replay(client, failed["id"])

    assert response.status_code == 200, response.text
    replayed = response.json()
    assert replayed["id"] == failed["id"]
    assert replayed["status"] == "pending"
    assert replayed["failure_reason"] is None
    assert replayed["attempts_used"] == 0
    assert replayed["attempt_budget"] == runtime_of(app).settings.webhook_retry_max_attempts
    assert replayed["attempt_count"] == 1  # the history stays
    assert len(replayed["attempts"]) == 1
    assert datetime.fromisoformat(replayed["next_attempt_at"]) == clock.now()  # due at once


async def test_a_replay_continues_the_numbering_with_the_same_webhook_id(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    sent: list[httpx.Request] = []

    async def receiver(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(410 if len(sent) == 1 else 200)

    worker = worker_with_transport(app, receiver)
    await worker.run_once()
    await replay(client, (await only_delivery(client))["id"])
    await worker.run_once()

    delivery = await only_delivery(client)
    assert delivery["status"] == "succeeded"
    assert delivery["attempt_count"] == 2
    assert delivery["attempts_used"] == 1
    assert [a["number"] for a in delivery["attempts"]] == [1, 2]
    assert [r.headers["webhook-id"] for r in sent] == [delivery["id"], delivery["id"]]


async def test_only_failed_deliveries_can_be_replayed(app: FastAPI, client: AsyncClient) -> None:
    await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    pending = await only_delivery(client)

    refused_pending = await replay(client, pending["id"])
    await worker_with_transport(app, responses(200)).run_once()
    refused_succeeded = await replay(client, pending["id"])

    for response, status in ((refused_pending, "pending"), (refused_succeeded, "succeeded")):
        assert response.status_code == 409
        assert response.headers["content-type"] == "application/problem+json"
        assert status in response.json()["detail"]
    assert (await only_delivery(client))["status"] == "succeeded"


async def test_a_delivery_of_a_disabled_endpoint_cannot_be_replayed(
    app: FastAPI, client: AsyncClient
) -> None:
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    await client.patch(f"/endpoints/{endpoint['id']}", json={"enabled": False})
    failed = await only_delivery(client)

    response = await replay(client, failed["id"])

    assert response.status_code == 409
    assert "disabled" in response.json()["detail"]
    assert (await only_delivery(client))["status"] == "failed"


async def test_replaying_an_unknown_delivery_is_a_404(client: AsyncClient) -> None:
    response = await replay(client, "dlv_missing")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


# Every failed delivery of an endpoint


async def test_replay_failed_replays_only_the_endpoints_failed_deliveries(
    app: FastAPI, client: AsyncClient
) -> None:
    target = await create_endpoint(client, url=RECEIVER, event_types=["campaign_updated"])
    other = await create_endpoint(client, url=RECEIVER, event_types=["member_account_linked"])
    await submit_event(client, key="a", event_type="campaign_updated")
    await submit_event(client, key="b", event_type="campaign_updated")
    await submit_event(client, key="c", event_type="member_account_linked")
    await fail_every_delivery(app)
    await submit_event(client, key="d", event_type="campaign_updated")
    await worker_with_transport(app, responses(200)).run_once()
    await submit_event(client, key="e", event_type="campaign_updated")

    response = await client.post(f"/endpoints/{target['id']}/replay-failed")

    assert response.status_code == 200, response.text
    assert response.json() == {"replayed": 2}
    by_status: dict[tuple[str, str], int] = {}
    for d in await list_deliveries(client):
        key = (d["endpoint_id"], d["status"])
        by_status[key] = by_status.get(key, 0) + 1
    assert by_status == {
        (target["id"], "pending"): 3,  # the two replayed, and "e"
        (target["id"], "succeeded"): 1,
        (other["id"], "failed"): 1,
    }


async def test_the_endpoint_list_counts_failed_deliveries_until_they_are_replayed(
    app: FastAPI, client: AsyncClient
) -> None:
    target = await create_endpoint(client, url=RECEIVER, event_types=["campaign_updated"])
    other = await create_endpoint(client, url=RECEIVER, event_types=["member_account_linked"])
    await submit_event(client, key="a", event_type="campaign_updated")
    await submit_event(client, key="b", event_type="campaign_updated")
    await fail_every_delivery(app)
    await submit_event(client, key="c", event_type="campaign_updated")  # pending: not counted

    async def failed_counts() -> dict[str, int]:
        listed = (await client.get("/endpoints")).json()
        return {endpoint["id"]: endpoint["failed_count"] for endpoint in listed}

    assert await failed_counts() == {target["id"]: 2, other["id"]: 0}
    await client.post(f"/endpoints/{target['id']}/replay-failed")
    assert await failed_counts() == {target["id"]: 0, other["id"]: 0}


async def test_replay_failed_with_nothing_failed_replays_nothing(client: AsyncClient) -> None:
    endpoint = await create_endpoint(client)

    response = await client.post(f"/endpoints/{endpoint['id']}/replay-failed")

    assert response.json() == {"replayed": 0}


async def test_replay_failed_on_a_disabled_endpoint_is_a_409(client: AsyncClient) -> None:
    endpoint = await create_endpoint(client, url=RECEIVER)
    await submit_event(client)
    await client.patch(f"/endpoints/{endpoint['id']}", json={"enabled": False})

    response = await client.post(f"/endpoints/{endpoint['id']}/replay-failed")

    assert response.status_code == 409
    assert "disabled" in response.json()["detail"]
    assert (await only_delivery(client))["status"] == "failed"


async def test_replay_failed_on_an_unknown_endpoint_is_a_404(client: AsyncClient) -> None:
    response = await client.post("/endpoints/ep_missing/replay-failed")

    assert response.status_code == 404


# End to end, through the mock receiver


async def test_flaky_through_the_whole_budget_fails_then_a_replay_succeeds(
    app: FastAPI, client: AsyncClient, clock: FakeClock, worker: DeliveryWorker
) -> None:
    budget = runtime_of(app).settings.webhook_retry_max_attempts
    await create_endpoint(client, url=f"http://test/mock/flaky?n={budget}")
    await submit_event(client)

    for _ in range(budget):
        assert await worker.run_once() is True
        clock.advance(PAST_ANY_BACKOFF)
    failed = await only_delivery(client)
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "attempts_exhausted"

    assert (await replay(client, failed["id"])).status_code == 200
    assert await worker.run_once() is True

    delivery = await only_delivery(client)
    assert delivery["status"] == "succeeded"
    assert delivery["attempt_count"] == budget + 1
    assert delivery["attempts_used"] == 1
    assert [a["number"] for a in delivery["attempts"]] == list(range(1, budget + 2))
    assert [a["response_status"] for a in delivery["attempts"]] == [500] * budget + [200]
    assert {a["request_headers"]["webhook-id"] for a in delivery["attempts"]} == {delivery["id"]}

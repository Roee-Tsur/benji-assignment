from httpx import AsyncClient

from tests.conftest import create_endpoint, list_deliveries, submit_event


async def test_fans_out_to_enabled_subscribed_endpoints_only(client: AsyncClient) -> None:
    subscribed = await create_endpoint(client, event_types=["reward_transaction_created"])
    also_subscribed = await create_endpoint(
        client, event_types=["campaign_updated", "reward_transaction_created"]
    )
    await create_endpoint(client, event_types=["campaign_updated"])
    disabled = await create_endpoint(client, event_types=["reward_transaction_created"])
    await client.patch(f"/endpoints/{disabled['id']}", json={"enabled": False})

    event = await submit_event(client, event_type="reward_transaction_created")

    assert event["id"].startswith("evt_")
    assert event["deduplicated"] is False
    assert event["delivery_count"] == 2
    deliveries = await list_deliveries(client)
    assert {d["endpoint_id"] for d in deliveries} == {subscribed["id"], also_subscribed["id"]}
    assert all(d["status"] == "pending" and d["event_id"] == event["id"] for d in deliveries)
    assert all(d["attempt_count"] == 0 and d["attempt_budget"] == 6 for d in deliveries)


async def test_new_event_is_201(client: AsyncClient) -> None:
    response = await client.post(
        "/events",
        json={"type": "campaign_updated", "data": {}},
        headers={"Idempotency-Key": "k"},
    )

    assert response.status_code == 201


async def test_stores_the_envelope_that_every_attempt_sends(client: AsyncClient) -> None:
    await create_endpoint(client, event_types=["member_account_linked"])

    event = await submit_event(client, event_type="member_account_linked", data={"member": "m_1"})

    [delivery] = await list_deliveries(client)
    detail = (await client.get(f"/deliveries/{delivery['id']}")).json()
    assert detail["payload"] == {
        "id": event["id"],
        "type": "member_account_linked",
        "timestamp": event["created_at"],
        "data": {"member": "m_1"},
    }


async def test_resubmitting_the_same_key_creates_no_new_deliveries(client: AsyncClient) -> None:
    await create_endpoint(client)
    original = await submit_event(client, key="same")
    await create_endpoint(client)  # a later subscriber must not get the resubmitted event

    resubmitted = await client.post(
        "/events",
        json={"type": "reward_transaction_created", "data": {"points": 10}},
        headers={"Idempotency-Key": "same"},
    )

    assert resubmitted.status_code == 200
    body = resubmitted.json()
    assert body["id"] == original["id"]
    assert body["deduplicated"] is True
    assert body["delivery_count"] == 1
    assert len(await list_deliveries(client)) == 1


async def test_event_with_no_subscribers_has_no_deliveries(client: AsyncClient) -> None:
    event = await submit_event(client, event_type="campaign_updated")

    assert event["delivery_count"] == 0


async def test_rejects_unknown_event_types(client: AsyncClient) -> None:
    response = await client.post(
        "/events", json={"type": "nope", "data": {}}, headers={"Idempotency-Key": "k"}
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"

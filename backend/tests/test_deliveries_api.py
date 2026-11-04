from httpx import AsyncClient

from tests.conftest import create_endpoint, list_deliveries, submit_event


async def test_lists_newest_first_with_event_and_endpoint_context(client: AsyncClient) -> None:
    endpoint = await create_endpoint(client, event_types=["campaign_updated"])
    first = await submit_event(client, key="a", event_type="campaign_updated")
    second = await submit_event(client, key="b", event_type="campaign_updated")

    deliveries = await list_deliveries(client)

    assert [d["event_id"] for d in deliveries] == [second["id"], first["id"]]
    assert deliveries[0]["id"].startswith("dlv_")
    assert deliveries[0]["event_type"] == "campaign_updated"
    assert deliveries[0]["endpoint_url"] == endpoint["url"]
    assert deliveries[0]["failure_reason"] is None


async def test_detail_includes_payload_and_attempts(client: AsyncClient) -> None:
    await create_endpoint(client)
    await submit_event(client)
    [delivery] = await list_deliveries(client)

    response = await client.get(f"/deliveries/{delivery['id']}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == delivery["id"]
    assert detail["attempts"] == []
    assert detail["payload"]["type"] == "reward_transaction_created"


async def test_unknown_delivery_is_a_404_problem(client: AsyncClient) -> None:
    response = await client.get("/deliveries/dlv_missing")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"

from typing import Any

import httpx
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import (
    FakeClock,
    create_endpoint,
    list_deliveries,
    submit_event,
    worker_with_transport,
)

OK = "https://ok.example/hook"
GONE = "https://gone.example/hook"


async def deliver_all(app: FastAPI) -> None:
    """Every due delivery to `OK` succeeds and every one to `GONE` fails (410), in one attempt."""

    async def ok_or_gone(request: httpx.Request) -> httpx.Response:
        return httpx.Response(410 if request.url.host == "gone.example" else 200)

    while await worker_with_transport(app, ok_or_gone).run_once():
        pass


async def test_lists_newest_first_with_event_and_endpoint_context(
    client: AsyncClient, clock: FakeClock
) -> None:
    endpoint = await create_endpoint(client, event_types=["campaign_updated"])
    first = await submit_event(client, key="a", event_type="campaign_updated")
    clock.advance(1)
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


async def test_filters_by_status_endpoint_and_event(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    ok = await create_endpoint(client, url=OK)
    gone = await create_endpoint(client, url=GONE)
    first = await submit_event(client, key="a")
    clock.advance(1)
    second = await submit_event(client, key="b")
    await deliver_all(app)

    failed = await list_deliveries(client, status="failed")
    assert {(d["endpoint_id"], d["status"]) for d in failed} == {
        (gone["id"], "failed"),
    }
    assert len(failed) == 2
    assert {d["endpoint_id"] for d in await list_deliveries(client, endpoint_id=ok["id"])} == {
        ok["id"]
    }
    by_event = await list_deliveries(client, event_id=first["id"])
    assert {d["event_id"] for d in by_event} == {first["id"]}
    assert len(by_event) == 2
    combined = await list_deliveries(
        client, status="succeeded", endpoint_id=ok["id"], event_id=second["id"]
    )
    assert [(d["endpoint_id"], d["event_id"]) for d in combined] == [(ok["id"], second["id"])]


async def test_pages_newest_first_by_keyset_cursor(client: AsyncClient, clock: FakeClock) -> None:
    await create_endpoint(client)
    events: list[dict[str, Any]] = []
    for key in "abcde":
        events.append(await submit_event(client, key=key))
        clock.advance(1)
    newest_first = [event["id"] for event in reversed(events)]

    first = (await client.get("/deliveries", params={"limit": 2})).json()
    second = (
        await client.get("/deliveries", params={"limit": 2, "cursor": first["next_cursor"]})
    ).json()
    last = (
        await client.get("/deliveries", params={"limit": 2, "cursor": second["next_cursor"]})
    ).json()

    pages = [first, second, last]
    assert [[d["event_id"] for d in page["items"]] for page in pages] == [
        newest_first[0:2],
        newest_first[2:4],
        newest_first[4:5],
    ]
    assert last["next_cursor"] is None


async def test_cursor_breaks_created_at_ties_by_id(client: AsyncClient) -> None:
    """One event's deliveries share `created_at`; paging must neither skip nor repeat them."""
    for _ in range(3):
        await create_endpoint(client)
    await submit_event(client)

    first = (await client.get("/deliveries", params={"limit": 2})).json()
    rest = (
        await client.get("/deliveries", params={"limit": 2, "cursor": first["next_cursor"]})
    ).json()

    ids = [d["id"] for d in first["items"] + rest["items"]]
    assert len(ids) == len(set(ids)) == 3
    assert rest["next_cursor"] is None


async def test_a_full_last_page_has_no_cursor(client: AsyncClient) -> None:
    await create_endpoint(client)
    await create_endpoint(client)
    await submit_event(client)

    page = (await client.get("/deliveries", params={"limit": 2})).json()

    assert len(page["items"]) == 2
    assert page["next_cursor"] is None


async def test_cursor_keeps_filters(client: AsyncClient, clock: FakeClock) -> None:
    ok = await create_endpoint(client)
    await create_endpoint(client)
    for key in "abc":
        await submit_event(client, key=key)
        clock.advance(1)

    params = {"limit": 2, "endpoint_id": ok["id"]}
    first = (await client.get("/deliveries", params=params)).json()
    rest = (
        await client.get("/deliveries", params={**params, "cursor": first["next_cursor"]})
    ).json()

    assert {d["endpoint_id"] for d in first["items"] + rest["items"]} == {ok["id"]}
    assert len(first["items"] + rest["items"]) == 3


async def test_rejects_an_unknown_status_and_an_out_of_range_limit(client: AsyncClient) -> None:
    assert (await client.get("/deliveries", params={"status": "bogus"})).status_code == 422
    assert (await client.get("/deliveries", params={"limit": 0})).status_code == 422
    assert (await client.get("/deliveries", params={"limit": 101})).status_code == 422


async def test_counts_by_status_filtered_by_endpoint_and_event(
    app: FastAPI, client: AsyncClient, clock: FakeClock
) -> None:
    ok = await create_endpoint(client, url=OK)
    gone = await create_endpoint(client, url=GONE)
    first = await submit_event(client, key="a")
    await deliver_all(app)
    clock.advance(1)
    await submit_event(client, key="b")

    async def counts(**params: str) -> dict[str, int]:
        response = await client.get("/deliveries/counts", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    assert await counts() == {"pending": 2, "in_progress": 0, "succeeded": 1, "failed": 1}
    assert await counts(endpoint_id=gone["id"]) == {
        "pending": 1,
        "in_progress": 0,
        "succeeded": 0,
        "failed": 1,
    }
    assert await counts(endpoint_id=ok["id"], event_id=first["id"]) == {
        "pending": 0,
        "in_progress": 0,
        "succeeded": 1,
        "failed": 0,
    }

from httpx import AsyncClient

from tests.conftest import create_endpoint


async def test_create_returns_the_signing_secret_once(client: AsyncClient) -> None:
    created = await create_endpoint(client, event_types=["campaign_updated", "campaign_updated"])

    assert created["id"].startswith("ep_")
    assert created["secret"].startswith("whsec_")
    assert created["enabled"] is True
    assert created["event_types"] == ["campaign_updated"]

    listed = (await client.get("/endpoints")).json()
    assert [endpoint["id"] for endpoint in listed] == [created["id"]]
    assert "secret" not in listed[0]


async def test_list_is_newest_first(client: AsyncClient) -> None:
    first = await create_endpoint(client)
    second = await create_endpoint(client)

    listed = (await client.get("/endpoints")).json()

    assert [endpoint["id"] for endpoint in listed] == [second["id"], first["id"]]


async def test_toggle_enabled(client: AsyncClient) -> None:
    created = await create_endpoint(client)

    disabled = await client.patch(f"/endpoints/{created['id']}", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    enabled = await client.patch(f"/endpoints/{created['id']}", json={"enabled": True})
    assert enabled.json()["enabled"] is True


async def test_toggle_unknown_endpoint_is_a_404_problem(client: AsyncClient) -> None:
    response = await client.patch("/endpoints/ep_missing", json={"enabled": False})

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == 404


async def test_rejects_non_http_urls_and_empty_subscriptions(client: AsyncClient) -> None:
    bad_url = await client.post(
        "/endpoints", json={"url": "ftp://example.com", "event_types": ["campaign_updated"]}
    )
    no_types = await client.post(
        "/endpoints", json={"url": "https://example.com", "event_types": []}
    )
    unknown_type = await client.post(
        "/endpoints", json={"url": "https://example.com", "event_types": ["nope"]}
    )

    for response in (bad_url, no_types, unknown_type):
        assert response.status_code == 422
        assert response.headers["content-type"] == "application/problem+json"
        problem = response.json()
        assert problem["title"] == "Request validation failed"
        assert problem["errors"]

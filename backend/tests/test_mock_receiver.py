from datetime import UTC, datetime
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from tests.conftest import FakeClock, create_endpoint, list_deliveries, submit_event
from webhooks.domain import signing
from webhooks.main import create_app
from webhooks.settings import Settings

BODY = b'{"hello":"world"}'


async def _delivery_and_secret(client: AsyncClient) -> tuple[str, str]:
    endpoint = await create_endpoint(client)
    await submit_event(client)
    [delivery] = await list_deliveries(client)
    return delivery["id"], endpoint["secret"]


async def test_accepts_a_valid_signature(client: AsyncClient, clock: FakeClock) -> None:
    delivery_id, secret = await _delivery_and_secret(client)
    headers = signing.signature_headers(secret, delivery_id, clock.now(), BODY)

    response = await client.post("/mock/ok", content=BODY, headers=headers)

    assert response.status_code == 200


async def test_rejects_a_bad_signature(client: AsyncClient) -> None:
    delivery_id, _ = await _delivery_and_secret(client)
    headers = signing.signature_headers(
        signing.generate_secret(), delivery_id, datetime.now(UTC), BODY
    )

    response = await client.post("/mock/ok", content=BODY, headers=headers)

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert "signature" in response.json()["detail"]


async def test_rejects_an_unknown_webhook_id(client: AsyncClient) -> None:
    headers = signing.signature_headers(
        signing.generate_secret(), "dlv_unknown", datetime.now(UTC), BODY
    )

    response = await client.post("/mock/ok", content=BODY, headers=headers)

    assert response.status_code == 401


async def test_rejects_missing_headers(client: AsyncClient) -> None:
    response = await client.post("/mock/ok", content=BODY)

    assert response.status_code == 401


async def test_is_not_mounted_when_disabled(settings: Settings, tmp_path: Path) -> None:
    app = create_app(settings.model_copy(update={"mock_receiver_enabled": False}))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app), base_url="http://test") as client,
    ):
        response = await client.post("/mock/ok", content=BODY)

    assert response.status_code == 404

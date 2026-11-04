from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import create_endpoint, list_deliveries, submit_event
from webhooks.domain.enums import DeliveryStatus
from webhooks.models import Delivery
from webhooks.runtime import runtime_of


async def test_openapi_schema_is_served(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert {"/endpoints", "/endpoints/{endpoint_id}", "/events", "/deliveries"} <= set(
        schema["paths"]
    )
    assert not any(path.startswith("/mock") for path in schema["paths"])
    validation_error = schema["paths"]["/events"]["post"]["responses"]["422"]
    assert "application/problem+json" in validation_error["content"]


async def test_sqlite_runs_in_wal_mode_with_a_busy_timeout(app: FastAPI) -> None:
    async with runtime_of(app).sessions() as session:
        journal_mode = (await session.execute(text("PRAGMA journal_mode"))).scalar_one()
        busy_timeout = (await session.execute(text("PRAGMA busy_timeout"))).scalar_one()

    assert journal_mode == "wal"
    assert busy_timeout == runtime_of(app).settings.sqlite_busy_timeout_ms


async def test_at_most_one_delivery_per_event_and_endpoint(
    app: FastAPI, client: AsyncClient
) -> None:
    await create_endpoint(client)
    await submit_event(client)
    [existing] = await list_deliveries(client)
    now = datetime.now(UTC)

    async with runtime_of(app).sessions() as session:
        session.add(
            Delivery(
                id="dlv_duplicate",
                event_id=existing["event_id"],
                endpoint_id=existing["endpoint_id"],
                status=DeliveryStatus.PENDING,
                attempt_budget=6,
                next_attempt_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_http_error_problems_keep_their_headers(client: AsyncClient) -> None:
    response = await client.delete("/events")

    assert response.status_code == 405
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["allow"] == "POST"

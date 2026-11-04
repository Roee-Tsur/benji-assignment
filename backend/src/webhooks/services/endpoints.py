from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from webhooks.domain import signing
from webhooks.domain.enums import DeliveryStatus, EventType, FailureReason
from webhooks.ids import new_id
from webhooks.models import Delivery, Endpoint
from webhooks.services.errors import NotFoundError


async def create_endpoint(
    session: AsyncSession, *, url: str, event_types: Sequence[EventType], now: datetime
) -> Endpoint:
    endpoint = Endpoint(
        id=new_id("ep"),
        url=url,
        event_types=[str(event_type) for event_type in event_types],
        secret=signing.generate_secret(),
        enabled=True,
        created_at=now,
    )
    session.add(endpoint)
    await session.commit()
    return endpoint


@dataclass(frozen=True)
class ListedEndpoint:
    endpoint: Endpoint
    failed_count: int


async def list_endpoints(session: AsyncSession) -> Sequence[ListedEndpoint]:
    """Newest first, each with how many failed deliveries "replay failed" would retry."""
    failed_count = (
        select(func.count())
        .select_from(Delivery)
        .where(Delivery.endpoint_id == Endpoint.id, Delivery.status == DeliveryStatus.FAILED)
        .scalar_subquery()
    )
    query = select(Endpoint, failed_count).order_by(Endpoint.created_at.desc(), Endpoint.id.desc())
    return [ListedEndpoint(endpoint, count) for endpoint, count in await session.execute(query)]


async def set_enabled(
    session: AsyncSession, endpoint_id: str, *, enabled: bool, now: datetime
) -> Endpoint:
    """Disabling also fails the endpoint's pending deliveries, in the same transaction (ADR 0003).

    Attempts already in progress finish. Enabling again delivers nothing: that is replay's job.
    """
    endpoint = await session.scalar(
        update(Endpoint)
        .where(Endpoint.id == endpoint_id)
        .values(enabled=enabled)
        .returning(Endpoint)
    )
    if endpoint is None:
        await session.rollback()
        raise NotFoundError("endpoint", endpoint_id)
    if not enabled:
        await session.execute(
            update(Delivery)
            .where(Delivery.endpoint_id == endpoint_id, Delivery.status == DeliveryStatus.PENDING)
            .values(
                status=DeliveryStatus.FAILED,
                failure_reason=FailureReason.ENDPOINT_DISABLED,
                updated_at=now,
            )
        )
    await session.commit()
    return endpoint

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from webhooks.domain import signing
from webhooks.domain.enums import EventType
from webhooks.ids import new_id
from webhooks.models import Endpoint
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


async def list_endpoints(session: AsyncSession) -> Sequence[Endpoint]:
    query = select(Endpoint).order_by(Endpoint.created_at.desc(), Endpoint.id.desc())
    return (await session.scalars(query)).all()


async def set_enabled(session: AsyncSession, endpoint_id: str, *, enabled: bool) -> Endpoint:
    """Only flips the flag. What disabling does to pending deliveries is ADR 0003 (#5)."""
    endpoint = await session.scalar(
        update(Endpoint)
        .where(Endpoint.id == endpoint_id)
        .values(enabled=enabled)
        .returning(Endpoint)
    )
    if endpoint is None:
        await session.rollback()
        raise NotFoundError("endpoint", endpoint_id)
    await session.commit()
    return endpoint

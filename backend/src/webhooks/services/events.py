from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from webhooks.domain.enums import DeliveryStatus, EventType
from webhooks.domain.envelope import MAX_ENVELOPE_BYTES, serialize_envelope
from webhooks.ids import new_id
from webhooks.models import Delivery, Endpoint, Event
from webhooks.services.errors import IdempotencyKeyReusedError, PayloadTooLargeError


@dataclass(frozen=True)
class SubmittedEvent:
    event: Event
    delivery_count: int
    deduplicated: bool


async def submit_event(
    session: AsyncSession,
    *,
    event_type: EventType,
    data: dict[str, Any],
    idempotency_key: str,
    now: datetime,
    attempt_budget: int,
) -> SubmittedEvent:
    """Stores the event and fans it out in one transaction (a transactional outbox).

    Subscribers are snapshotted now: an endpoint created later never gets this event.

    Dedup is insert-and-catch on the key's unique constraint, never check-then-insert: a
    concurrent submit with the same key waits on the write lock, then hits the constraint.
    """
    event_id = new_id("evt")
    envelope = serialize_envelope(event_id, event_type, now, data)
    if len(envelope) > MAX_ENVELOPE_BYTES:
        raise PayloadTooLargeError(len(envelope), MAX_ENVELOPE_BYTES)

    event = Event(
        id=event_id,
        type=event_type,
        idempotency_key=idempotency_key,
        data=data,
        envelope=envelope,
        created_at=now,
    )
    session.add(event)
    try:
        await session.flush()  # the INSERT takes the write lock before fan-out reads endpoints
    except IntegrityError:
        await session.rollback()
        return await _resubmitted(session, idempotency_key, event_type, data)

    enabled = await session.scalars(select(Endpoint).where(Endpoint.enabled.is_(True)))
    deliveries = [
        Delivery(
            id=new_id("dlv"),
            event_id=event_id,
            endpoint_id=endpoint.id,
            status=DeliveryStatus.PENDING,
            attempt_budget=attempt_budget,
            next_attempt_at=now,
            created_at=now,
            updated_at=now,
        )
        # Subscriptions are a JSON list, so matching happens here; fine at this scale.
        for endpoint in enabled
        if event_type in endpoint.event_types
    ]
    session.add_all(deliveries)
    await session.commit()
    return SubmittedEvent(event, len(deliveries), False)


async def _resubmitted(
    session: AsyncSession, idempotency_key: str, event_type: EventType, data: dict[str, Any]
) -> SubmittedEvent:
    original = (
        await session.scalars(select(Event).where(Event.idempotency_key == idempotency_key))
    ).one()
    if original.type != event_type or original.data != data:
        raise IdempotencyKeyReusedError(idempotency_key)
    return SubmittedEvent(original, await _delivery_count(session, original.id), True)


async def _delivery_count(session: AsyncSession, event_id: str) -> int:
    query = select(func.count()).select_from(Delivery).where(Delivery.event_id == event_id)
    return (await session.scalar(query)) or 0

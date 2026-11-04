from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from webhooks.domain.enums import AttemptOutcome, DeliveryStatus
from webhooks.ids import new_id
from webhooks.models import Attempt, Delivery, Endpoint, Event
from webhooks.services.errors import NotFoundError

MAX_RESPONSE_BODY_BYTES = 2048


@dataclass(frozen=True)
class ClaimedDelivery:
    """Everything the worker needs to make an attempt without touching the database."""

    delivery_id: str
    lease_token: str
    url: str
    secret: str
    body: bytes


@dataclass(frozen=True)
class AttemptResult:
    started_at: datetime
    finished_at: datetime
    request_headers: dict[str, str]
    outcome: AttemptOutcome
    response_status: int | None = None
    response_body: bytes | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.response_status is not None and 200 <= self.response_status < 300


async def list_deliveries(session: AsyncSession, *, limit: int = 50) -> Sequence[Delivery]:
    query = (
        select(Delivery)
        .options(
            joinedload(Delivery.event).load_only(Event.type),
            joinedload(Delivery.endpoint).load_only(Endpoint.url),
        )
        .order_by(Delivery.created_at.desc(), Delivery.id.desc())
        .limit(limit)
    )
    return (await session.scalars(query)).all()


async def get_delivery(session: AsyncSession, delivery_id: str) -> Delivery:
    query = (
        select(Delivery)
        .where(Delivery.id == delivery_id)
        .options(
            joinedload(Delivery.event),
            joinedload(Delivery.endpoint).load_only(Endpoint.url),
            selectinload(Delivery.attempts),
        )
    )
    delivery = await session.scalar(query)
    if delivery is None:
        raise NotFoundError("delivery", delivery_id)
    return delivery


async def get_signing_secret(session: AsyncSession, delivery_id: str) -> str | None:
    """The secret a receiver would look up from a request's `webhook-id`."""
    query = select(Endpoint.secret).join(Delivery).where(Delivery.id == delivery_id)
    return await session.scalar(query)


async def claim_next(
    session: AsyncSession, *, now: datetime, lease_duration: timedelta
) -> ClaimedDelivery | None:
    """Claims the most overdue pending delivery with a single `UPDATE … RETURNING`.

    The `status = pending` condition is re-checked by the UPDATE itself, so two workers can
    never claim the same row.
    """
    due = (
        select(Delivery.id)
        .where(Delivery.status == DeliveryStatus.PENDING, Delivery.next_attempt_at <= now)
        .order_by(Delivery.next_attempt_at)
        .limit(1)
        .scalar_subquery()
    )
    lease_token = new_id("lease")
    claimed = (
        await session.execute(
            update(Delivery)
            .where(Delivery.id == due, Delivery.status == DeliveryStatus.PENDING)
            .values(
                status=DeliveryStatus.IN_PROGRESS,
                lease_token=lease_token,
                lease_expires_at=now + lease_duration,
                updated_at=now,
            )
            .returning(Delivery.id)
        )
    ).first()
    if claimed is None:
        await session.rollback()
        return None

    url, secret, body = (
        await session.execute(
            select(Endpoint.url, Endpoint.secret, Event.envelope)
            .select_from(Delivery)
            .join(Delivery.endpoint)
            .join(Delivery.event)
            .where(Delivery.id == claimed.id)
        )
    ).one()
    await session.commit()
    return ClaimedDelivery(claimed.id, lease_token, url, secret, body)


async def record_attempt(
    session: AsyncSession, claimed: ClaimedDelivery, result: AttemptResult
) -> DeliveryStatus:
    """Records the attempt and settles the delivery. No retries yet: a failure is final."""
    status = DeliveryStatus.SUCCEEDED if result.succeeded else DeliveryStatus.FAILED
    number = (
        await session.scalars(
            update(Delivery)
            .where(Delivery.id == claimed.delivery_id)
            .values(
                status=status,
                attempt_count=Delivery.attempt_count + 1,
                attempts_used=Delivery.attempts_used + 1,
                lease_token=None,
                lease_expires_at=None,
                updated_at=result.finished_at,
            )
            .returning(Delivery.attempt_count)
        )
    ).one()
    session.add(
        Attempt(
            id=new_id("att"),
            delivery_id=claimed.delivery_id,
            number=number,
            started_at=result.started_at,
            finished_at=result.finished_at,
            request_headers=result.request_headers,
            outcome=result.outcome,
            response_status=result.response_status,
            response_body=_truncate(result.response_body),
            error=result.error,
        )
    )
    await session.commit()
    return status


def _truncate(body: bytes | None) -> str | None:
    if body is None:
        return None
    return body[:MAX_RESPONSE_BODY_BYTES].decode(errors="replace")

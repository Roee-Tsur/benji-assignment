from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from webhooks.domain.enums import AttemptOutcome, DeliveryStatus, FailureReason
from webhooks.domain.retry_policy import RetryPolicy, classify
from webhooks.ids import new_id
from webhooks.models import Attempt, Delivery, Endpoint, Event
from webhooks.services.errors import NotFoundError, NotReplayableError

MAX_RESPONSE_BODY_BYTES = 2048


@dataclass(frozen=True)
class Lease:
    """A worker's claim on one delivery. Its results count only while `token` is still current.

    `attempts_used` is as of the claim: only the lease holder changes it while the lease holds.
    """

    delivery_id: str
    token: str
    attempts_used: int
    attempt_budget: int


@dataclass(frozen=True)
class ClaimedDelivery:
    """Everything the worker needs to make an attempt without touching the database."""

    lease: Lease
    claimed_at: datetime
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
    retry_after: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class _Settlement:
    status: DeliveryStatus
    failure_reason: FailureReason | None = None
    next_attempt_at: datetime | None = None  # only when the delivery goes back to pending


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


async def replay(
    session: AsyncSession, delivery_id: str, *, now: datetime, attempt_budget: int
) -> None:
    """Returns a failed delivery to pending with a fresh budget, in one conditional `UPDATE`.

    Its `attempt_count` (and so the attempt numbering) and its id, the `webhook-id`, carry on.
    """
    replayed = await session.scalar(
        update(Delivery)
        .where(Delivery.id == delivery_id, *_replayable())
        .values(_replayed(now, attempt_budget))
        .returning(Delivery.id)
    )
    if replayed is not None:
        await session.commit()
        return
    # The decision is made; these reads only explain it.
    found = (
        await session.execute(
            select(Delivery.status, Delivery.endpoint_id).where(Delivery.id == delivery_id)
        )
    ).first()
    await session.rollback()
    if found is None:
        raise NotFoundError("delivery", delivery_id)
    status, endpoint_id = found
    if status is not DeliveryStatus.FAILED:
        raise NotReplayableError(
            f"delivery {delivery_id!r} is {status}; only failed deliveries can be replayed"
        )
    raise _endpoint_disabled(endpoint_id)


async def replay_failed(
    session: AsyncSession, endpoint_id: str, *, now: datetime, attempt_budget: int
) -> int:
    """Replays every failed delivery of the endpoint in one conditional `UPDATE`."""
    replayed = (
        await session.scalars(
            update(Delivery)
            .where(Delivery.endpoint_id == endpoint_id, *_replayable())
            .values(_replayed(now, attempt_budget))
            .returning(Delivery.id)
        )
    ).all()
    if replayed:
        await session.commit()
        return len(replayed)
    enabled = await session.scalar(select(Endpoint.enabled).where(Endpoint.id == endpoint_id))
    await session.rollback()
    if enabled is None:
        raise NotFoundError("endpoint", endpoint_id)
    if not enabled:
        raise _endpoint_disabled(endpoint_id)
    return 0


def _replayable() -> tuple[ColumnElement[bool], ...]:
    """Failed, and its endpoint enabled: checked by the replay `UPDATE` itself."""
    enabled_endpoints = select(Endpoint.id).where(Endpoint.enabled.is_(True))
    return (Delivery.status == DeliveryStatus.FAILED, Delivery.endpoint_id.in_(enabled_endpoints))


def _replayed(now: datetime, attempt_budget: int) -> dict[str, object]:
    return {
        "status": DeliveryStatus.PENDING,
        "failure_reason": None,
        "attempts_used": 0,
        "attempt_budget": attempt_budget,
        "next_attempt_at": now,
        "updated_at": now,
    }


def _endpoint_disabled(endpoint_id: str) -> NotReplayableError:
    return NotReplayableError(
        f"endpoint {endpoint_id!r} is disabled; enable it before replaying its deliveries"
    )


async def claim_next(
    session: AsyncSession, *, now: datetime, lease_duration: timedelta
) -> ClaimedDelivery | None:
    """Claims the most overdue pending delivery with a single `UPDATE … RETURNING`.

    The `status = pending` condition is re-checked by the UPDATE itself, so two workers can
    never claim the same row. The endpoint is re-checked after it, under the claim's write lock:
    a delivery whose endpoint is disabled is failed instead of sent, and the next one is claimed.
    """
    due = (
        select(Delivery.id)
        .where(Delivery.status == DeliveryStatus.PENDING, Delivery.next_attempt_at <= now)
        .order_by(Delivery.next_attempt_at)
        .limit(1)
        .scalar_subquery()
    )
    token = new_id("lease")
    while True:
        claimed = (
            await session.execute(
                update(Delivery)
                .where(Delivery.id == due, Delivery.status == DeliveryStatus.PENDING)
                .values(
                    status=DeliveryStatus.IN_PROGRESS,
                    lease_token=token,
                    lease_expires_at=now + lease_duration,
                    updated_at=now,
                )
                .returning(Delivery.id, Delivery.attempts_used, Delivery.attempt_budget)
            )
        ).first()
        if claimed is None:
            await session.commit()  # keeps any deliveries failed along the way
            return None

        enabled, url, secret, body = (
            await session.execute(
                select(Endpoint.enabled, Endpoint.url, Endpoint.secret, Event.envelope)
                .select_from(Delivery)
                .join(Delivery.endpoint)
                .join(Delivery.event)
                .where(Delivery.id == claimed.id)
            )
        ).one()
        if enabled:
            await session.commit()
            lease = Lease(claimed.id, token, claimed.attempts_used, claimed.attempt_budget)
            return ClaimedDelivery(lease, now, url, secret, body)
        await _fail_endpoint_disabled(session, claimed.id, now)


async def record_attempt(
    session: AsyncSession, lease: Lease, result: AttemptResult, policy: RetryPolicy
) -> DeliveryStatus | None:
    """Records the attempt and settles the delivery: succeeded, failed, or pending for a retry.

    The write is fenced on the lease token. If the lease was lost (it expired and was reclaimed),
    a newer attempt may already exist, so nothing is written and this returns `None`.
    """
    attempts_used = lease.attempts_used + 1
    settlement = _settle(result, attempts_used, lease.attempt_budget, policy)
    values: dict[str, object] = {
        "status": settlement.status,
        "failure_reason": settlement.failure_reason,
        "attempt_count": Delivery.attempt_count + 1,
        "attempts_used": attempts_used,
        "lease_token": None,
        "lease_expires_at": None,
        "updated_at": result.finished_at,
    }
    if settlement.next_attempt_at is not None:
        values["next_attempt_at"] = settlement.next_attempt_at
    number = (
        await session.scalars(
            update(Delivery)
            .where(Delivery.id == lease.delivery_id, Delivery.lease_token == lease.token)
            .values(values)
            .returning(Delivery.attempt_count)
        )
    ).one_or_none()
    if number is None:
        await session.rollback()
        return None
    # Under the write lock now, so a disable can't land between this check and the commit.
    status = settlement.status
    if status is DeliveryStatus.PENDING and not await _endpoint_enabled(session, lease.delivery_id):
        await _fail_endpoint_disabled(session, lease.delivery_id, result.finished_at)
        status = DeliveryStatus.FAILED

    session.add(
        Attempt(
            id=new_id("att"),
            delivery_id=lease.delivery_id,
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


async def reclaim_expired(
    session: AsyncSession, *, now: datetime, lease_duration: timedelta, policy: RetryPolicy
) -> int:
    """Records each expired lease as an `interrupted` attempt and settles its delivery.

    An interrupted attempt spends the budget like any failed one, so a delivery that keeps
    killing its worker still fails in the end. Each write is fenced on the token read here: if
    the holder writes back first, its result stands and this reclaim of it changes nothing.
    """
    expired = await session.execute(
        select(
            Delivery.id,
            Delivery.lease_token,
            Delivery.lease_expires_at,
            Delivery.attempts_used,
            Delivery.attempt_budget,
        ).where(Delivery.status == DeliveryStatus.IN_PROGRESS, Delivery.lease_expires_at <= now)
    )
    reclaimed = 0
    for delivery_id, token, expires_at, attempts_used, attempt_budget in expired.all():
        if token is None or expires_at is None:  # in progress always holds a lease
            continue
        lease = Lease(delivery_id, token, attempts_used, attempt_budget)
        result = interrupted(started_at=expires_at - lease_duration, now=now, why="lease expired")
        if await record_attempt(session, lease, result, policy) is not None:
            reclaimed += 1
    return reclaimed


async def _endpoint_enabled(session: AsyncSession, delivery_id: str) -> bool:
    query = select(Endpoint.enabled).join(Delivery).where(Delivery.id == delivery_id)
    return bool(await session.scalar(query))


async def _fail_endpoint_disabled(session: AsyncSession, delivery_id: str, now: datetime) -> None:
    await session.execute(
        update(Delivery)
        .where(Delivery.id == delivery_id)
        .values(
            status=DeliveryStatus.FAILED,
            failure_reason=FailureReason.ENDPOINT_DISABLED,
            lease_token=None,
            lease_expires_at=None,
            updated_at=now,
        )
    )


def interrupted(*, started_at: datetime, now: datetime, why: str) -> AttemptResult:
    """An attempt whose outcome was never recorded. Whether it reached the receiver is unknown."""
    return AttemptResult(
        started_at=started_at,
        finished_at=now,
        request_headers={},
        outcome=AttemptOutcome.INTERRUPTED,
        error=why,
    )


def _settle(
    result: AttemptResult, attempts_used: int, attempt_budget: int, policy: RetryPolicy
) -> _Settlement:
    match classify(result.response_status):
        case "success":
            return _Settlement(DeliveryStatus.SUCCEEDED)
        case "endpoint_gone":
            return _Settlement(DeliveryStatus.FAILED, FailureReason.ENDPOINT_GONE)
        case "retryable" if attempts_used >= attempt_budget:
            return _Settlement(DeliveryStatus.FAILED, FailureReason.ATTEMPTS_EXHAUSTED)
        case "retryable":
            delay = policy.retry_delay(attempts_used, result.retry_after)
            return _Settlement(DeliveryStatus.PENDING, next_attempt_at=result.finished_at + delay)


def _truncate(body: bytes | None) -> str | None:
    if body is None:
        return None
    return body[:MAX_RESPONSE_BODY_BYTES].decode(errors="replace")

"""ORM models. API schemas live separately in `webhooks.api.schemas`."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, LargeBinary, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webhooks.db import Base
from webhooks.domain.enums import AttemptOutcome, DeliveryStatus, FailureReason


def _values(enum: type[StrEnum]) -> list[str]:
    return [member.value for member in enum]


def _enum[E: StrEnum](enum: type[E]) -> Enum:
    """Stores the enum's value (`in_progress`), not its name, as plain text."""
    return Enum(
        enum,
        native_enum=False,
        length=32,
        values_callable=_values,
        validate_strings=True,
    )


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[str] = mapped_column(primary_key=True)
    url: Mapped[str]
    event_types: Mapped[list[str]] = mapped_column(JSON)
    secret: Mapped[str]
    enabled: Mapped[bool]
    created_at: Mapped[datetime]


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[str]
    idempotency_key: Mapped[str] = mapped_column(unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    # The serialized envelope: every attempt sends (and signs) exactly these bytes.
    envelope: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime]


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("event_id", "endpoint_id"),
        Index("ix_deliveries_status_next_attempt_at", "status", "next_attempt_at"),
    )

    # Also the `webhook-id`: stable across attempts and replays, so receivers can dedupe on it.
    id: Mapped[str] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("endpoints.id"), index=True)
    status: Mapped[DeliveryStatus] = mapped_column(_enum(DeliveryStatus))
    failure_reason: Mapped[FailureReason | None] = mapped_column(_enum(FailureReason))

    # Every attempt ever made; the next attempt's number is `attempt_count + 1`.
    attempt_count: Mapped[int] = mapped_column(default=0)
    # Attempts made in the current budget; a replay resets this, not `attempt_count`.
    attempts_used: Mapped[int] = mapped_column(default=0)
    attempt_budget: Mapped[int]
    next_attempt_at: Mapped[datetime]

    lease_token: Mapped[str | None]
    lease_expires_at: Mapped[datetime | None]

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    event: Mapped[Event] = relationship(lazy="raise")
    endpoint: Mapped[Endpoint] = relationship(lazy="raise")
    attempts: Mapped[list["Attempt"]] = relationship(lazy="raise", order_by="Attempt.number")


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("delivery_id", "number"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("deliveries.id"))
    number: Mapped[int]
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime]
    request_headers: Mapped[dict[str, str]] = mapped_column(JSON)
    outcome: Mapped[AttemptOutcome] = mapped_column(_enum(AttemptOutcome))
    response_status: Mapped[int | None]
    # Truncated; see `webhooks.services.deliveries.MAX_RESPONSE_BODY_BYTES`.
    response_body: Mapped[str | None]
    error: Mapped[str | None]

"""API schemas, kept separate from the ORM models so the wire format changes deliberately."""

import json
from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import AfterValidator, BaseModel, Field, HttpUrl

from webhooks.domain.enums import AttemptOutcome, DeliveryStatus, EventType, FailureReason
from webhooks.models import Attempt, Delivery, Endpoint, Event


def _unique[T](items: list[T]) -> list[T]:
    return list(dict.fromkeys(items))


class EndpointCreate(BaseModel):
    url: HttpUrl
    event_types: Annotated[list[EventType], Field(min_length=1), AfterValidator(_unique)]


class EndpointUpdate(BaseModel):
    enabled: bool


class EndpointOut(BaseModel):
    id: str
    url: str
    event_types: list[EventType]
    enabled: bool
    created_at: datetime

    @classmethod
    def from_model(cls, endpoint: Endpoint) -> Self:
        return cls(
            id=endpoint.id,
            url=endpoint.url,
            event_types=[EventType(event_type) for event_type in endpoint.event_types],
            enabled=endpoint.enabled,
            created_at=endpoint.created_at,
        )


class EndpointCreated(EndpointOut):
    secret: str = Field(description="The signing secret. Returned only here, once.")

    @classmethod
    def from_created(cls, endpoint: Endpoint) -> Self:
        return cls(**EndpointOut.from_model(endpoint).model_dump(), secret=endpoint.secret)


class EventCreate(BaseModel):
    type: EventType
    data: dict[str, Any]


class EventSubmitted(BaseModel):
    id: str
    type: EventType
    data: dict[str, Any]
    idempotency_key: str
    created_at: datetime
    delivery_count: int
    deduplicated: bool = Field(
        description="True when the key was seen before: this is the original event, "
        "and no new deliveries were created."
    )

    @classmethod
    def from_model(cls, event: Event, *, delivery_count: int, deduplicated: bool) -> Self:
        return cls(
            id=event.id,
            type=EventType(event.type),
            data=event.data,
            idempotency_key=event.idempotency_key,
            created_at=event.created_at,
            delivery_count=delivery_count,
            deduplicated=deduplicated,
        )


class DeliveryOut(BaseModel):
    id: str = Field(description="Also the `webhook-id` header of every attempt.")
    event_id: str
    event_type: EventType
    endpoint_id: str
    endpoint_url: str
    status: DeliveryStatus
    failure_reason: FailureReason | None
    attempt_count: int = Field(description="Attempts made over the delivery's whole life.")
    attempts_used: int = Field(description="Attempts made in the current attempt budget.")
    attempt_budget: int
    next_attempt_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, delivery: Delivery) -> Self:
        return cls(
            id=delivery.id,
            event_id=delivery.event_id,
            event_type=EventType(delivery.event.type),
            endpoint_id=delivery.endpoint_id,
            endpoint_url=delivery.endpoint.url,
            status=delivery.status,
            failure_reason=delivery.failure_reason,
            attempt_count=delivery.attempt_count,
            attempts_used=delivery.attempts_used,
            attempt_budget=delivery.attempt_budget,
            next_attempt_at=delivery.next_attempt_at,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
        )


class AttemptOut(BaseModel):
    id: str
    number: int
    started_at: datetime
    finished_at: datetime
    request_headers: dict[str, str]
    outcome: AttemptOutcome
    response_status: int | None
    response_body: str | None = Field(description="Truncated to 2 KB.")
    error: str | None

    @classmethod
    def from_model(cls, attempt: Attempt) -> Self:
        return cls(
            id=attempt.id,
            number=attempt.number,
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
            request_headers=attempt.request_headers,
            outcome=attempt.outcome,
            response_status=attempt.response_status,
            response_body=attempt.response_body,
            error=attempt.error,
        )


class DeliveryDetail(DeliveryOut):
    payload: Any = Field(description="The event envelope exactly as every attempt sends it.")
    attempts: list[AttemptOut]

    @classmethod
    def from_model(cls, delivery: Delivery) -> Self:
        return cls(
            **DeliveryOut.from_model(delivery).model_dump(),
            payload=json.loads(delivery.event.envelope),
            attempts=[AttemptOut.from_model(attempt) for attempt in delivery.attempts],
        )

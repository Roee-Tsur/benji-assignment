from typing import Annotated

from fastapi import APIRouter, Header, Response, status

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.api.problems import problem_responses
from webhooks.api.schemas import EventCreate, EventSubmitted
from webhooks.services import events

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {
            "model": EventSubmitted,
            "description": "Deduplicated: the original event, and no new deliveries.",
        },
        **problem_responses(422),
    },
)
async def submit_event(
    body: EventCreate,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    response: Response,
    session: SessionDep,
    runtime: RuntimeDep,
) -> EventSubmitted:
    submitted = await events.submit_event(
        session,
        event_type=body.type,
        data=body.data,
        idempotency_key=idempotency_key,
        now=runtime.clock.now(),
        attempt_budget=runtime.settings.webhook_retry_max_attempts,
    )
    if submitted.deduplicated:
        response.status_code = status.HTTP_200_OK
    return EventSubmitted.from_model(
        submitted.event,
        delivery_count=submitted.delivery_count,
        deduplicated=submitted.deduplicated,
    )

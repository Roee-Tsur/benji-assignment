from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response, status

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.api.problems import Problem, ValidationProblem, problem_responses
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
        **problem_responses(400, 413),
        422: {
            "model": ValidationProblem | Problem,
            "description": "Invalid request, or the idempotency key was already used for a "
            "different payload (a plain problem, without `errors`).",
        },
    },
)
async def submit_event(
    body: EventCreate,
    response: Response,
    session: SessionDep,
    runtime: RuntimeDep,
    # Declared optional so a missing key is our 400 (IETF Idempotency-Key draft), not FastAPI's 422.
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            max_length=255,
            description="Required. Resubmitting with the same key and payload is deduplicated.",
        ),
    ] = None,
) -> EventSubmitted:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The Idempotency-Key header is required.")
    submitted = await events.submit_event(
        session,
        event_type=body.type,
        data=body.data,
        idempotency_key=idempotency_key,
        now=runtime.clock.now(),
        attempt_budget=runtime.settings.retry_policy.max_attempts,
    )
    if submitted.deduplicated:
        response.status_code = status.HTTP_200_OK
    return EventSubmitted.from_model(
        submitted.event,
        delivery_count=submitted.delivery_count,
        deduplicated=submitted.deduplicated,
    )

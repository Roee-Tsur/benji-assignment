from fastapi import APIRouter

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.api.problems import problem_responses
from webhooks.api.schemas import (
    EndpointCreate,
    EndpointCreated,
    EndpointListed,
    EndpointOut,
    EndpointUpdate,
    ReplayedFailed,
)
from webhooks.services import deliveries, endpoints

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.post("", status_code=201, responses=problem_responses(422))
async def create_endpoint(
    body: EndpointCreate, session: SessionDep, runtime: RuntimeDep
) -> EndpointCreated:
    endpoint = await endpoints.create_endpoint(
        session, url=str(body.url), event_types=body.event_types, now=runtime.clock.now()
    )
    return EndpointCreated.model_validate(endpoint)


@router.get("")
async def list_endpoints(session: SessionDep) -> list[EndpointListed]:
    """Newest first, with their failed-delivery counts."""
    return [
        EndpointListed.from_model(listed.endpoint, failed_count=listed.failed_count)
        for listed in await endpoints.list_endpoints(session)
    ]


@router.patch("/{endpoint_id}", responses=problem_responses(404, 422))
async def update_endpoint(
    endpoint_id: str, body: EndpointUpdate, session: SessionDep, runtime: RuntimeDep
) -> EndpointOut:
    """Disabling fails the endpoint's pending deliveries; enabling again delivers nothing."""
    endpoint = await endpoints.set_enabled(
        session, endpoint_id, enabled=body.enabled, now=runtime.clock.now()
    )
    return EndpointOut.model_validate(endpoint)


@router.post("/{endpoint_id}/replay-failed", responses=problem_responses(404, 409, 422))
async def replay_failed(
    endpoint_id: str, session: SessionDep, runtime: RuntimeDep
) -> ReplayedFailed:
    """Replays every failed delivery of the endpoint, e.g. after an outage. 409 if it's disabled."""
    replayed = await deliveries.replay_failed(
        session,
        endpoint_id,
        now=runtime.clock.now(),
        attempt_budget=runtime.settings.retry_policy.max_attempts,
    )
    return ReplayedFailed(replayed=replayed)

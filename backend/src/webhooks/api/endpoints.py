from fastapi import APIRouter

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.api.problems import problem_responses
from webhooks.api.schemas import EndpointCreate, EndpointCreated, EndpointOut, EndpointUpdate
from webhooks.services import endpoints

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
async def list_endpoints(session: SessionDep) -> list[EndpointOut]:
    return [
        EndpointOut.model_validate(endpoint) for endpoint in await endpoints.list_endpoints(session)
    ]


@router.patch("/{endpoint_id}", responses=problem_responses(404, 422))
async def update_endpoint(
    endpoint_id: str, body: EndpointUpdate, session: SessionDep
) -> EndpointOut:
    endpoint = await endpoints.set_enabled(session, endpoint_id, enabled=body.enabled)
    return EndpointOut.model_validate(endpoint)

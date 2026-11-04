from typing import Annotated

from fastapi import APIRouter, Query

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.api.problems import problem_responses
from webhooks.api.schemas import DeliveryCounts, DeliveryDetail, DeliveryOut, DeliveryPage
from webhooks.domain.enums import DeliveryStatus
from webhooks.services import deliveries
from webhooks.services.deliveries import DeliveryFilter

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

EndpointIdQuery = Annotated[str | None, Query()]
EventIdQuery = Annotated[str | None, Query()]


@router.get("", responses=problem_responses(422))
async def list_deliveries(
    session: SessionDep,
    status: DeliveryStatus | None = None,
    endpoint_id: EndpointIdQuery = None,
    event_id: EventIdQuery = None,
    cursor: Annotated[str | None, Query(description="A previous page's `next_cursor`.")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> DeliveryPage:
    """Newest first, a page at a time."""
    page = await deliveries.list_deliveries(
        session,
        DeliveryFilter(status=status, endpoint_id=endpoint_id, event_id=event_id),
        cursor=cursor,
        limit=limit,
    )
    return DeliveryPage(
        items=[DeliveryOut.from_model(d) for d in page.deliveries],
        next_cursor=page.next_cursor,
    )


@router.get("/counts", responses=problem_responses(422))
async def count_deliveries(
    session: SessionDep, endpoint_id: EndpointIdQuery = None, event_id: EventIdQuery = None
) -> DeliveryCounts:
    """Per status, regardless of paging, for the dashboard's status chips."""
    counts = await deliveries.count_by_status(
        session, DeliveryFilter(endpoint_id=endpoint_id, event_id=event_id)
    )
    return DeliveryCounts(**{status.value: count for status, count in counts.items()})


@router.get("/{delivery_id}", responses=problem_responses(404, 422))
async def get_delivery(delivery_id: str, session: SessionDep) -> DeliveryDetail:
    return DeliveryDetail.from_model(await deliveries.get_delivery(session, delivery_id))


@router.post("/{delivery_id}/replay", responses=problem_responses(404, 409, 422))
async def replay_delivery(
    delivery_id: str, session: SessionDep, runtime: RuntimeDep
) -> DeliveryDetail:
    """A failed delivery goes back to pending with a fresh attempt budget, keeping its history.

    409 if it isn't failed, or its endpoint is disabled.
    """
    await deliveries.replay(
        session,
        delivery_id,
        now=runtime.clock.now(),
        attempt_budget=runtime.settings.retry_policy.max_attempts,
    )
    return DeliveryDetail.from_model(await deliveries.get_delivery(session, delivery_id))

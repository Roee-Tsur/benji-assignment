from fastapi import APIRouter

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.api.problems import problem_responses
from webhooks.api.schemas import DeliveryDetail, DeliveryOut
from webhooks.services import deliveries

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("")
async def list_deliveries(session: SessionDep) -> list[DeliveryOut]:
    """The newest 50. Filters and paging come with the deliveries view."""
    return [DeliveryOut.from_model(d) for d in await deliveries.list_deliveries(session)]


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

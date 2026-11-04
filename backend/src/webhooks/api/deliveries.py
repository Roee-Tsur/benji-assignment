from fastapi import APIRouter

from webhooks.api.deps import SessionDep
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

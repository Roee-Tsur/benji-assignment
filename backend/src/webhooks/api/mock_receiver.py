"""A built-in receiver to point endpoints at, so the system can be tried with nothing else running.

It verifies each request the way a real receiver would, looking up the secret by `webhook-id`.
Mounted only when `MOCK_RECEIVER_ENABLED` is set, and kept out of the OpenAPI schema.
"""

from fastapi import APIRouter, HTTPException, Request

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.domain import signing
from webhooks.services import deliveries

router = APIRouter(prefix="/mock", include_in_schema=False)


@router.post("/ok")
async def ok(request: Request, session: SessionDep, runtime: RuntimeDep) -> dict[str, bool]:
    await _verify(request, session, runtime)
    return {"received": True}


async def _verify(request: Request, session: SessionDep, runtime: RuntimeDep) -> None:
    webhook_id = request.headers.get("webhook-id")
    secret = webhook_id and await deliveries.get_signing_secret(session, webhook_id)
    if not secret:
        raise HTTPException(401, "missing or unknown webhook-id")
    try:
        signing.verify(secret, request.headers, await request.body(), now=runtime.clock.now())
    except signing.SignatureError as error:
        raise HTTPException(401, f"invalid signature: {error}") from error

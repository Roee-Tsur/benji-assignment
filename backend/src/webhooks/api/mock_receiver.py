"""A built-in receiver to point endpoints at, so the system can be tried with nothing else running.

It verifies each request the way a real receiver would, looking up the secret by `webhook-id`,
then answers by mode: `ok`, `fail`, `flaky?n=`, or `slow?s=`. Mounted only when
`MOCK_RECEIVER_ENABLED` is set, and kept out of the OpenAPI schema.
"""

import asyncio
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from webhooks.api.deps import RuntimeDep, SessionDep
from webhooks.domain import signing
from webhooks.services import deliveries

Received = dict[str, bool]


def create_router() -> APIRouter:
    """One per app: `flaky` counts the requests it has seen, as a real receiver would."""
    router = APIRouter(prefix="/mock", include_in_schema=False)
    seen = Counter[str]()

    @router.post("/ok")
    async def ok(request: Request, session: SessionDep, runtime: RuntimeDep) -> Received:
        await _verify(request, session, runtime)
        return {"received": True}

    @router.post("/fail")
    async def fail(request: Request, session: SessionDep, runtime: RuntimeDep) -> Received:
        await _verify(request, session, runtime)
        raise HTTPException(500, "mock receiver: always fails")

    @router.post("/flaky")
    async def flaky(
        request: Request,
        session: SessionDep,
        runtime: RuntimeDep,
        n: Annotated[int, Query(ge=0, description="How many requests to fail per webhook-id.")],
    ) -> Received:
        webhook_id = await _verify(request, session, runtime)
        seen[webhook_id] += 1
        if seen[webhook_id] <= n:
            raise HTTPException(500, f"mock receiver: failing request {seen[webhook_id]} of {n}")
        return {"received": True}

    @router.post("/slow")
    async def slow(
        request: Request,
        session: SessionDep,
        runtime: RuntimeDep,
        s: Annotated[float, Query(ge=0, le=60, description="Seconds to wait before answering.")],
    ) -> Received:
        await _verify(request, session, runtime)
        await asyncio.sleep(s)
        return {"received": True}

    return router


async def _verify(request: Request, session: SessionDep, runtime: RuntimeDep) -> str:
    """Returns the verified `webhook-id`."""
    webhook_id = request.headers.get("webhook-id")
    secret = webhook_id and await deliveries.get_signing_secret(session, webhook_id)
    await session.close()  # gives the connection back, so `slow` doesn't hold one while it waits
    if not webhook_id or not secret:
        raise HTTPException(401, "missing or unknown webhook-id")
    try:
        signing.verify(secret, request.headers, await request.body(), now=runtime.clock.now())
    except signing.SignatureError as error:
        raise HTTPException(401, f"invalid signature: {error}") from error
    return webhook_id

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webhooks.runtime import Runtime, runtime_of


def get_runtime(request: Request) -> Runtime:
    return runtime_of(request.app)


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]


async def get_session(runtime: RuntimeDep) -> AsyncIterator[AsyncSession]:
    async with runtime.sessions() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

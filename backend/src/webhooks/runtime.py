from dataclasses import dataclass
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.applications import Starlette

from webhooks.clock import Clock
from webhooks.settings import Settings


@dataclass(frozen=True)
class Runtime:
    """What the lifespan builds and the request handlers depend on."""

    settings: Settings
    sessions: async_sessionmaker[AsyncSession]
    clock: Clock


def runtime_of(app: Starlette) -> Runtime:
    return cast(Runtime, app.state.runtime)

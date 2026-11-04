import asyncio
import contextlib
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute

from webhooks.api import deliveries, endpoints, events, mock_receiver
from webhooks.api.problems import install_problem_handlers, use_problem_media_type
from webhooks.clock import Clock, SystemClock
from webhooks.db import create_engine, create_schema, create_sessionmaker
from webhooks.runtime import Runtime
from webhooks.settings import Settings
from webhooks.worker import DeliveryWorker


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or Settings()
    clock = clock or SystemClock()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        engine = create_engine(settings)
        await create_schema(engine)
        runtime = Runtime(settings, create_sessionmaker(engine), clock)
        app.state.runtime = runtime

        try:
            async with httpx.AsyncClient() as http:
                worker = DeliveryWorker(runtime.sessions, http, clock, settings)
                task = asyncio.create_task(worker.run()) if settings.worker_enabled else None
                try:
                    yield
                finally:
                    if task is not None:
                        task.cancel()  # graceful shutdown (lease release) is #4
                        with contextlib.suppress(asyncio.CancelledError):
                            await task
        finally:
            await engine.dispose()

    app = FastAPI(
        title="Benji Webhooks",
        version="0.1.0",
        lifespan=lifespan,
        generate_unique_id_function=_operation_id,
    )
    install_problem_handlers(app)
    app.include_router(endpoints.router)
    app.include_router(events.router)
    app.include_router(deliveries.router)
    if settings.mock_receiver_enabled:
        app.include_router(mock_receiver.router)

    default_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        return use_problem_media_type(default_openapi())

    app.openapi = openapi
    return app


def _operation_id(route: APIRoute) -> str:
    """`create_endpoint` rather than FastAPI's `create_endpoint_endpoints_post`."""
    return route.name

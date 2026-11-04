"""The delivery worker: claims due deliveries and makes their attempts.

It runs as an asyncio task in the API process but shares no in-memory state with it; everything
goes through the database (ADR 0001), so it could run as its own process unchanged.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from webhooks.clock import Clock
from webhooks.domain import signing
from webhooks.domain.enums import AttemptOutcome
from webhooks.services import deliveries
from webhooks.services.deliveries import AttemptResult, ClaimedDelivery, Lease
from webhooks.settings import Settings

logger = logging.getLogger(__name__)

USER_AGENT = "benji-webhooks/0.1"


class DeliveryWorker:
    """A continuous pool: up to `worker_concurrency` attempts in flight, refilled as each ends."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        http: httpx.AsyncClient,
        clock: Clock,
        settings: Settings,
    ) -> None:
        self._sessions = sessions
        self._http = http
        self._clock = clock
        self._settings = settings
        self._policy = settings.retry_policy
        self._lease_duration = timedelta(seconds=settings.webhook_lease_seconds)
        self._stopping = asyncio.Event()
        self._in_flight: dict[asyncio.Task[None], ClaimedDelivery] = {}

    def stop(self) -> None:
        """Stops claiming. `run` then drains the in-flight attempts and returns."""
        self._stopping.set()

    async def run(self) -> None:
        try:
            while not self._stopping.is_set():
                await self._fill()
                await self._wait_for_a_free_slot_or_the_next_poll()
        finally:
            await self._shut_down()

    async def run_once(self) -> bool:
        """Claims and attempts one due delivery, without the pool. Returns whether there was one."""
        claimed = await self._claim()
        if claimed is None:
            return False
        await self._process(claimed)
        return True

    async def reclaim_expired(self) -> int:
        async with self._sessions() as session:
            reclaimed = await deliveries.reclaim_expired(
                session,
                now=self._clock.now(),
                lease_duration=self._lease_duration,
                policy=self._policy,
            )
        if reclaimed:
            logger.warning("reclaimed %d expired leases as interrupted attempts", reclaimed)
        return reclaimed

    async def _fill(self) -> None:
        try:
            await self.reclaim_expired()
            while len(self._in_flight) < self._settings.worker_concurrency:
                if self._stopping.is_set() or (claimed := await self._claim()) is None:
                    return
                task = asyncio.create_task(self._process(claimed))
                self._in_flight[task] = claimed
                task.add_done_callback(self._finished)
        except Exception:
            logger.exception("delivery worker iteration failed")

    async def _wait_for_a_free_slot_or_the_next_poll(self) -> None:
        stopping = asyncio.create_task(self._stopping.wait())
        try:
            await asyncio.wait(
                {stopping, *self._in_flight},
                timeout=self._settings.worker_poll_interval_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            stopping.cancel()

    def _finished(self, task: asyncio.Task[None]) -> None:
        claimed = self._in_flight.pop(task)
        if not task.cancelled() and (error := task.exception()) is not None:
            # Its lease will expire and be reclaimed, so the delivery isn't stranded.
            logger.error("delivery %s attempt crashed", claimed.lease.delivery_id, exc_info=error)

    async def _shut_down(self) -> None:
        """Gives in-flight attempts the shutdown timeout, then records the rest as interrupted."""
        claims = dict(self._in_flight)
        if not claims:
            return
        _, unfinished = await asyncio.wait(
            set(claims), timeout=self._settings.worker_shutdown_timeout
        )
        for task in unfinished:
            task.cancel()
        await asyncio.gather(*unfinished, return_exceptions=True)
        for task in unfinished:
            claimed = claims[task]
            result = deliveries.interrupted(
                started_at=claimed.claimed_at, now=self._clock.now(), why="worker shut down"
            )
            try:
                await self._record(claimed.lease, result)
            except Exception:  # keep releasing the others; this lease expires and is reclaimed
                logger.exception("could not release delivery %s", claimed.lease.delivery_id)

    async def _claim(self) -> ClaimedDelivery | None:
        async with self._sessions() as session:
            return await deliveries.claim_next(
                session, now=self._clock.now(), lease_duration=self._lease_duration
            )

    async def _process(self, claimed: ClaimedDelivery) -> None:
        # The claim is committed and its session closed: nothing is held open during the call.
        result = await self._attempt(claimed)
        await self._record(claimed.lease, result)

    async def _record(self, lease: Lease, result: AttemptResult) -> None:
        async with self._sessions() as session:
            status = await deliveries.record_attempt(session, lease, result, self._policy)
        if status is None:
            logger.warning(
                "delivery %s: lease lost, discarded a %s result", lease.delivery_id, result.outcome
            )
        else:
            logger.info("delivery %s attempt: %s → %s", lease.delivery_id, result.outcome, status)

    async def _attempt(self, claimed: ClaimedDelivery) -> AttemptResult:
        started_at = self._clock.now()
        delivery_id = claimed.lease.delivery_id
        timeout = self._settings.webhook_request_timeout_seconds
        headers = {
            "content-type": "application/json",
            "user-agent": USER_AGENT,
            # A fresh timestamp per attempt keeps it inside receivers' tolerance window.
            **signing.signature_headers(claimed.secret, delivery_id, started_at, claimed.body),
        }
        try:
            # httpx's timeout is per connect/read/write; this one bounds the whole request.
            async with asyncio.timeout(timeout):
                response = await self._http.post(
                    claimed.url,
                    content=claimed.body,
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=False,
                )
        except (httpx.TimeoutException, TimeoutError) as error:
            # Outcome unknown: the receiver may have processed it. `webhook-id` lets it dedupe.
            return self._failure(started_at, headers, AttemptOutcome.TIMEOUT, error)
        except httpx.RequestError as error:  # anything else short of a usable response
            return self._failure(started_at, headers, AttemptOutcome.CONNECTION_ERROR, error)

        return AttemptResult(
            started_at=started_at,
            finished_at=self._clock.now(),
            request_headers=headers,
            outcome=AttemptOutcome.RESPONSE,
            response_status=response.status_code,
            response_body=response.content,
            retry_after=response.headers.get("retry-after"),
        )

    def _failure(
        self,
        started_at: datetime,
        headers: dict[str, str],
        outcome: AttemptOutcome,
        error: Exception,
    ) -> AttemptResult:
        return AttemptResult(
            started_at=started_at,
            finished_at=self._clock.now(),
            request_headers=headers,
            outcome=outcome,
            error=str(error) or type(error).__name__,
        )

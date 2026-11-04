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
from webhooks.services.deliveries import AttemptResult, ClaimedDelivery
from webhooks.settings import Settings

logger = logging.getLogger(__name__)

USER_AGENT = "benji-webhooks/0.1"


class DeliveryWorker:
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

    async def run(self) -> None:
        """Polls until cancelled. One attempt at a time for now; the pool is #4."""
        while True:
            try:
                worked = await self.run_once()
            except Exception:
                logger.exception("delivery worker iteration failed")
                worked = False
            if not worked:
                await asyncio.sleep(self._settings.worker_poll_interval_seconds)

    async def run_once(self) -> bool:
        """Claims and attempts one due delivery. Returns whether there was one."""
        async with self._sessions() as session:
            claimed = await deliveries.claim_next(
                session,
                now=self._clock.now(),
                lease_duration=timedelta(seconds=self._settings.webhook_lease_seconds),
            )
        if claimed is None:
            return False

        # The claim is committed and its session closed: nothing is held open during the call.
        result = await self._attempt(claimed)

        async with self._sessions() as session:
            status = await deliveries.record_attempt(session, claimed, result)
        logger.info("delivery %s attempt: %s → %s", claimed.delivery_id, result.outcome, status)
        return True

    async def _attempt(self, claimed: ClaimedDelivery) -> AttemptResult:
        started_at = self._clock.now()
        headers = {
            "content-type": "application/json",
            "user-agent": USER_AGENT,
            # A fresh timestamp per attempt, so receivers' tolerance window never rejects a retry.
            **signing.signature_headers(
                claimed.secret, claimed.delivery_id, started_at, claimed.body
            ),
        }
        try:
            response = await self._http.post(
                claimed.url,
                content=claimed.body,
                headers=headers,
                timeout=self._settings.webhook_request_timeout_seconds,
                follow_redirects=False,
            )
        except httpx.TimeoutException as error:
            # Outcome unknown: the receiver may have processed it. `webhook-id` lets it dedupe.
            return self._failure(started_at, headers, AttemptOutcome.TIMEOUT, error)
        except httpx.TransportError as error:
            return self._failure(started_at, headers, AttemptOutcome.CONNECTION_ERROR, error)

        return AttemptResult(
            started_at=started_at,
            finished_at=self._clock.now(),
            request_headers=headers,
            outcome=AttemptOutcome.RESPONSE,
            response_status=response.status_code,
            response_body=response.content,
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

# Implementation Plan

A webhook notification system for Benji: customers register endpoints, subscribe them to event types, and receive signed, retried, deduplicated notifications. An ops dashboard shows every delivery and attempt live.

Produced in an AI-assisted design interview (see [AI_USAGE.md](./AI_USAGE.md)). Vocabulary is defined in [GLOSSARY.md](../GLOSSARY.md); hard-to-reverse decisions are in [adr/](./adr/).

**Status:** pre-build. This will be revised against what was actually built.

## Approach

| Area | Choice |
|---|---|
| Backend | Python ≥3.12, FastAPI, SQLAlchemy 2 (async), Pydantic, `uv` |
| Storage + queue | SQLite (WAL) as both store and delivery queue: [ADR 0001](./adr/0001-database-as-delivery-queue.md) |
| Worker | asyncio task in the API process, sharing no in-memory state with it (can be split out unchanged) |
| Signing | Standard Webhooks, HMAC-SHA256, per-endpoint `whsec_` secret: [ADR 0002](./adr/0002-standard-webhooks-signing.md) |
| Frontend | Nuxt 3 (SPA mode) + Vue 3 + TypeScript, Nuxt UI v3, TanStack Vue Query, `pnpm` |
| Live updates | Polling (~1.5s while anything is non-terminal, backing off when idle) |
| Tests | pytest (backend behavior), Vitest (state layer), Playwright (3 e2e flows) |
| CI | GitHub Actions: lint + typecheck + pytest + Playwright |

### Backend shape

- **Pure domain modules** (no I/O): `signing` (sign/verify), `retry_policy` (backoff with full jitter, retryable classification).
- **Services**: `events` (submit, idempotency, fan-out) and `deliveries` (claim, record attempt, replay).
- **Worker**: a loop that orchestrates services. The HTTP client and `Clock` are injected, so tests control transport and time.
- **Thin routers**: Pydantic API schemas kept separate from ORM models. Errors are RFC 9457 `application/problem+json`.
- Schema is created with `create_all` on startup.

### Delivery lifecycle

1. **Submit**: `POST /events` with an `Idempotency-Key`. In one transaction it stores the Event and creates one Delivery (`pending`) per *enabled* endpoint subscribed to the type. This is a transactional outbox: endpoints are snapshotted at submit time.
2. **Claim**: the worker polls every 0.5s and atomically claims due `pending` rows with a 30s lease (status becomes `in progress`), running up to 10 attempts concurrently. Expired leases are reclaimed.
3. **Attempt**: the worker signs the body and POSTs with a 10s timeout. Each Attempt records timing, HTTP status or error class, the request headers sent, and the response body truncated to 2KB.
4. **Outcome**: a 2xx means `succeeded`. Any non-2xx, timeout, or connection error schedules a retry, or sets `failed` once attempts are exhausted.
5. **Replay**: an operator returns a `failed` delivery to `pending`. Its attempt history continues and it keeps the same `webhook-id`.

**Retry policy:** 6 attempts, exponential backoff with full jitter (base 2s, cap 5min), honoring `Retry-After` on 429/503. All values come from settings; tests override them.

**Disabled endpoints** (Stripe/Svix model): fan-out skips them. A pending delivery whose endpoint was disabled is marked `failed` (`endpoint_disabled`) with no HTTP call, and the operator replays it after re-enabling. Nothing is flushed automatically on re-enable, which avoids firing a burst of stale events at an endpoint that was probably broken.

### Guarantees (stated precisely)

Exactly-once delivery over HTTP isn't possible, so we promise:

- **No duplicate events**: the same idempotency key with the same payload returns the original event (`deduplicated: true`, no new deliveries). The same key with a different payload returns 409.
- **At most one delivery per event–endpoint pair**, enforced by a DB unique constraint.
- **At-least-once attempts, receiver-dedupable**: every attempt and replay of a delivery carries the same `webhook-id`.
- **No ordering guarantee** across events. The envelope `timestamp` lets receivers order events themselves.

Event envelope: `{ id, type, timestamp, data }`. Supported types: `reward_transaction_created`, `campaign_updated`, `member_account_linked`. `data` is free-form JSON.

### Frontend shape

- **API layer**: a client typed from FastAPI's OpenAPI (`openapi-typescript` + `openapi-fetch`), plus a single `ApiError` normalizer.
- **State layer**: feature composables over Vue Query (`useEndpoints`, `useTriggerEvent`, `useDeliveries`, …) that own loading, error, and in-flight state, polling, and invalidation.
- **UI**: pages and components only render state and call composables.
- **Errors**: mutation failures show a toast; query failures show an inline error with retry. The treatment is the same in every view.

### Dashboard

- **Endpoints**: list, create (signing secret shown once in a modal), enable/disable.
- **Events**: trigger form (type picker plus JSON editor; the idempotency key persists until the input changes or the user clicks "new key", so resubmitting visibly dedupes), and a recent-events list with fan-out counts that drills down to its deliveries.
- **Deliveries**: live table filtered by status and endpoint, status count chips (separate aggregate query), newest 50 with keyset "load more" (polling refreshes the first page only), and an expandable row with payload, attempt log, and Replay.

### Tests

- **pytest**: backoff and jitter bounds, retryable classification, `Retry-After`; retry-to-success and retry-to-exhaustion (fake clock + httpx `MockTransport`); idempotent resubmit, 409 on conflict, unique constraint; replay continuing the history with the same `webhook-id`; sign/verify round-trip, tampering, stale timestamp; lease reclaim; disabled-endpoint handling.
- **Vitest**: `ApiError` normalization and a polling composable.
- **Playwright**, against a test-only Node receiver with OK and always-500 modes: (1) create an endpoint and see the secret once; (2) trigger, watch it reach `succeeded` live, resubmit and see the dedup notice; (3) failing receiver → `failed` → flip to OK → replay → `succeeded`.

## Build order and cut line

1. Backend core + pytest suite
2. Frontend views
3. Playwright e2e
4. CI
5. README / PLAN / AI note polish

If time runs short, cut in this order: CI, then the Events list (keeping the trigger form), then the count chips. The backend tests and the dashboard requirements are never cut.

## Deliberately cut

- **Auth and multi-tenancy**: single implicit customer. The brief requires neither.
- **Built-in demo receivers/sinks** and a fast demo retry profile.
- **Endpoint edit/delete**, secret rotation, per-type payload schemas.
- **Pause/hold semantics** for endpoints, bulk replay.
- **Alembic migrations**, data retention/cleanup.
- **SSRF protection**: URLs are validated as `http(s)` only, and loopback is needed for local testing.
- **Charts and search** in the dashboard.

## With more time

- Postgres + `SKIP LOCKED` and separate worker processes (ADR 0001's scale-out path).
- SSE/WebSocket as a cache-invalidation hint on top of polling.
- Endpoint pause/resume with controlled drain, and bulk replay ("recover since T").
- Secret rotation with dual signatures (supported by the Standard Webhooks header format).
- Automatic endpoint disabling after sustained failure, with an alert.
- SSRF guard (block private ranges, pin resolved IPs).
- Auth, multi-tenant customers, per-tenant rate limits.
- Retention policy for events and attempts.

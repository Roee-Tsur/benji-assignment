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
| Disabled endpoints | Fail pending deliveries, recover by replay: [ADR 0003](./adr/0003-disable-fails-pending-deliveries.md) |
| Frontend | Nuxt 4 (SPA mode) + Vue 3 + TypeScript, Nuxt UI v4, TanStack Vue Query, `pnpm` |
| Frontend state | Server state in Vue Query only, no Pinia: [ADR 0004](./adr/0004-server-state-in-vue-query.md) |
| Live updates | Polling (~1.5s while anything is non-terminal, backing off when idle) |
| Demo/test receiver | Built-in mock receiver mounted in the API behind a setting |
| Tests | pytest (backend behavior), Vitest (state layer), Playwright (3 e2e flows) |
| CI | GitHub Actions: lint + typecheck + pytest + Playwright |

### Backend shape

- **Pure domain modules** (no I/O): `signing` (sign/verify), `retry_policy` (backoff with full jitter, outcome classification, `Retry-After` parsing).
- **Services**: `events` (submit, idempotency, fan-out), `deliveries` (claim, record attempt, replay), and `endpoints` (create, enable/disable).
- **Worker**: a loop that orchestrates services. The HTTP client and `Clock` are injected, so tests control transport and time.
- **Mock receiver** (`/mock/*`, enabled by `MOCK_RECEIVER_ENABLED`, on by default locally): verifies each request's signature (looking up the secret via `webhook-id`) and answers by mode:
  - `ok` → 200
  - `fail` → 500
  - `flaky?n=` → fails the first *n* attempts of each delivery, then 200
  - `slow?s=` → sleeps, then 200; the only way to see `in progress` with your own eyes

  Playwright uses the same receiver, so there is no separate test receiver.
- **Thin routers**: Pydantic API schemas kept separate from ORM models. Errors are RFC 9457 `application/problem+json`.
- Schema is created with `create_all` on startup.
- IDs are prefixed (`ep_`, `evt_`, `dlv_`, `att_`). The delivery ID is the `webhook-id`.
- A delivery counts attempts two ways: `attempt_count` over its whole life (it numbers attempts, so numbering continues across replays) and `attempts_used` / `attempt_budget` within the current budget (what the UI shows as "attempt 3/6", and what a replay resets).
- SQLite transactions start at the first write, so reads before it aren't isolated. Anything that must be atomic is a single conditional statement or a unique constraint, never a read followed by a write.

### Delivery lifecycle

1. **Submit**: `POST /events` with a required `Idempotency-Key`. In one transaction it stores the Event and creates one Delivery (`pending`) per *enabled* endpoint subscribed to the type. This is a transactional outbox: endpoints are snapshotted at submit time. The envelope is serialized once and the bytes are stored; every attempt sends exactly those bytes.
2. **Claim**: a continuous worker pool keeps up to 10 attempts in flight and claims more as soon as a slot frees, so it never waits on a batch. A claim is a single `UPDATE … RETURNING` that:
   - picks due `pending` rows;
   - sets `in progress`, a fresh `lease_token`, and a 30s lease expiry.
3. **Attempt**: just before sending, the worker re-checks the endpoint is enabled. It signs with a fresh `webhook-timestamp`, so replays aren't rejected by receivers' 5-minute tolerance, then POSTs with a 10s timeout. No DB transaction is held open during the HTTP call. The response body is stored truncated to 2KB. Each Attempt records:
   - timing;
   - the request headers sent;
   - the truncated response body;
   - the outcome: an HTTP status, `timeout`, `connection_error`, or `interrupted` (lease expired or shutdown mid-attempt). A timeout is shown as "outcome unknown": the receiver may have processed it, and `webhook-id` lets it dedupe the retry.
4. **Write-back**: results are written only `WHERE id = ? AND lease_token = ?`. A late result from a lost lease changes nothing, so it can't overwrite a newer attempt.
5. **Outcome**:
   - 2xx → `succeeded`.
   - 410 → `failed`, reason `endpoint_gone`; no retry.
   - Anything else (including 3xx, since redirects aren't followed), timeouts, and connection errors → retry, or `failed` with reason `attempts_exhausted` once the attempt budget is spent.
6. **Lease reclaim**: an expired lease is recorded as an `interrupted` attempt, which counts against the budget so a poison delivery can't loop forever. The delivery returns to `pending`.
7. **Replay** (`POST /deliveries/{id}/replay`): a `failed` delivery returns to `pending` with a fresh attempt budget. Attempt numbers keep counting up and it keeps the same `webhook-id`. Replaying anything not `failed`, or a delivery whose endpoint is disabled, returns 409. `POST /endpoints/{id}/replay-failed` replays every failed delivery of an endpoint in one conditional `UPDATE`, for recovery after an outage.

**Retry policy:** 6 attempts per budget, exponential backoff with full jitter (base 2s, cap 5min). `Retry-After` is honored in its delta-seconds form and clamped to the cap. Settings: `WEBHOOK_RETRY_MAX_ATTEMPTS`, `WEBHOOK_RETRY_BASE_SECONDS`, `WEBHOOK_RETRY_CAP_SECONDS`, validated at startup. The pure `domain/retry_policy` module holds all three: `backoff`, `retry_delay` (`Retry-After` or backoff), and `classify` (2xx → success, 410 → endpoint gone, anything else or no response → retryable). The README shows the values that make retries visible in seconds; tests override them.

**Disabled endpoints** ([ADR 0003](./adr/0003-disable-fails-pending-deliveries.md)): disabling an endpoint and failing its `pending` deliveries (reason `endpoint_disabled`) happen in one transaction. Attempts already `in progress` finish. Fan-out skips disabled endpoints, and the claim-time check covers races. Re-enabling flushes nothing; the operator uses replay-failed.

**SQLite specifics:** WAL mode, `busy_timeout` set, and an index on `(status, next_attempt_at)`.

**Graceful shutdown:** stop claiming, give in-flight attempts up to the request timeout to finish, then record any still running as `interrupted` and release their leases back to `pending`. Without this, rows would sit `in progress` for 30s after a restart.

### Guarantees (stated precisely)

Exactly-once delivery over HTTP isn't possible, so we promise:

- **No duplicate events**: the `Idempotency-Key` is required (400 if missing or blank). The same key with the same payload returns the original event (`deduplicated: true`, no new deliveries); the same key with a different payload returns 422 (per the IETF Idempotency-Key draft). "Same payload" means the same type and JSON-equal `data`: key order is ignored, but `1`, `1.0`, and `true` differ. Implemented as insert-and-catch on the unique key, not check-then-insert, so concurrent resubmits can't race.
- **At most one delivery per event–endpoint pair**, enforced by a DB unique constraint.
- **At-least-once attempts, receiver-dedupable**: every attempt and replay of a delivery carries the same `webhook-id`.
- **No ordering guarantee** across events. The envelope `timestamp` lets receivers order events themselves.

Event envelope: `{ id, type, timestamp, data }`. Supported types: `reward_transaction_created`, `campaign_updated`, `member_account_linked`. `data` is free-form JSON. An event whose serialized envelope (the bytes every attempt sends) is over 64 KiB is rejected with 413.

### Signing details

- The HMAC key is the **base64-decoded** part of the `whsec_` secret, not the literal string.
- The signed content is `{webhook-id}.{webhook-timestamp}.{body}`, where the body is the stored bytes.
- Every attempt is re-signed with a fresh timestamp.
- An interop test verifies our signatures with the official `standardwebhooks` PyPI package, which catches key-encoding bugs that a round-trip through our own `verify()` would miss.

### Frontend shape

- **API layer**: a client typed from FastAPI's OpenAPI (`openapi-typescript` + `openapi-fetch`), plus a single `ApiError` normalizer. CI fails if the generated client is out of date with the backend schema, so type safety holds end to end.
- **State layer** ([ADR 0004](./adr/0004-server-state-in-vue-query.md)):
  - feature composables over Vue Query (`useEndpoints`, `useTriggerEvent`, `useDeliveries`, …) own loading, error, and in-flight state, polling, and invalidation;
  - a query key factory makes invalidation targeted;
  - filters and the open delivery live in the URL, not in a store.
- **UI**: pages and components only render state and call composables.
- **Errors**: mutation failures show a toast; query failures show an inline error with retry. The treatment is the same in every view.
- **Optimistic replay**: the row flips to `pending` immediately and rolls back with a toast if the request fails.
- **Accessibility**:
  - status badges use color, an icon, and text, never color alone;
  - rows expand from the keyboard and the slideover traps focus;
  - Playwright runs an axe check on every view.
- Desktop-first: an ops dashboard, with no mobile layout.

### Staying accurate over time

- The deliveries list is an infinite query. Each poll refetches **every loaded page**, not just the first, and "load more" bounds the cost.
- An expanded row's detail query (payload and attempt log) polls on its own while its delivery is non-terminal.
- The status count chips come from a separate aggregate query, so they're right regardless of paging.
- Every view reads the DB, which is also the queue, so there's no second source of truth to drift.
- Making "live" visible:
  - rows briefly highlight when their status changes;
  - a "live · updated 2s ago" indicator shows polling health and turns into an error state when polls fail;
  - polling pauses while the browser tab is hidden and refetches when it becomes visible.

### Dashboard

- **Endpoints**: list, create (signing secret shown once in a modal), enable/disable, and "replay failed" per endpoint.
- **Events**: trigger form with a type picker and a JSON editor prefilled with a sample payload per type. The editor validates JSON live and has a "format" button. The idempotency key persists until the input changes or the user clicks "new key", so resubmitting visibly dedupes. Below it, a recent-events list with fan-out counts that drills down to its deliveries.
- **Deliveries**: live table filtered by status and endpoint, with the filters held in the URL (`?status=failed&endpoint=…`) so views can be deep-linked and the back button works. It has status count chips and the newest 50 plus keyset "load more". Pending rows show "attempt 3/6 · next in 12s" (from `next_attempt_at`) and failed rows show their failure reason. Opening a delivery shows a slideover with its own URL, containing the payload, the attempt log, and Replay.

### Tests

- **pytest**:
  - backoff and jitter bounds, outcome classification (3xx, 410), `Retry-After` with clamping;
  - retry-to-success and retry-to-exhaustion (fake clock + httpx `MockTransport`);
  - required key, idempotent resubmit, 422 on mismatch, concurrent resubmit, unique constraint;
  - replay: fresh budget, numbering continues, same `webhook-id`, 409 cases, replay-failed;
  - signing: round-trip, tampering, stale timestamp, re-sign per attempt, and **interop with `standardwebhooks`**;
  - lease: reclaim as `interrupted`, and a stale `lease_token` write being discarded;
  - disable failing pending deliveries, graceful-shutdown lease release.
- **Vitest** (`@nuxt/test-utils` + MSW handlers typed from the OpenAPI schema):
  - `ApiError` normalization;
  - polling stops once every delivery is terminal and resumes when one isn't;
  - every loaded page refreshes;
  - optimistic replay rolls back on error;
  - the trigger form shows the dedup notice and the 422 mismatch;
  - URL ↔ filter sync.
- **Playwright**, against the built-in mock receiver:
  1. create an endpoint and see the secret once;
  2. trigger, watch it reach `succeeded` live, resubmit and see the dedup notice;
  3. `flaky?n=<max attempts>` → `failed` → Replay → `succeeded`.

  Each view also gets an axe accessibility check.

### Requirement traceability

Planned now; file and test links get filled in during the final docs-vs-code pass.

| Requirement (brief) | Mechanism | Proven by |
|---|---|---|
| Configurable subscriptions | Endpoint with a set of event types; fan-out by type | pytest: fan-out; e2e 1 |
| Reliable delivery | DB queue, backoff with jitter, leases | pytest: retry policy ([test_retry_policy.py](../backend/tests/test_retry_policy.py)), retry, lease reclaim, shutdown |
| Authenticated delivery | Standard Webhooks HMAC | pytest: signing + `standardwebhooks` interop ([test_signing.py](../backend/tests/test_signing.py)); mock receiver verification ([test_mock_receiver.py](../backend/tests/test_mock_receiver.py)) |
| Replay-able failures | Failure reason + Replay / replay-failed | pytest: replay; e2e 3 |
| Unique delivery | Idempotency-Key, unique (event, endpoint), stable `webhook-id` | pytest: idempotency, constraint (resubmit, 422 mismatch, concurrent resubmit, and unique constraint: [test_events_api.py](../backend/tests/test_events_api.py), [test_app.py](../backend/tests/test_app.py)); e2e 2 |
| Observable delivery | Deliveries view, attempt log | e2e 2, 3 |
| Endpoint management, secret once | Endpoints view | e2e 1 |
| Event trigger, dedup surfaced | Trigger form | e2e 2 |
| Live delivery view | Polling all loaded pages + detail | e2e 2, 3; Vitest polling |
| Attempt inspection, replay | Delivery slideover, optimistic replay | e2e 3; Vitest rollback |
| Async UX, consistent errors | Vue Query composables, `ApiError` | Vitest `ApiError`, trigger form |
| API / state / UI separation | `api/`, `composables/`, components | Code layout |

## Build order and cut line

The work is tracked as GitHub issues #1–#11, one session and PR each, run with the `work-ticket` skill. Each ticket states its dependencies and a suggested effort level.

The role is frontend-leaning, so the dashboard gets the extra depth, and the backend is held to what keeps the dashboard truthful.

1. **Thin vertical slice:** create endpoint → trigger → worker → mock receiver → `succeeded` visible in a minimal dashboard.
2. **Deepen the backend:** retries, leases and fencing, replay, disable, shutdown, plus the pytest suite.
3. **Deepen the dashboard:** deliveries table, filters, attempt log, retry countdown, async UX.
4. **UI polish pass** (#11): a fresh session uses the app in the browser and tightens visual hierarchy, consistency, empty states, and microcopy.
5. Playwright e2e.
6. CI.
7. **Final pass:** traceability links, a docs-vs-code check, a separate AI review session against `ASSIGNMENT.md`, and a README with a GIF of the live view and screenshots.

If time runs short, cut in this order: CI, then the Events list (keeping the trigger form), then the count chips. The backend tests, the dashboard requirements, and the polish pass are never cut.

## Deliberately cut

- **Auth and multi-tenancy**: single implicit customer. The brief requires neither.
- **A named fast "demo" retry profile**: the retry env vars are documented instead.
- **Endpoint edit/delete**, secret rotation, per-type payload schemas.
- **Pause/hold semantics** for endpoints ([ADR 0003](./adr/0003-disable-fails-pending-deliveries.md)), and time-ranged recovery ("replay since T").
- **Alembic migrations**, data retention/cleanup.
- **SSRF protection**: URLs are validated as `http(s)` only, and loopback is needed for local testing.
- **Charts and search** in the dashboard. A mobile layout, Storybook, visual regression tests.
- **Backend refinements traded for frontend depth**: a per-endpoint in-flight cap, `Retry-After` HTTP-date parsing, and streaming response capture.

## With more time

- Postgres + `SKIP LOCKED` and separate worker processes (ADR 0001's scale-out path).
- A per-endpoint in-flight cap, so one slow endpoint can't take every worker slot.
- `Retry-After` in HTTP-date form, and streaming response capture that stops reading at 2KB.
- A request-size limit before the body is parsed (today the 64 KiB check runs on the parsed event).
- Delta polling (`updated_after` cursor merged into the cache by id), or SSE as an invalidation hint, instead of refetching loaded pages.
- Endpoint pause/resume with a controlled drain, and "replay since T".
- Secret rotation with dual signatures (supported by the Standard Webhooks header format).
- Automatic endpoint disabling after sustained failure (or on 410), with an alert.
- SSRF guard (block private ranges, pin resolved IPs).
- Auth, multi-tenant customers, per-tenant rate limits.
- Retention policy for events and attempts.

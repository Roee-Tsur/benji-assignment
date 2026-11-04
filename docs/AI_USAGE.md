# AI Usage

How AI was used to build this, session by session. Each entry is short: what I asked for, how I steered, and what I overrode. Full chat transcripts are added to `docs/transcripts/` after I review them.

Tooling: Claude Code (Opus) in the desktop app.

## Sessions

### 1. Design interview → plan (2026-11-04)

- **Asked:** run a structured "grill" over the assignment before writing code, with the explicit goal of impressing reviewers while respecting the one-day time box and not bloating scope.
- **Process:** the AI proposed the design tree in rounds of numbered decisions, each with a recommendation. I accepted, amended, or rejected each one. Terms went into `GLOSSARY.md` and hard-to-reverse choices into ADRs as they settled.
- **Where I steered:**
  - Dropped the fast "demo" retry profile and the built-in mock receivers. They weren't needed for the brief.
  - Asked for Playwright e2e on top of the backend-heavy test plan.
  - Asked it to confirm that the brief doesn't require auth or multi-tenancy before cutting them.
  - Challenged the first take on disabled endpoints ("does re-enabling flush everything? is that industry standard?"). That surfaced that Stripe and Svix *don't* auto-flush, and the design switched to "mark failed, replay explicitly".
- **Cross-checked with a parallel session:** I ran a separate AI session that researched other public submissions of this take-home and came back with a gap list. I brought it back here and asked this session to triage it rather than apply it blindly. The result:
  - **Adopted as-is:** worker correctness (lease fencing, per-endpoint concurrency cap, graceful shutdown), signing details plus an interop test against the official `standardwebhooks` package, and explicit replay rules.
  - **Adopted the goal with a simpler mechanism:** for the stale-live-view issue, refetch all loaded pages instead of a delta-merge cursor.
  - **Reversed my own earlier cut** (the built-in receiver), because a reviewer otherwise has nowhere to point an endpoint, and it replaces the test-only receiver anyway.
- **Ticketing for context hygiene:** I asked for the plan to be split into tickets sized for one fresh session each, with an effort level per ticket. We ended up with 10 GitHub issues, one PR per ticket that I merge, and a committed `work-ticket` skill so every session follows the same steps: orient, test-first, verify, `/code-review`, update docs, open a PR. Effort is set to *xhigh* only where races or independent review make depth worth the cost.
- **Re-weighted for the role:** I told it the role is frontend-leaning and asked what should change. It proposed adding frontend depth and paying for it with backend cuts:
  - **Added:** URL-held filters and deep links, optimistic replay with rollback, visible "live" cues, a query key factory with ADR 0004 (no Pinia), MSW-backed component tests, an axe accessibility check, a CI check that the generated API client is current, and a dedicated UI polish ticket.
  - **Cut:** three backend refinements that don't change what the dashboard shows (per-endpoint cap, HTTP-date `Retry-After`, streaming capture).
- **Output:** [PLAN.md](./PLAN.md), [GLOSSARY.md](../GLOSSARY.md), [ADR 0001](./adr/0001-database-as-delivery-queue.md), [ADR 0002](./adr/0002-standard-webhooks-signing.md), [ADR 0003](./adr/0003-disable-fails-pending-deliveries.md), [ADR 0004](./adr/0004-server-state-in-vue-query.md).

### 2. Ticket #1: backend walking skeleton (2026-11-04)

- **Asked:** run `/work-ticket 1`, building the FastAPI + SQLite skeleton (schema, API, signing, minimal worker, mock receiver) that every later ticket copies.
- **Process:** the AI restated the ticket and listed the choices the plan left open before writing code: a required `Idempotency-Key` from day one so the frontend generates against the final shape, no fake failure reason until #4, two attempt counters (lifetime vs. current budget), and prefixed IDs. I approved them and the `uv` install it needed. Then it worked test-first: signing first, with the `standardwebhooks` interop test, then API, worker, and mock receiver tests before the code.
- **Checks beyond the tests:** it mutation-tested the "no transaction held during the HTTP call" test, confirming the test fails when the claim's transaction is left open, and ran the acceptance flow by hand with curl against `make dev-backend`.
- **Review:** `/code-review` found 9 issues. It fixed 7: request errors other than transport errors left a delivery stuck `in progress`, problem responses dropped the `Allow` header, and 5 smaller cleanups. It skipped 2 that belong to later tickets: shutdown mid-attempt (#4) and the concurrent same-key race (#3).
- **Output:** `backend/` (47 pytest tests, ruff, strict pyright) and root `Makefile` targets.

### 3. Ticket #2: frontend walking skeleton (2026-11-04)

- **Asked:** run `/work-ticket 2` from the ticket #1 session, stacked on the unmerged #1 branch (a GitHub incident delayed the merge): the Nuxt 4 SPA, a typed API layer, the Vue Query state layer, the app shell, minimal pages, and the Vitest + MSW harness.
- **Process:** the AI scaffolded from the official Nuxt UI starter and resolved the open choices on its own, without stopping for approval:
  - a `/api` proxy instead of CORS on the backend;
  - schema generation straight from the FastAPI app, so the stale check needs no running server;
  - closed sets as `Record<…>` tables keyed by the generated enums, so a new status or event type fails typecheck.
- **Checks beyond the tests:** it ran the acceptance flow in the browser (create, secret shown once, trigger, `succeeded`), triggered a second event from curl to show polling picks it up without a reload, changed a backend schema temporarily to see `gen:api --check` fail, and checked the new ESLint layering rule against deliberate violations.
- **Review:** `/code-review` found 8 issues, and it fixed all of them. The main ones: `mutateAsync` rejections went unhandled, a create that resolved after its modal closed could bring back the secret, one failed poll hid the loaded rows, and the generated schema depended on the local backend `.env`.
- **Where I steered:** coming from frameworks with a separate view model, I asked whether component logic like `submit`, `validate`, and `copySecret` should move out of the view. The AI's answer was that Vue's equivalent is a composable, and one-view glue stays in the component. Only reused or pure, testable logic moves out. I had it apply that rule: VueUse `useClipboard` replaced the hand-written copy, and JSON parsing moved to `app/domain/` with tests. I also had the rule recorded in `CLAUDE.md` for later tickets.
- **Output:** `frontend/` (23 Vitest tests in Node and Nuxt projects, ESLint, `vue-tsc` over app and tests), `make dev` plus frontend coverage in `make lint` / `typecheck` / `test`.


### 4. Ticket #3: retry policy + idempotency hardening (2026-11-04)

- **Asked:** run `/work-ticket 3` in its own worktree, stacked on the unmerged #1 branch while #2 ran in parallel in the main checkout, and keep away from the shared `Makefile`.
- **Process:** test-first. The retry policy got table-driven tests (jitter bounds, cap, every classification, `Retry-After` clamping and ignored HTTP-dates). The concurrent-resubmit test was run against the old check-then-insert code first and reproduced the `UNIQUE constraint` 500 before the insert-and-catch fix.
- **Choices it made and flagged in the PR:** the 64 KiB limit measures the serialized envelope (what receivers get), a missing key is a 400 by declaring the header optional and checking it in the router, and `RetryPolicy` owns the attempt budget's size.
- **Review:** `/code-review` found 7 issues. It fixed 5: `True == 1 == 1.0` let different payloads dedupe, bad retry settings failed per request instead of at startup, blank keys were accepted, other integrity errors were masked, and an odd `Retry-After` sentinel. It recorded the request-size guard under "With more time" and the PLAN wording under docs.
- **Output:** `domain/retry_policy.py`, hardened `POST /events`, 107 pytest tests.

### 5. Ticket #4: worker reliability (2026-11-04)

- **Asked:** run `/work-ticket 4` in its own worktree, stacked on the unmerged #3 branch (itself on #1), while #2 kept the main checkout.
- **Process:** test-first. A fake clock went into the test app first, so retries and leases are driven by moving time rather than sleeping. Then 18 failing worker tests covered every acceptance criterion: retry to success and exhaustion, 410, `Retry-After`, fresh signatures, 2 KB truncation, fencing, reclaim, the pool, and shutdown. The code came after. The stale-write test was mutation-checked: dropping the `lease_token` fence makes it fail.
- **Choices it made and flagged in the PR:** interrupted attempts (reclaimed or cut off by shutdown) go through the same settle rule as any retryable outcome, so the budget's "at most 6" holds even across restarts. The request timeout now bounds the whole request, because httpx's is per read.
- **Review:** `/code-review` (xhigh) found 15 candidates. It fixed 3: a lease no longer than the request timeout is now rejected at startup, one failed release no longer stops shutdown releasing the rest, and the shutdown wait defaults to the request timeout instead of a copy of it. It documented the shutdown settle rule in the plan and skipped the minor ones, listed in the PR.
- **Output:** a continuous worker pool with fenced write-back, lease reclaim, and graceful shutdown; 127 pytest tests.

### 6. Ticket #5: replay + disable (2026-11-04)

- **Asked:** run `/work-ticket 5` in its own worktree, stacked on the unmerged #4 branch (→ #3 → #1), and open the PR against `main` saying it merges after the stack.
- **Process:** test-first. Shared worker test helpers moved into `conftest.py` first. Then failing tests for disable, the claim-time re-check, replay and its 409s, replay-failed, the mock modes, and the `flaky?n=6` → failed → replay → succeeded flow, before the code.
- **Choices it made and flagged in the PR:** a pending delivery the claim finds on a disabled endpoint is failed, not skipped, so it can't sit `pending` forever. An in-flight attempt that would retry on a just-disabled endpoint fails with `endpoint_disabled` (the ADR's "dashboard misreports" reason applies). `flaky` counts requests per `webhook-id` on the receiver side, in memory, rather than reading the sender's attempt count.
- **Review:** `/code-review` (high) found 4 candidates. It fixed 1: the mock receiver held a pooled DB connection while `slow` slept. It skipped the minor ones, listed in the PR.
- **Output:** `POST /deliveries/{id}/replay`, `POST /endpoints/{id}/replay-failed`, disable per ADR 0003, `/mock/fail|flaky|slow`; 148 pytest tests.

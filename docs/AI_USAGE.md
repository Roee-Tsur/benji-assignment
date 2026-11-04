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


### Ticket #3: retry policy + idempotency hardening (2026-11-04)

- **Asked:** run `/work-ticket 3` in its own worktree, stacked on the unmerged #1 branch while #2 ran in parallel in the main checkout, and keep away from the shared `Makefile`.
- **Process:** test-first. The retry policy got table-driven tests (jitter bounds, cap, every classification, `Retry-After` clamping and ignored HTTP-dates). The concurrent-resubmit test was run against the old check-then-insert code first and reproduced the `UNIQUE constraint` 500 before the insert-and-catch fix.
- **Choices it made and flagged in the PR:** the 64 KiB limit measures the serialized envelope (what receivers get), a missing key is a 400 by declaring the header optional and checking it in the router, and `RetryPolicy` owns the attempt budget's size.
- **Review:** `/code-review` found 7 issues. It fixed 5: `True == 1 == 1.0` let different payloads dedupe, bad retry settings failed per request instead of at startup, blank keys were accepted, other integrity errors were masked, and an odd `Retry-After` sentinel. It recorded the request-size guard under "With more time" and the PLAN wording under docs.
- **Output:** `domain/retry_policy.py`, hardened `POST /events`, 107 pytest tests.

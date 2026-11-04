# AI Usage

How AI was used to build this, session by session. Each entry is short: what I asked for, how I steered, and what I overrode. Each entry links its full chat transcript in [`docs/transcripts/`](./transcripts/), named by entry number (`01-…md` is entry 1). They are rendered from the session logs: prompts and replies verbatim, tool calls one line each, tool output left out, local paths and my email redacted.

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
- **Transcript:** [01-design-interview.md](./transcripts/01-design-interview.md); the parallel research session: [01b-research-other-submissions.md](./transcripts/01b-research-other-submissions.md)

### 2. Ticket #1: backend walking skeleton (2026-11-04)

- **Asked:** run `/work-ticket 1`, building the FastAPI + SQLite skeleton (schema, API, signing, minimal worker, mock receiver) that every later ticket copies.
- **Process:** the AI restated the ticket and listed the choices the plan left open before writing code: a required `Idempotency-Key` from day one so the frontend generates against the final shape, no fake failure reason until #4, two attempt counters (lifetime vs. current budget), and prefixed IDs. I approved them and the `uv` install it needed. Then it worked test-first: signing first, with the `standardwebhooks` interop test, then API, worker, and mock receiver tests before the code.
- **Checks beyond the tests:** it mutation-tested the "no transaction held during the HTTP call" test, confirming the test fails when the claim's transaction is left open, and ran the acceptance flow by hand with curl against `make dev-backend`.
- **Review:** `/code-review` found 9 issues. It fixed 7: request errors other than transport errors left a delivery stuck `in progress`, problem responses dropped the `Allow` header, and 5 smaller cleanups. It skipped 2 that belong to later tickets: shutdown mid-attempt (#4) and the concurrent same-key race (#3).
- **Output:** `backend/` (47 pytest tests, ruff, strict pyright) and root `Makefile` targets.
- **Transcript:** [02-ticket-1-backend-skeleton.md](./transcripts/02-ticket-1-backend-skeleton.md)

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
- **Transcript:** [03-ticket-2-frontend-skeleton.md](./transcripts/03-ticket-2-frontend-skeleton.md)

### 4. Ticket #3: retry policy + idempotency hardening (2026-11-04)

- **Asked:** run `/work-ticket 3` in its own worktree, stacked on the unmerged #1 branch while #2 ran in parallel in the main checkout, and keep away from the shared `Makefile`.
- **Process:** test-first. The retry policy got table-driven tests (jitter bounds, cap, every classification, `Retry-After` clamping and ignored HTTP-dates). The concurrent-resubmit test was run against the old check-then-insert code first and reproduced the `UNIQUE constraint` 500 before the insert-and-catch fix.
- **Choices it made and flagged in the PR:** the 64 KiB limit measures the serialized envelope (what receivers get), a missing key is a 400 by declaring the header optional and checking it in the router, and `RetryPolicy` owns the attempt budget's size.
- **Review:** `/code-review` found 7 issues. It fixed 5: `True == 1 == 1.0` let different payloads dedupe, bad retry settings failed per request instead of at startup, blank keys were accepted, other integrity errors were masked, and an odd `Retry-After` sentinel. It recorded the request-size guard under "With more time" and the PLAN wording under docs.
- **Output:** `domain/retry_policy.py`, hardened `POST /events`, 107 pytest tests.
- **Transcript:** [04-ticket-3-retry-idempotency.md](./transcripts/04-ticket-3-retry-idempotency.md)

### 5. Ticket #4: worker reliability (2026-11-04)

- **Asked:** run `/work-ticket 4` in its own worktree, stacked on the unmerged #3 branch (itself on #1), while #2 kept the main checkout.
- **Process:** test-first. A fake clock went into the test app first, so retries and leases are driven by moving time rather than sleeping. Then 18 failing worker tests covered every acceptance criterion: retry to success and exhaustion, 410, `Retry-After`, fresh signatures, 2 KB truncation, fencing, reclaim, the pool, and shutdown. The code came after. The stale-write test was mutation-checked: dropping the `lease_token` fence makes it fail.
- **Choices it made and flagged in the PR:** interrupted attempts (reclaimed or cut off by shutdown) go through the same settle rule as any retryable outcome, so the budget's "at most 6" holds even across restarts. The request timeout now bounds the whole request, because httpx's is per read.
- **Review:** `/code-review` (xhigh) found 15 candidates. It fixed 3: a lease no longer than the request timeout is now rejected at startup, one failed release no longer stops shutdown releasing the rest, and the shutdown wait defaults to the request timeout instead of a copy of it. It documented the shutdown settle rule in the plan and skipped the minor ones, listed in the PR.
- **Output:** a continuous worker pool with fenced write-back, lease reclaim, and graceful shutdown; 127 pytest tests.
- **Transcript:** [05-ticket-4-worker-reliability.md](./transcripts/05-ticket-4-worker-reliability.md)

### 6. Ticket #5: replay + disable (2026-11-04)

- **Asked:** run `/work-ticket 5` in its own worktree, stacked on the unmerged #4 branch (→ #3 → #1), and open the PR against `main` saying it merges after the stack.
- **Process:** test-first. Shared worker test helpers moved into `conftest.py` first. Then failing tests for disable, the claim-time re-check, replay and its 409s, replay-failed, the mock modes, and the `flaky?n=6` → failed → replay → succeeded flow, before the code.
- **Choices it made and flagged in the PR:** a pending delivery the claim finds on a disabled endpoint is failed, not skipped, so it can't sit `pending` forever. An in-flight attempt that would retry on a just-disabled endpoint fails with `endpoint_disabled` (the ADR's "dashboard misreports" reason applies). `flaky` counts requests per `webhook-id` on the receiver side, in memory, rather than reading the sender's attempt count.
- **Review:** `/code-review` (high) found 4 candidates. It fixed 1: the mock receiver held a pooled DB connection while `slow` slept. It skipped the minor ones, listed in the PR.
- **Output:** `POST /deliveries/{id}/replay`, `POST /endpoints/{id}/replay-failed`, disable per ADR 0003, `/mock/fail|flaky|slow`; 148 pytest tests.
- **Transcript:** [06-ticket-5-replay-disable.md](./transcripts/06-ticket-5-replay-disable.md)

### 7. Ticket #7: Endpoints + Events views (2026-11-04)

- **Asked:** run `/work-ticket 7` in its own worktree, in parallel with #6 (Deliveries view) in another, and keep shared files to minimal, called-out changes.
- **Process:** it found the brief needed a `GET /events` that didn't exist and added it test-first. Then it messaged the #6 session to accept an `?event=` filter for the drill-down rather than editing deliveries files itself, and left notes in the shared folder. The frontend was test-first too: domain helpers, composables, then MSW component tests for the key lifecycle, dedup, 422, and show-once secret.
- **Caught along the way:** the first key-lifecycle tests passed for the wrong reason, because happy-dom drops headers given to `new Request()` as a `Headers` object and every key arrived as `null`. A test-only shim fixed the harness. The secret test was checked against a mutant: without `gcTime: 0` the secret stays in Vue Query's mutation cache for five minutes after the modal closes, and the test fails.
- **Choices it made and flagged in the PR:** the key is tied to the parsed type and data, so "Format" keeps it. The key is editable, which is how the 422 can be reached. A reused-key 422 shows inline instead of as a toast, through a `meta.toastError` hook on the shared mutation cache.
- **Review:** `/code-review` (high) found 7 issues. It fixed 6: `crypto.randomUUID` crashing on non-HTTPS hosts, two accessible-name mismatches, a missing events index, duplicated event schemas, and a misnamed composable file. The drill-down filter waits on #6.
- **Output:** Endpoints view (inline URL validation, enable toggle, replay failed), Events view (trigger form plus recent events), `GET /events`; 150 pytest tests and 42 Vitest tests.
- **Transcript:** [07-ticket-7-endpoints-events-views.md](./transcripts/07-ticket-7-endpoints-events-views.md)

### 8. Ticket #6: deliveries view (2026-11-04)

- **Asked:** run `/work-ticket 6` in its own worktree, in parallel with #7 (endpoints + events views), keeping to the deliveries page and its own composables and calling out any shared file in the PR.
- **Process:** the backend list had no filters, paging, or counts, so it added them first, test-first: filters, a keyset cursor on `(created_at, id)` (including ties within one fan-out), and `GET /deliveries/counts`. On the frontend, the pure parts (countdown text, outcome labels, status-change detection) got unit tests, and the Vue Query layer got MSW tests under fake timers before the code. The rollback test was mutation-checked: with the rollback removed, it fails.
- **Coordinating with #7:** it left #7 a note (in the shared notes folder and as a message): link the events drill-down to `/deliveries?event=<id>`. #6 owns the `event_id` filter, so #7 doesn't touch the deliveries API.
- **Checks beyond the tests:** in the browser, against `/mock/slow?s=3` and `/mock/flaky?n=2`, it sampled the DOM while deliveries ran. Rows went pending → in progress → succeeded with highlights, the countdown ticked, the open slideover's attempt log grew 0 → 2 → 3, a page-2 row updated after "load more", deep links survived a reload, a replay against a disabled endpoint rolled back with the 409 toast, and stopping the backend showed "Updates failing" and then recovered on its own.
- **Review:** `/code-review` (high) found 8 issues, and it fixed all of them. The main ones: a failed delivery's open detail stopped polling, so it went stale after a replay from elsewhere; a closed slideover kept polling; rollback restored the whole list snapshot; and a 1s clock re-rendered the whole table.
- **Output:** filtered, paged, counted `GET /deliveries`; the deliveries view (URL filters, status chips, live indicator, highlights, countdowns, load more, slideover, optimistic replay); 155 pytest and 47 Vitest tests.
- **Transcript:** [08-ticket-6-deliveries-view.md](./transcripts/08-ticket-6-deliveries-view.md)

### 9. Ticket #11: UI polish pass (2026-11-04)

- **Asked:** run `/work-ticket 11` in a fresh session, so it would look at the UI as a reviewer would rather than as its author. Use the real app in every state, fix only polish issues, and save before/after screenshots for the README.
- **Process:** it scripted headless Chrome against `make dev` and stubbed the API to force the loading, error, and empty states. That surfaced a real bug, not just polish: after a failed first load, Deliveries and Events flipped between the error and a false "No deliveries yet" on every poll, because Vue Query clears `error` when a fetch starts without data. It wrote a failing test for this first and mutation-checked it, then fixed it with `useLoadError`. The new formatters (relative time, durations, counts) were also test-first.
- **Polish:** skeleton rows instead of a premature "empty" message, empty states with next actions (via Nuxt UI's `UEmpty` rather than a hand-rolled component), relative times with the absolute time on hover, a slideover title that no longer collides with the close button, Format moved onto its field, a Cancel button in the create modal, a zero fan-out notice, and a sidebar mark with a color-mode toggle.
- **Review:** `/code-review` (high) found 9 issues and it fixed 8. The main ones: the load error outlived a filter change, the slideover still had the flicker, an empty placeholder page flashed "no matches", and Retry stayed disabled while polls ran. It skipped the mock-receiver hint that shows even with the receiver off.
- **Caught along the way:** the Nuxt test environment timed out on setup while `make dev` was running beside it, so it stopped the dev server for the test runs instead of raising timeouts.
- **Output:** designed loading, empty, and error states on every view, consistent formatting, 21 before/after screenshots in `docs/screenshots/`; 157 pytest and 94 Vitest tests.
- **Transcript:** [09-ticket-11-ui-polish.md](./transcripts/09-ticket-11-ui-polish.md)

### 10. Cutting Playwright e2e (2026-11-04)

- **Asked:** on a tight schedule, take Playwright off the plan and the tickets and move it to "With more time", while keeping the CI ticket.
- **Where I steered:** the AI asked two questions before editing. The axe checks only ran through Playwright, so I chose to defer them with it rather than move them into Vitest. I had the change go on its own branch off `main`, not on the in-progress endpoint branch.
- **Output:** PLAN.md without Playwright (Approach, Tests, traceability, build order) and a "With more time" entry for it; ticket #8 rescoped to CI only, and #9's README scope updated.
- **Transcript:** [10-cut-playwright.md](./transcripts/10-cut-playwright.md)

### 11. "Replay failed" only when there is something to replay (2026-11-04)

- **Asked:** a UX question: does "Replay failed" make sense on an endpoint with no failed deliveries? The AI said no. The button looked actionable and the zero case only surfaced as a toast after the click. It checked the API and found the view couldn't tell (no count on `EndpointOut`), then laid out three options and recommended adding the count.
- **Where I steered:** I picked that option and asked for it on top of the freshly merged UX fixes on `main`, rather than on the stale ticket branch the checkout was on.
- **Output:** `GET /endpoints` returns `failed_count` (a subquery, in the same pattern as the events' `delivery_count`); the button reads "Replay 3 failed", is disabled at zero with a tooltip, and the list polls every 5s and refetches after a replay. One pytest test and one page test were added.
- **Transcript:** [11-replay-failed-button.md](./transcripts/11-replay-failed-button.md)

### 12. Ticket #8: CI (2026-11-04)

- **Asked:** run `/work-ticket 8`: one GitHub Actions workflow for lint, typecheck, pytest, Vitest, and the stale-API-client check.
- **Process:** two jobs (backend, frontend). The frontend job also installs uv, because `pnpm gen:api --check` reads the schema from the FastAPI app. All checks passed locally, and the stale check was proven locally by appending to `schema.d.ts` (exit 1) and restoring it (exit 0).
- **Where I steered:** a GitHub Actions outage left the first run queued. The AI suggested finishing on local proof and keeping the PR a draft until a real run is green and a deliberately stale commit fails, and I agreed rather than block on GitHub.
- **Review:** `/code-review` (low) found nothing.
- **Merged during the GitHub Actions incident:** I chose to merge on the local proof and assume the workflow works, rather than wait. Confirming it on GitHub (a green run, and a stale commit that fails) is a follow-up.
- **Output:** `.github/workflows/ci.yml`, merged before its first run on GitHub.
- **Transcript:** [12-ticket-8-ci.md](./transcripts/12-ticket-8-ci.md)

### 13. Ticket #9: final docs pass (2026-11-04)

- **Asked:** run `/work-ticket 9`: a README with a live GIF and a demo walkthrough, a docs-vs-code pass over PLAN, the ADRs and the glossary, and PLAN moved to final.
- **Where I steered:** the AI stopped at the start because #8 (CI) was still open. I finished #8 first, then told it to continue.
- **Process:** two subagents audited the docs against the code in parallel, one for the backend and one for the frontend, citing code for every contradiction. They found no behavior bugs, only doc drift:
  - the Vitest list said polling "stops", when it backs off;
  - the live indicator's example text and "rows expand" didn't match the UI;
  - `data` must be a JSON object;
  - interrupted attempts record no headers;
  - PLAN still said "pre-build".

  It fixed the docs, plus one UI string that said "Retry" where the glossary says "Replay". For the GIF, it recorded the dashboard with Playwright from a scratch script, so Playwright stayed out of the repo. It ran the app from a throwaway clone on separate ports, so my own dev servers kept running.
- **Checks:** from a fresh clone, following only the README: install, `make lint typecheck test` (158 pytest and 101 Vitest tests), and the app running with the fast retry settings.
- **Output:** [README.md](../README.md), [live-deliveries.gif](./screenshots/live-deliveries.gif), and PLAN.md checked against the code, with the traceability links filled in.
- **Transcript:** [13-ticket-9-final-docs.md](./transcripts/13-ticket-9-final-docs.md)

### 14. Cursor support (2026-11-04)

- **Asked:** the Benji team works in Cursor, not Claude Code. What should change so the repo works well for them locally?
- **Process:** the AI checked the repo for Claude-only pieces. Running the app (README, Makefile, CI) had none, only `CLAUDE.md` and the `work-ticket` skill. It proposed four changes.
- **Where I steered:** I took two of them: the shared instructions file and the editor config. I dropped the one that would have marked my own workflow rules (AI usage log, one PR per ticket) as author-only. Reviewers will read and run the code, not write to the repo.
- **Output:** the instructions moved to `AGENTS.md`, which Cursor reads, and `CLAUDE.md` now imports it with `@AGENTS.md`, so there is still one source. `.vscode/` (Cursor reads it too) recommends the Python, Ruff, Vue, ESLint and Tailwind extensions, points at `backend/.venv`, and runs ruff and ESLint fixes on save.
- **Transcript:** [14-cursor-support.md](./transcripts/14-cursor-support.md)

### 15. Ticket #29: idempotency key survives leaving Events (2026-11-04)

- **Asked:** run `/work-ticket 29`, the one high-severity gap from the pre-submit review: README demo step 5 created a new event, because the trigger form's key was regenerated whenever the Events page unmounted.
- **Where I steered:** I picked the fix from the issue's options: keep the key with the submission it belongs to in `sessionStorage` via VueUse, rather than reword the README, and kept the key rules unchanged.
- **Process:** the new remount tests failed against the old composable and pass with `useSessionStorage`. In the app, on separate ports: trigger → Deliveries → Events → submit showed "Duplicate submission", a reload kept the key too, and changed data still got a new key. `/code-review` (low) found nothing.
- **Output:** [useIdempotencyKey.ts](../frontend/app/composables/useIdempotencyKey.ts), with the remount tests and PLAN's Events bullet updated. README step 5 is true as written.
- **Transcript:** [15-ticket-29-idempotency-key.md](./transcripts/15-ticket-29-idempotency-key.md)

### 16. Ticket #10: independent pre-submit review (2026-11-04)

- **Asked:** run `/work-ticket 10` in a fresh session that did no build work: review the repo against the brief as a Benji reviewer would, run `/code-review` over the whole codebase, follow the README in a fresh clone, file each gap as an issue, and fix nothing.
- **Where I steered:** the AI flagged that a fix-nothing ticket conflicts with the every-session AI usage entry. I chose a docs-only PR for this entry, and approved new `severity:*` labels.
- **Process:**
  - It read every source file, ran `/code-review` (xhigh), and probed suspected bugs directly: it compiled the claim SQL to rule out a correlation bug, and posted a `NaN` payload, which confirmed one.
  - It ran the README demo in the browser from a throwaway clone on separate ports, leaving my running dev servers alone.
  - The demo turned up the main finding: the idempotency key resets when you leave the Events page, so the README's dedup step creates a new event.
- **Output:** a verdict with evidence for every requirement, posted on #10 (all met; AI usage note partial until transcripts land). 13 issues filed (#29–#41): 1 high, 4 medium, 8 low.
- **Transcript:** [16-ticket-10-pre-submit-review.md](./transcripts/16-ticket-10-pre-submit-review.md)

### 17. Ticket #33: session transcripts (2026-11-04)

- **Asked:** run `/work-ticket 33` from the review session: add the exported session transcripts to `docs/transcripts/` and link them from this file.
- **Where I steered:** the AI mapped the 14 exports to entries and listed what wasn't exported, then asked about scope, format, and redaction before writing anything. I picked all 14 now and the rest later, readable Markdown with tool calls collapsed rather than raw JSONL, and subagent reports only as they appear in the parent session. For redaction I chose local paths and my email, and kept the injected skill and review text and the local demo `whsec_` secret as they were. I approved two sample files before the full set went in.
- **Process:** a scratch script (kept out of the repo) renders each export: prompts, answers to its questions, and replies verbatim, each tool call one line, tool output and screenshots dropped. It found mid-turn messages and subagent reports that the plain transcript records miss. A scan before and after rendering found no tokens and no leftover paths or email. `main` moved while this ran, so the review transcript became entry 16.
- **Where I steered (2):** after the first PR, I pointed out that every session ran in this app, so the AI could reach the missing ones itself. It found them, and noticed the original exports were taken while their sessions were still running. It re-rendered all of them from the complete session logs on disk, since the app caps exports at six an hour, and added the research session (01b), entries 14 and 15, and this session. I approved the new files, including 01b naming other candidates' public repos.
- **Output:** 18 transcripts in [docs/transcripts/](./transcripts/), each linked from its entry.
- **Transcript:** [17-ticket-33-transcripts.md](./transcripts/17-ticket-33-transcripts.md) (ends just before the final commit)

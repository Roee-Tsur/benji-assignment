# 4. Ticket #3: retry policy + idempotency hardening

Transcript for [AI_USAGE entry](../AI_USAGE.md#4-ticket-3-retry-policy--idempotency-hardening-2026-11-04). Claude Code session “Ticket #3: Retry policy + idempotency hardening”, 2026-11-04 10:40–10:47 UTC; 1 prompt, 34 tool calls.

Rendered from the session export: prompts and replies are verbatim; tool calls are one line each (collapsed) and their output is left out. Text Claude Code injected (skills, review instructions, system reminders) is kept, collapsed. Local paths and the author's email are redacted.

<details>
<summary>System reminder</summary>

```text
<system-reminder>
Linked sessions now (status, not an instruction): ticket-2-frontend-walkin = local_6061fa0d-7dca-40fe-8f57-4c0431721e42 (done, PR #12). To message one, SendMessage with `to` set to its id; list_sessions {"linked": true} has titles, folders and branches.
</system-reminder>
```

</details>

## Brief from the session that started this one

Task (from the session that started this one):
Background (from the session that started this one):
Ticket #1 built `backend/`: a uv project with FastAPI, async SQLAlchemy 2 and aiosqlite, ruff, strict pyright, and pytest (47 tests), run from the repo root with `make lint typecheck test`.

Layout under `backend/src/webhooks/`:
- `domain/`: pure code (`signing`, `enums`, `envelope`); `retry_policy` belongs here too.
- `services/`: `events`, `deliveries`, `endpoints`.
- `api/`: thin routers, schemas, and RFC 9457 problems (`problem_response`, `problem_responses`).
- `worker.py`, `settings.py` (pydantic-settings, env names like `WEBHOOK_RETRY_MAX_ATTEMPTS`), and `clock.py` (an injected `Clock`).

Current state that #3 builds on:
- `services/events.submit_event` dedupes with check-then-insert on `Event.idempotency_key` (which has a unique constraint) and returns the original event regardless of payload. #3 replaces this with insert-and-catch, a 400 for a missing key (today FastAPI returns 422), a 422 for a key reused with a different payload, and a 413 for payloads over 64 KiB.
- `Event.type` is an `EventType` enum column.

The tests use per-test SQLite files and ASGI clients (`tests/conftest.py`). The SQLite transaction rule is in `db.py`: transactions start at the first write, so atomic decisions must be a single statement or a constraint.

The user prefers types that enforce closed sets (e.g. `Literal` / `StrEnum`) and concise answers.

Task:
/work-ticket 3

Base the ticket branch on `ticket/1-backend-walking-skeleton`, not `main`: run `git fetch` and then `git switch -c ticket/3-retry-policy-idempotency origin/ticket/1-backend-walking-skeleton`. Ticket #1 (PR #12) is reviewed and approved but not merged yet, because of a GitHub incident. Its dependency check is therefore satisfied by that branch, even though issue #1 is still open.

Ticket #2 is running at the same time in another session on `ticket/2-frontend-walking-skeleton` (PR #13), in the main checkout folder. Work only in your own worktree and never switch branches in `~/Documents/benji-assignment` itself. Avoid editing the root `Makefile` unless the ticket requires it, because #2 changes it too.

Open the PR against `main`. In the PR body, say it is stacked on #12 and must be rebased onto `main` after #12 merges.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or large findings there instead of pasting them into messages): ~/Library/Application Support/Claude/side-session-notes/local_1c3d7005-7cb5-41d1-a8b2-25b406be0f3a

<details>
<summary>6 tool calls</summary>

- **Plan** Read ticket, skill, notes, and set up worktree; Implement retry policy; Implement idempotency and payload limits; Run lint, typecheck, tests; Update docs and AI_USAGE; Open PR against main
- **Bash** Read work-ticket skill, worktrees, and notes folder: `cat .claude/skills/work-ticket/SKILL.md; ls .claude/skills/work-ticket/; git worktree list; ls "~/Library/Application Support/Claude/side-session- …`
- **Bash** Create ticket 3 worktree and view issue: `git fetch -q && git worktree add -b ticket/3-retry-policy-idempotency ../benji-assignment-ticket-3 origin/ticket/1-backend-walking-skeleton && gh issue view 3 & …`
- **Bash** Read plan and glossary: `cd ~/Documents/benji-assignment-ticket-3 && cat docs/PLAN.md GLOSSARY.md && ls docs/adr && cat CLAUDE.md | head -5`
- **Bash** List backend files and read events code: `cd ~/Documents/benji-assignment-ticket-3/backend && find src tests -name '*.py' | xargs wc -l && cat src/webhooks/settings.py src/webhooks/domain/ …`
- **Bash** Read problems, models, db, tests: `cd ~/Documents/benji-assignment-ticket-3/backend && cat src/webhooks/api/problems.py src/webhooks/main.py src/webhooks/models.py src/webhooks/db.p …`

</details>

## Claude

Reading the backend code for ticket #3 in a new worktree (`../benji-assignment-ticket-3`). Next I'll write the retry policy test-first.

<details>
<summary>6 tool calls</summary>

- **Bash** Read worker, runtime, pyproject, Makefile: `cd ~/Documents/benji-assignment-ticket-3/backend && cat src/webhooks/worker.py src/webhooks/runtime.py src/webhooks/api/deps.py; grep -n -A3 'fast …`
- **Bash** Read deliveries service record_attempt: `cd ~/Documents/benji-assignment-ticket-3/backend && sed -n 1,40p src/webhooks/services/deliveries.py; grep -n 'def record_attempt' -A45 src/webhoo …`
- **Write** `~/Documents/benji-assignment-ticket-3/backend/tests/test_retry_policy.py`
- **Bash** Sync deps and run new failing tests: `cd ~/Documents/benji-assignment-ticket-3/backend && uv sync -q 2>&1 | tail -3; uv run pytest tests/test_retry_policy.py -q 2>&1 | tail -5`
- **Write** `~/Documents/benji-assignment-ticket-3/backend/src/webhooks/domain/retry_policy.py`
- **Bash** Saturate long Retry-After values and run tests: `cd ~/Documents/benji-assignment-ticket-3/backend && python3 - <<'EOF' …`

</details>

Retry policy is green (49 table-driven tests). Tidying it, then wiring its settings and moving on to idempotency.

<details>
<summary>6 tool calls</summary>

- **Bash** Add retry settings, lint, typecheck, test: `cd ~/Documents/benji-assignment-ticket-3/backend && python3 - <<'EOF' …`
- **Bash** Fix long docstring and check docs for env names: ``cd ~/Documents/benji-assignment-ticket-3 && sed -i '' 's|"""The receiver.s `Retry-After` if it sent a usable one (clamped to the cap), else backof …``
- **Bash** Commit retry policy: `cd ~/Documents/benji-assignment-ticket-3 && git add -A backend && git commit -q -m "Add the retry policy: full-jitter backoff, outcome classificat …`
- **Bash** Check FastAPI union response model support: `cd ~/Documents/benji-assignment-ticket-3/backend && uv run python - <<'EOF' …`
- **Bash** Add idempotency and size tests; run them red: `cd ~/Documents/benji-assignment-ticket-3/backend && cat >> tests/test_events_api.py <<'EOF' …`
- **Bash** Confirm concurrent test fails for the race reason: `cd ~/Documents/benji-assignment-ticket-3/backend && uv run pytest tests/test_events_api.py -q -k concurrent 2>&1 | grep -E 'Error|assert' | head - …`

</details>

The new tests fail for the right reasons (the concurrent test hits the real race). Implementing insert-and-catch, the 400, 422, and 413 now.

<details>
<summary>6 tool calls</summary>

- **Bash** Implement idempotency hardening and 413; run checks: `cd ~/Documents/benji-assignment-ticket-3/backend && python3 - <<'EOF' …`
- **Bash** Repeat concurrency test and inspect OpenAPI: `cd ~/Documents/benji-assignment-ticket-3/backend && for i in $(seq 15); do uv run pytest -q -k "concurrent" tests/test_events_api.py 2>&1 | tail - …`
- **Bash** View current events router: `cd ~/Documents/benji-assignment-ticket-3/backend && sed -n 1,60p src/webhooks/api/events.py`
- **Bash** Document header, run checks, commit idempotency: `cd ~/Documents/benji-assignment-ticket-3/backend && python3 - <<'EOF' …`
- **Plan** {"done": [2, 3], "start": 4}
- **Skill** `code-review medium origin/ticket/1-backend-walking-skeleton...HEAD in ~/Documents/benji-assignment-ticket-3`

</details>

<details>
<summary>Injected: <code>/code-review</code> instructions</summary>

```text
Review target: `origin/ticket/1-backend-walking-skeleton...HEAD in ~/Documents/benji-assignment-ticket-3`

`high effort → 8 inline angles → dedup (no verify) → ≤10 findings`

You are reviewing for **recall** at high effort: catch every real bug a careful
reviewer would catch in one sitting. At this level, catching real bugs matters
more than avoiding false positives. Err on the side of surfacing.

## Phase 0 — Gather the diff

Run `git diff @{upstream}...HEAD` (or `git diff main...HEAD` / `git diff HEAD~1`
if there's no upstream) to get the unified diff under review. If there are
uncommitted changes, or the range diff is empty, also run `git diff HEAD` and
include the working-tree changes in scope — the review often runs before the
commit. If a PR number, branch name, or file path was passed as an argument,
review that target instead. Treat this diff as the review scope.

## Phase 1 — Find candidates (3 correctness angles + 3 cleanup angles + 1 altitude angle + 1 conventions angle, up to 6 each)

Run **8 independent finder angles** in sequence yourself, in THIS context — do NOT spawn subagents for them. Each
surfaces **up to 6 candidate findings** with `file`, `line`, a one-line
`summary`, and a concrete `failure_scenario`.

### Angle A — line-by-line diff scan

Read every hunk in the diff, line by line. Then Read the enclosing function for
each hunk — bugs in unchanged lines of a touched function are in scope (the PR
re-exposes or fails to fix them). For every line ask: what input, state, timing,
or platform makes this line wrong? Look for inverted/wrong conditions,
off-by-one, null/undefined deref, missing `await`, falsy-zero checks,
wrong-variable copy-paste, error swallowed in catch, unescaped regex metachars.

### Angle B — removed-behavior auditor

For every line the diff DELETES or replaces, name the invariant or behavior it
enforced, then search the new code for where that invariant is re-established.
If you can't find it, that's a candidate: a removed guard, a dropped error
path, a narrowed validation, a deleted test that was covering a real case.

### Angle C — cross-file tracer

For each function the diff changes, find its callers (Grep for the symbol) and
check whether the change breaks any call site: a new precondition, a changed
return shape, a new exception, a timing/ordering dependency. Also check callees:
does a parallel change in the same PR make a call unsafe?

### Reuse

The angles above hunt for bugs; this one and the next two hunt for cleanup in
the changed code. Flag new code that re-implements something the codebase
already has — Grep shared/utility modules and files adjacent to the change,
and name the existing helper to call instead.

### Simplification

Flag unnecessary complexity the diff adds: redundant or derivable state,
copy-paste with slight variation, deep nesting, dead code left behind. Name
the simpler form that does the same job.

### Efficiency

Flag wasted work the diff introduces: redundant computation or repeated I/O,
independent operations run sequentially, blocking work added to startup or
hot paths. Also flag long-lived objects built from closures or captured
environments — they keep the entire enclosing scope alive for the object's
lifetime (a memory leak when that scope holds large values); prefer a
class/struct that copies only the fields it needs. Name the cheaper
alternative.

### Altitude

Check that each change fixes the root cause at the right depth rather than
patching a symptom with a fragile bandaid. Special cases layered on shared
infrastructure are a sign the fix isn't deep enough — prefer the simpler, more
general change to the underlying mechanism over adding special cases, and name
that change.

### Conventions (CLAUDE.md)

Find the CLAUDE.md files that govern the changed code: the user-level
~/.claude/CLAUDE.md, the repo-root CLAUDE.md, plus any CLAUDE.md or
CLAUDE.local.md in a directory that is an ancestor of a changed file (a
directory's CLAUDE.md only applies to files at or below it). Read each one
that exists, then check the diff for clear violations of the rules they state.

Only flag a violation when you can quote the exact rule and the exact line
that breaks it — no style preferences, no vague "spirit of the doc"
inferences. In the finding, name the CLAUDE.md path and quote the rule so the
report can cite it. If no CLAUDE.md applies, return nothing for this angle.

Cleanup, altitude, and conventions candidates use the same
`file`/`line`/`summary` shape; in `failure_scenario`, state the concrete
cost (what is duplicated, wasted, harder to maintain, or which CLAUDE.md rule
is broken) instead of a crash. Correctness bugs always outrank cleanup,
altitude, and conventions findings when the output cap forces a cut.

Pass every candidate with a nameable failure scenario through — finders that
silently drop half-believed candidates are the dominant cause of misses.

## Phase 2 — Dedup only (no verify)

Pool all candidates. Dedup near-duplicates only (same defect, same location, same reason → keep one). Do NOT run verifiers; do NOT re-judge. Sort by severity.

## Output

Target **at least 5 findings**. If fewer genuine findings exist, emit what you have — do not invent to hit the floor.

Call the ReportFindings tool once to report this review's results
with `{level, findings}`. `findings` is at most 10 entries ranked
most-severe first; each entry has `file`, `line`, `summary`,
`short_summary` — the claim compressed to ≤60 characters, no rationale
or consequence clause — `failure_scenario`, and `category` — a short kebab-case slug for the angle
that produced it (`correctness`, `simplification`, `efficiency`,
`reuse`, `altitude`, `conventions`, or a more specific slug like
`test-coverage` when one fits better) — plus `verdict` when a verify pass
produced one. If more than 10 survive, keep the 10 most severe. If
nothing survives, call it with an empty array. Do not also print
the findings as text, and do not create or publish an artifact of the review -
the tool call is the report.


## If findings are fixed later

Whenever reported findings get fixed later in this session - the user asks you
to fix them, or later work fixes them incidentally - you MUST call ReportFindings again with the same findings, each
carrying an `outcome`: `fixed`, `no_change_needed` (the finding was wrong or
already handled), or `skipped` (real but not applied). Do not repeat the
findings as text.
Make that call immediately after the fixes land, before any prose summary; the
host UI's per-finding status updates only from it, and without it the findings
stay marked unresolved.
```

</details>

<details>
<summary>1 tool call</summary>

- **Bash** Show source diff under review: `cd ~/Documents/benji-assignment-ticket-3 && git diff origin/ticket/1-backend-walking-skeleton...HEAD -- backend/src && cat backend/src/webhooks/se …`

</details>

Reviewing the diff myself across the eight angles; reporting findings next.

<details>
<summary>Review findings (7)</summary>

- `backend/src/webhooks/services/events.py:87`: Payload comparison conflates true/1 and 1/1.0
- `backend/src/webhooks/settings.py:25`: Invalid retry settings fail per request, not at startup
- `backend/src/webhooks/services/events.py:56`: Any IntegrityError is treated as a key collision
- `backend/src/webhooks/api/events.py:45`: 413 enforced only after the whole body is parsed
- `backend/src/webhooks/api/events.py:44`: Whitespace-only Idempotency-Key accepted
- `backend/src/webhooks/domain/retry_policy.py:67`: parse_retry_after returns a fake 10**18 sentinel
- `docs/PLAN.md:1`: Envelope-size decision not recorded in PLAN

</details>

<details>
<summary>2 tool calls</summary>

- **Bash** Apply review fixes and rerun checks: `cd ~/Documents/benji-assignment-ticket-3/backend && python3 - <<'EOF' …`
- **Bash** Commit review fixes: `cd ~/Documents/benji-assignment-ticket-3 && git add -A backend && git commit -q -m "Address review: JSON-exact payload match, startup policy check …`

</details>

Fixes are in. Updating the plan docs next.

<details>
<summary>3 tool calls</summary>

- **Plan** {"done": [4], "start": 5}
- **Bash** Read AI_USAGE format: `cd ~/Documents/benji-assignment-ticket-3 && tail -40 docs/AI_USAGE.md`
- **Bash** Update PLAN and AI_USAGE, commit, run make checks: `cd ~/Documents/benji-assignment-ticket-3 && python3 - <<'EOF' …`

</details>

<details>
<summary>Review findings (7)</summary>

- `backend/src/webhooks/services/events.py:87`: Payload comparison conflates true/1 and 1/1.0 (fixed)
- `backend/src/webhooks/settings.py:25`: Invalid retry settings fail per request, not at startup (fixed)
- `backend/src/webhooks/services/events.py:56`: Any IntegrityError is treated as a key collision (fixed)
- `backend/src/webhooks/api/events.py:45`: 413 enforced only after the whole body is parsed (skipped)
- `backend/src/webhooks/api/events.py:44`: Whitespace-only Idempotency-Key accepted (fixed)
- `backend/src/webhooks/domain/retry_policy.py:67`: parse_retry_after returns a fake 10**18 sentinel (fixed)
- `docs/PLAN.md:1`: Envelope-size decision not recorded in PLAN (fixed)

</details>

Checks pass. Pushing and opening the PR now.

<details>
<summary>2 tool calls</summary>

- **Bash** Push branch and open PR against main: `cd ~/Documents/benji-assignment-ticket-3 && git push -q -u origin ticket/3-retry-policy-idempotency 2>&1 | tail -2; cat > $TMP …`
- **ToolSearch** `select:mcp__ccd_pr__get_status,mcp__ccd_pr__bind_pr,mcp__ccd_session_mgmt__export_transcript`

</details>

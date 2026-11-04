# 3. Ticket #2: frontend walking skeleton

Transcript for [AI_USAGE entry](../AI_USAGE.md#3-ticket-2-frontend-walking-skeleton-2026-11-04). Claude Code session “Ticket #2: Frontend walking skeleton”, 2026-11-04 10:04–10:24 UTC; 1 prompt, 97 tool calls.

Rendered from the session export: prompts and replies are verbatim; tool calls are one line each (collapsed) and their output is left out. Text Claude Code injected (skills, review instructions, system reminders) is kept, collapsed. Local paths and the author's email are redacted.

## Brief from the session that started this one

Task (from the session that started this one):
Background (from the session that started this one):
Ticket #1 built `backend/`, a uv project with FastAPI and SQLite, run with `make dev-backend` on port 8000. Its API:
- `POST/GET /endpoints` (returns the `whsec_` secret once) and `PATCH /endpoints/{endpoint_id}` (`{enabled}`);
- `POST /events`, which requires an `Idempotency-Key` header and returns 201 when new or 200 with `deduplicated: true`;
- `GET /deliveries` (newest 50) and `GET /deliveries/{delivery_id}` (payload plus attempts).

Endpoints can point at `http://127.0.0.1:8000/mock/ok`, the built-in receiver. Every error is RFC 9457 `application/problem+json`, and the OpenAPI schema (`/openapi.json`) declares it that way, so generated types are accurate. Operation IDs are the function names, e.g. `create_endpoint`. The backend has no CORS yet, so the frontend needs a dev proxy or a small, justified backend change. The root `Makefile` has `dev-backend`, `lint`, `typecheck`, and `test` targets that run backend-only for now; #2 extends them to the frontend. The user is less familiar with Python and prefers concise answers and closed sets enforced by types.

Task:
/work-ticket 2

Base the ticket branch on `ticket/1-backend-walking-skeleton`, not `main`: run `git fetch` and then `git switch -c ticket/2-frontend-walking-skeleton origin/ticket/1-backend-walking-skeleton`. Ticket #1 (PR #12) is reviewed and approved but not merged yet, because of a GitHub incident. Its dependency check is therefore satisfied by that branch, even though issue #1 is still open. Open the PR against `main` as usual. In the PR body, say it is stacked on #12 and must be rebased onto `main` after #12 merges.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or large findings there instead of pasting them into messages): ~/Library/Application Support/Claude/side-session-notes/local_1c3d7005-7cb5-41d1-a8b2-25b406be0f3a

<details>
<summary>12 tool calls</summary>

- **Plan** Read work-ticket skill, ticket, plan; Create ticket branch from ticket/1; Build the frontend walking skeleton; Wire Makefile targets and verify; Update docs and AI_USAGE; Open stacked PR against main
- **Bash** Read the work-ticket skill and list shared notes: `cat .claude/skills/work-ticket/SKILL.md; ls .claude/skills/work-ticket/; ls "~/Library/Application Support/Claude/side-session-notes/local_1c3d700 …`
- **Bash** Read ticket #2, plan, glossary, ADR list: `gh issue view 2; cat CLAUDE.md docs/PLAN.md GLOSSARY.md; ls docs/adr/`
- **Bash** Read ADR 0004, Makefile, AI usage log, repo layout: `cat docs/adr/0004-server-state-in-vue-query.md Makefile; tail -60 docs/AI_USAGE.md; ls -a; ls backend backend/app 2>/dev/null; cat .gitignore`
- **Bash** Create ticket branch and inspect backend tooling: `git fetch -q && git switch -c ticket/2-frontend-walking-skeleton origin/ticket/1-backend-walking-skeleton && git log --oneline -3 && ls -R backend/src | head -5 …`
- **Bash** Read backend API schemas, problems, app factory: `cd ~/Documents/benji-assignment/backend && cat src/webhooks/api/schemas.py src/webhooks/api/problems.py src/webhooks/main.py src/webhooks/domain/e …`
- **Bash** Look up current package versions: `cd ~/Documents/benji-assignment && for p in nuxt @nuxt/ui @tanstack/vue-query openapi-fetch openapi-typescript msw vitest @nuxt/test-utils @nuxt/e …`
- **Bash** Check peer dependency ranges: `pnpm view vue-tsc peerDependencies; pnpm view @nuxt/test-utils peerDependencies; pnpm view @nuxt/ui peerDependencies; pnpm view openapi-typescript peerDependenc …`
- **Bash** Check TS 5 version and create-nuxt options: `pnpm view typescript@5 version | tail -1; pnpm dlx create-nuxt@latest --help 2>&1 | tail -40`
- **Bash** Scaffold Nuxt UI starter without installing: `pnpm dlx create-nuxt@latest frontend -t ui --packageManager=pnpm --no-gitInit --no-install --modules= </dev/null 2>&1 | tail -15; ls -la frontend; find frontend …`
- **Bash** Drop template extras and show starter config: `cd ~/Documents/benji-assignment/frontend && rm -rf LICENSE renovate.json .github README.md app/components/TemplateMenu.vue app/components/AppLogo. …`
- **Bash** Check openapi-msw and msw compatibility: `pnpm view openapi-msw version peerDependencies; pnpm view msw@2 version | tail -1; pnpm view msw@3 engines 2>/dev/null; pnpm view @nuxt/test-utils@4 dependencie …`

</details>

## Claude

Scaffolded the Nuxt UI starter and removed the template extras. Next I'm writing `package.json` with Vue Query, openapi-fetch/-typescript, MSW (via `openapi-msw`), and Vitest, then installing.

<details>
<summary>13 tool calls</summary>

- **Write** `~/Documents/benji-assignment/frontend/package.json`
- **Bash** Install frontend dependencies: `rm pnpm-lock.yaml && pnpm install 2>&1 | tail -25`
- **Bash** Skip msw build script and reinstall: `cat > pnpm-workspace.yaml <<'EOF' …`
- **Bash** Write gen:api script and generate the schema types: `mkdir -p ~/Documents/benji-assignment/frontend/scripts && cat > ~/Documents/benji-assignment/frontend/scripts/gen-api.mjs <<'EOF' …`
- **Bash** Inspect generated component schemas: `sed -n 120,330p app/api/schema.d.ts; grep -n "operations\[\|submit_event: {" -A40 app/api/schema.d.ts | sed -n '/submit_event: {/,/};$/p' | head -60`
- **Bash** Read openapi-msw usage and openapi-fetch fetch capture: `sed -n '/## Usage/,/## /p' node_modules/openapi-msw/README.md | head -120; grep -n "fetch: baseFetch\|globalThis.fetch" node_modules/openapi-fetch/dist/index.js …`
- **Bash** Read openapi-msw getting started section: `sed -n '/### Getting Started/,/### Handling Unknown/p' node_modules/openapi-msw/README.md | head -150; ls node_modules/openapi-fetch/dist; grep -n "globalThis.f …`
- **Write** `~/Documents/benji-assignment/frontend/app/api/errors.ts`
- **Write** `~/Documents/benji-assignment/frontend/app/api/client.ts`
- **Write** `~/Documents/benji-assignment/frontend/app/api/queryKeys.ts`
- **Bash** Add status/event-type tables and the Vue Query plugin: `mkdir -p app/domain app/plugins app/composables app/components app/layouts app/pages && cat > app/domain/deliveryStatus.ts <<'EOF' …`
- **Bash** Add feature composables and the URL query helper: `cat > app/composables/useEndpoints.ts <<'EOF' …`
- **Bash** List Nuxt UI components and DashboardSidebar props: `ls node_modules/@nuxt/ui/dist/runtime/components/ | tr '\n' ' '; echo; grep -n "export interface DashboardSidebarProps" -A40 node_modules/@nuxt/ui/dist/runtime/ …`

</details>

Now the shell, badge, and pages.

<details>
<summary>8 tool calls</summary>

- **Bash** Add app shell, layout, status badge, query error: `cat > app/app.vue <<'EOF' …`
- **Bash** Check CheckboxGroup and Form APIs: `grep -n "export interface CheckboxGroupProps" -A30 node_modules/@nuxt/ui/dist/runtime/components/CheckboxGroup.vue.d.ts | grep -n "items\|valueKey\|labelKey" ;  …`
- **Bash** Read Form component props: `sed -n 1,80p node_modules/@nuxt/ui/dist/runtime/components/Form.vue.d.ts | grep -v "^\s*\*\|/\*\*" | head -50`
- **Bash** Add endpoints page and create-endpoint modal: `cat > app/components/CreateEndpointModal.vue <<'EOF' …`
- **Bash** Add events and deliveries pages, Nuxt config with proxy: `cat > app/pages/events.vue <<'EOF' …`
- **Bash** Run vue-tsc typecheck: `pnpm nuxt prepare >/dev/null 2>&1; pnpm typecheck 2>&1 | tail -30`
- **Bash** Fix input type, rerun typecheck and lint: `python3 - <<'EOF' …`
- **Bash** Ignore generated schema in lint, rerun lint: `sed -i '' "s#^import { ApiError } from '~/api/errors'#import type { ApiError } from '~/api/errors'#" app/plugins/vue-query.ts && python3 - <<'EOF' …`

</details>

Lint and typecheck pass. Next I'm wiring the `Makefile` and checking the slice in the browser against the real backend.

<details>
<summary>8 tool calls</summary>

- **Bash** Read README and launch config: `cd ~/Documents/benji-assignment && cat README.md; cat .claude/launch.json 2>/dev/null`
- **Bash** Extend Makefile and add preview launch config: `cd ~/Documents/benji-assignment && cat > Makefile <<'EOF' …`
- **Bash** Check whether ports 8000 and 3000 are in use: `lsof -iTCP:8000 -iTCP:3000 -sTCP:LISTEN -n -P 2>/dev/null | head`
- **browser.preview_start** `{"name": "backend"}`
- **Plan** {"done": [1, 2, 3], "start": 4}
- **Bash** Use explicit cd commands in launch config: `cat > .claude/launch.json <<'EOF' …`
- **browser.preview_start** `{"name": "backend"}`
- **browser.preview_logs** `{"serverId": "3b5770e7-6174-4f2f-8f70-7adadabeb4af"}`

</details>

The preview pane can't read `~/Documents` (sandbox), so I'm running the dev servers from the shell in the background instead.

<details>
<summary>7 tool calls</summary>

- **browser.preview_stop** `{"serverId": "3b5770e7-6174-4f2f-8f70-7adadabeb4af"}`
- **Bash** Run backend and dashboard together via make dev: `rm ~/Documents/benji-assignment/.claude/launch.json; cd ~/Documents/benji-assignment && make dev > $TMP …`
- **Bash** Wait for dashboard proxy to reach the backend: `for i in $(seq 1 40); do curl -sf http://127.0.0.1:3000/api/endpoints >/dev/null && break; sleep 1; done; curl -s -i http://127.0.0.1:3000/api/endpoints | head  …`
- **Bash** Check the proxy via localhost: `curl -s -i http://localhost:3000/api/endpoints | head -8; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/deliveries`
- **browser.batch** 2 actions (navigate, computer)
- **browser.read_console_messages** `{"limit": 20}`
- **browser.computer** `{"action": "screenshot", "scale": 0.6}`

</details>

The dashboard loads through the proxy. Next I'm running the acceptance flow: create endpoint → trigger → watch the delivery reach `succeeded`.

<details>
<summary>9 tool calls</summary>

- **browser.batch** 3 actions (computer)
- **browser.batch** 3 actions (computer)
- **browser.batch** 4 actions (computer, find)
- **browser.computer** `{"action": "screenshot", "scale": 0.6}`
- **browser.batch** 3 actions (computer)
- **browser.batch** 3 actions (computer)
- **browser.batch** 3 actions (computer)
- **Bash** Trigger an event via the proxy and check a problem response: `curl -s -X POST http://localhost:3000/api/events -H 'content-type: application/json' -H "Idempotency-Key: poll-check-$(date +%s)" -d '{"type":"campaign_updated" …`
- **browser.get_page_text** `{}`

</details>

Polling works: a delivery triggered from curl appeared as `Succeeded` with no reload. Next I'm writing the Vitest + MSW harness and the `ApiError` tests.

<details>
<summary>6 tool calls</summary>

- **Bash** Add Vitest projects config and typed MSW harness: `cd ~/Documents/benji-assignment/frontend && python3 - <<'EOF' …`
- **Bash** Write ApiError unit tests and MSW-backed composable tests, run them: `cat > test/unit/api-errors.test.ts <<'EOF' …`
- **Bash** Show MSW error detail: `pnpm vitest run --project nuxt 2>&1 | grep -n "MSW\|Error" | head -20`
- **Bash** Show unmatched request details: `pnpm vitest run --project nuxt 2>&1 | sed -n 1,17p`
- **Bash** Check whether setup and test share the MSW server: `cat > test/nuxt/debug.test.ts <<'EOF' …`
- **Bash** Run debug test and show output: `pnpm vitest run --project nuxt test/nuxt/debug.test.ts 2>&1 | tail -20`

</details>

Debugging why `server.use` overrides in MSW tests don't apply; the default handlers do work.

<details>
<summary>6 tool calls</summary>

- **Bash** Probe MSW server identity and handlers: `cat > test/nuxt/debug.test.ts <<'EOF' …`
- **Bash** Make MSW server per test file, rerun tests: `rm test/nuxt/debug.test.ts test/nuxt/setup.ts && cat > test/msw/server.ts <<'EOF' …`
- **Bash** List declared response statuses: `sed -n '/^    list_endpoints: {/,/^    };/p' app/api/schema.d.ts | grep -n "^            [0-9]*:" ; sed -n '/^    create_endpoint: {/,/^    };/p' app/api/schema …`
- **Bash** Show which files each Nuxt tsconfig includes: `node -e "for (const f of ['app','node','shared','server']) { const c=JSON.parse(require('fs').readFileSync('.nuxt/tsconfig.'+f+'.json','utf8')); console.log(f,  …`
- **Bash** Isolate query cache per test, rerun tests, typecheck, lint: `python3 - <<'EOF' …`
- **Bash** Confirm typecheck covers test files: `echo "const bad: number = 'x'; export { bad }" > test/unit/tmp-typecheck.ts && pnpm typecheck 2>&1 | grep "error TS"; rm test/unit/tmp-typecheck.ts`

</details>

Tests, typecheck (which now covers the tests), and lint all pass. Next I'm proving the stale-client check by changing the backend schema temporarily.

<details>
<summary>3 tool calls</summary>

- **Bash** Change backend schema, run stale check, revert, recheck: `cd ~/Documents/benji-assignment && cp backend/src/webhooks/api/schemas.py $TMP …`
- **Bash** Check for direct fetch use and run all make checks: `grep -rn "fetch\|\$fetch\|useFetch" frontend/app --include=*.vue --include=*.ts | grep -v "app/api/schema.d.ts" ; echo ---; make lint typecheck test 2>&1 | grep …`
- **Bash** Grep for fetch usage and confirm make exit code: `grep -rnE "fetch|useFetch" frontend/app | grep -v "app/api/schema.d.ts"; make lint typecheck >/dev/null 2>&1; echo "lint+typecheck exit=$?"`

</details>

I'll also enforce "components never call fetch directly" with a lint rule, so it holds after this PR.

<details>
<summary>3 tool calls</summary>

- **Bash** Add layering lint rule and probe it with violations: `cd ~/Documents/benji-assignment/frontend && cat > eslint.config.mjs <<'EOF' …`
- **Bash** Add useQueryParam tests and run the nuxt project: `cat > test/nuxt/useQueryParam.test.ts <<'EOF' …`
- **Bash** Show the failing useQueryParam test: `pnpm vitest run test/nuxt/useQueryParam.test.ts 2>&1 | grep -B5 -A25 "FAIL" | head -50`

</details>

The failure comes from the test harness, not the helper: `mountSuspended` navigates to `/` on mount, which drops the query the test pushed first. I'm moving the push after the mount.

<details>
<summary>1 tool call</summary>

- **Bash** Fix test ordering and rerun checks: `python3 - <<'EOF' …`

</details>

All checks pass. Next I'm committing in logical steps.

<details>
<summary>4 tool calls</summary>

- **Bash** Review untracked frontend files: `cd ~/Documents/benji-assignment && git status --short frontend | head; git check-ignore -q frontend/.nuxt && echo nuxt-ignored; ls frontend/public`
- **Bash** Commit the frontend in logical steps: `T=$'\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' && \ …`
- **Bash** Inspect the generated .nuxtrc: `cat frontend/.nuxtrc`
- **Bash** Commit .nuxtrc: `git add frontend/.nuxtrc && git commit -q -m "Record the @nuxt/test-utils setup version …`

</details>

Now `/code-review` on the branch.

<details>
<summary>1 tool call</summary>

- **Skill** `code-review ticket/2-frontend-walking-skeleton vs origin/ticket/1-backend-walking-skeleton (frontend/ and Makefile)`

</details>

<details>
<summary>Injected: <code>/code-review</code> instructions</summary>

```text
Review target: `ticket/2-frontend-walking-skeleton vs origin/ticket/1-backend-walking-skeleton (frontend/ and Makefile)`

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

- **Bash** Show diff stats and unwrap section: `git diff --stat origin/ticket/1-backend-walking-skeleton...HEAD | tail -5; cat frontend/app/api/errors.ts | sed -n 40,60p`

</details>

<details>
<summary>Review findings (8)</summary>

- `frontend/app/components/CreateEndpointModal.vue:21`: mutateAsync rejections unhandled in submit handlers
- `frontend/scripts/gen-api.mjs:13`: gen:api output depends on local backend .env
- `frontend/app/components/CreateEndpointModal.vue:33`: Secret from in-flight create leaks into next open
- `frontend/app/pages/deliveries.vue:25`: Failed poll hides already-loaded deliveries
- `frontend/app/pages/events.vue:33`: Stale success alert shown after a failed submit
- `frontend/app/components/CreateEndpointModal.vue:26`: Clipboard copy failure unhandled
- `frontend/eslint.config.mjs:28`: Layering lint rule bypassable via relative import
- `frontend/test/nuxt/endpoints.test.ts:20`: Retry test waits on real backoff delays

</details>

Fixing all 8 findings.

<details>
<summary>1 tool call</summary>

- **Bash** Apply review fixes, probe lint rule, rerun checks: `cd ~/Documents/benji-assignment/frontend && python3 - <<'EOF' …`

</details>

The checks pass. Rechecking the changed create and trigger flows in the browser:

<details>
<summary>4 tool calls</summary>

- **browser.batch** 5 actions (navigate, computer, find)
- **browser.batch** 5 actions (computer)
- **browser.batch** 8 actions (computer, navigate, get_page_text, read_console_messages)
- **Bash** Commit review fixes: `cd ~/Documents/benji-assignment && git add -A frontend && git commit -q -m "Address review: callback mutations, stable schema, visible stale data …`

</details>

<details>
<summary>Review findings (8)</summary>

- `frontend/app/components/CreateEndpointModal.vue:21`: mutateAsync rejections unhandled in submit handlers (fixed)
- `frontend/scripts/gen-api.mjs:13`: gen:api output depends on local backend .env (fixed)
- `frontend/app/components/CreateEndpointModal.vue:33`: Secret from in-flight create leaks into next open (fixed)
- `frontend/app/pages/deliveries.vue:25`: Failed poll hides already-loaded deliveries (fixed)
- `frontend/app/pages/events.vue:33`: Stale success alert shown after a failed submit (fixed)
- `frontend/app/components/CreateEndpointModal.vue:26`: Clipboard copy failure unhandled (fixed)
- `frontend/eslint.config.mjs:28`: Layering lint rule bypassable via relative import (fixed)
- `frontend/test/nuxt/endpoints.test.ts:20`: Retry test waits on real backoff delays (fixed)

</details>

Next, docs: PLAN.md decisions, the traceability table, and the AI_USAGE entry.

<details>
<summary>8 tool calls</summary>

- **Plan** {"done": [4], "start": 5}
- **Bash** Check whether #3 covers the missing-key status and #8 the stale check: `gh issue view 3 --json title,body -q '.title + "\n" + .body' | grep -inE "400|missing|title" | head; gh issue view 8 --json title,body -q '.title + "\n" + .body …`
- **Bash** Update PLAN.md and AI_USAGE.md, commit: `python3 - <<'EOF' …`
- **Plan** (next step)
- **Bash** Push branch and open the stacked PR: `git push -q -u origin ticket/2-frontend-walking-skeleton 2>&1 | tail -3 && gh pr create --base main --head ticket/2-frontend-walking-skeleton --title "#2 Fronte …`
- **ToolSearch** `select:mcp__ccd_pr__get_status,mcp__ccd_pr__bind_pr,mcp__ccd_session_mgmt__export_transcript`
- **app.pr__get_status** `{}`
- **app.session_mgmt__export_transcript** `{"session_id": "self"}`

</details>

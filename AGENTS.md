# Agent instructions

Benji take-home: a webhook notification system (FastAPI backend + Nuxt ops dashboard). The brief is in `docs/ASSIGNMENT.md`, the plan in `docs/PLAN.md`. Use the vocabulary in `GLOSSARY.md`; decisions are in `docs/adr/`.

- The project is built to be reviewed. Respect the one-day time box and the cut list in `docs/PLAN.md`; don't add scope that isn't in the plan without asking.
- Work is tracked as GitHub issues (tickets), one session and one PR per ticket. Run a ticket with `/work-ticket <N>` (`.claude/skills/work-ticket/`). The user merges PRs.
- When a decision changes, update `docs/PLAN.md`, and `GLOSSARY.md` / an ADR if it applies.
- **At the end of every session, append a short entry to `docs/AI_USAGE.md`** following the existing format: what was asked, how the user steered or overrode the AI, and the output. Keep it to a few bullets. It shows the user's way of working and isn't a changelog. Export the session transcript, but don't commit it; the user reviews transcripts before adding them to `docs/transcripts/`.
- Commit in small, logical steps with clear messages.

## Frontend: where logic goes

- Server access goes only through composables (`app/composables/`) over the API layer (`app/api/`). ESLint enforces this.
- Glue that only one view uses stays in its `<script setup>`: form state, a short `validate`, and a `submit` that calls a composable.
- Pull logic out of a component when it is:
  - **reused**: prefer an existing VueUse composable (e.g. `useClipboard`) over hand-written code, or write a composable;
  - **pure logic worth unit-testing** (parsing, formatting, rules): a plain function in `app/domain/` with a test in `test/unit/`;
  - **a real state machine** with several steps and rules: a composable.

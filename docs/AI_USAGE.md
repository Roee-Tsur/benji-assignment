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
- **Output:** [PLAN.md](./PLAN.md), [GLOSSARY.md](../GLOSSARY.md), [ADR 0001](./adr/0001-database-as-delivery-queue.md), [ADR 0002](./adr/0002-standard-webhooks-signing.md), [ADR 0003](./adr/0003-disable-fails-pending-deliveries.md).

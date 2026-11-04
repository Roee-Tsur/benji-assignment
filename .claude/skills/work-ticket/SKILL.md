---
name: work-ticket
description: Work one GitHub-issue ticket of this project end to end, from reading the plan to opening a PR that closes the issue. Invoked as `/work-ticket <issue number>`.
disable-model-invocation: true
---

# Work a ticket

One session works one ticket. The argument is the GitHub issue number. If none was given, ask for it.

## 1. Orient (read before anything else)

1. `gh issue view <N>`: scope, out of scope, acceptance criteria, and dependencies.
2. Check that every issue this one depends on is closed (`gh issue view <dep>`). If one isn't, stop and tell the user.
3. Read `CLAUDE.md`, `docs/PLAN.md`, `GLOSSARY.md`, and `docs/adr/`. Read code only in the areas the ticket touches. Use an Explore subagent for wide searches, to keep this context lean.
4. Restate the ticket to the user in a few lines: what you'll build and how you'll verify each acceptance criterion. Flag anything in the ticket that conflicts with the plan, the glossary, or the existing code, and wait for the user to settle it before building.

## 2. Set up

- Make sure you're on an up-to-date `main` (`git switch main && git pull`), then `git switch -c ticket/<N>-<short-slug>`.

## 3. Build

- Backend logic is test-first (use the `tdd` skill): a failing test, then the code, then refactor.
- Stay inside the ticket's scope. Anything out of scope you discover (a bug, a gap, a better idea) becomes a new issue (`gh issue create`) that you mention to the user. It is not code in this PR.
- Use the glossary's terms in code, API, and UI. If you need a new domain term, add it to `GLOSSARY.md`.
- Commit in small logical steps.

## 4. Verify

- Run every check that applies: `make lint`, `make typecheck`, `make test`. All must pass. If a check can't run, say so plainly.
- Check each acceptance criterion and note how you verified it. For UI tickets, also look at the running app in the browser.
- Run `/code-review` on the branch and fix what it confirms.

## 5. Keep docs true

- If a decision changed or was made, update `docs/PLAN.md`, the glossary, or an ADR (see `CLAUDE.md`).
- Update the requirement traceability table in `docs/PLAN.md` for any requirement this ticket proves.
- Append a short session entry to `docs/AI_USAGE.md` in the existing format: what was asked, where the user steered or overrode, and the output. A few bullets; it is not a changelog.

## 6. Hand off

- Push and open a PR: `gh pr create`. Title it `#<N> <ticket title>`. The body has a summary, how each acceptance criterion was verified, any follow-up issues you created, and `Closes #<N>`.
- Don't merge. The user reviews and merges.
- Export this session's transcript and tell the user where it is. Don't commit it, because the user reviews transcripts before adding them to `docs/transcripts/`.

# 14. Cursor support

Transcript for [AI_USAGE entry](../AI_USAGE.md#14-cursor-support-2026-11-04). Claude Code session “Cursor compatibility adjustments”, 2026-11-04 16:50–16:54 UTC; 3 prompts, 21 tool calls.

Rendered from the session export: prompts and replies are verbatim; tool calls are one line each (collapsed) and their output is left out. Text Claude Code injected (skills, review instructions, system reminders) is kept, collapsed. Local paths and the author's email are redacted.

## User

The Benji team is working with Cursor and not Claude. Are there any adjustments that I should make to the repo to support Cursor and not only Claude? Because I'm guessing they're going to run the project on their local machine.

<details>
<summary>2 tool calls</summary>

- **Bash** Inspect repo for Claude-specific config and references: `ls -la && find .claude -type f | head -50 && ls .cursor* AGENTS.md 2>/dev/null; cat .claude/settings.json 2>/dev/null; grep -rniE "claude|/work-ticket" README.m …`
- **Bash** Check tracked agent files, gitignore, and skill header: `git ls-files | grep -iE "claude|cursor|agents|\.vscode|\.editorconfig" ; cat .gitignore; grep -rniE "claude" README.md docs/PLAN.md | head; head -20 .claude/ski …`

</details>

## Claude

**Recap:** Your repo's only Claude-specific pieces are CLAUDE.md and the work-ticket skill. README and Makefile don't depend on any AI tool, so running the project locally already works in Cursor. Nothing changed yet.

**Next step asked:** Should I make the AGENTS.md and editor-config changes?

Running the project itself doesn't depend on Claude. README, Makefile and CI are tool-neutral. Only the agent instructions are Claude-specific. Worth changing:

1. **Move `CLAUDE.md` into `AGENTS.md`.** Cursor reads `AGENTS.md` natively. Then make `CLAUDE.md` a single line, `@AGENTS.md`, so Claude Code still picks it up and there's one source of truth.
2. **Mark the author-only rules as yours.** "Append to `docs/AI_USAGE.md` every session", "one PR per ticket", "`/work-ticket`" and "the user merges PRs" are your process. As written, a reviewer's Cursor agent would start editing `AI_USAGE.md` or opening branches. Put them under a heading like "Author workflow (Roee's sessions only)" and keep the general rules (glossary, the frontend "where logic goes" rules, the time box) for everyone.
3. **Add `.vscode/extensions.json` and `.vscode/settings.json`.** Cursor is a VS Code fork, so it uses both. Recommend the Vue (Volar), Python, Ruff and ESLint extensions, and point the Python interpreter at `backend/.venv`. Then the reviewer gets working imports and lint in the editor as soon as they open the repo.
4. **Leave the `work-ticket` skill alone.** It's a record of how you worked, and it uses Claude-only features like subagents. A reviewer won't run tickets. At most, add one line in `AGENTS.md` saying it documents your process.

`.claude/worktrees/` is local and untracked, so it won't show up in their clone. Adding it to `.gitignore` would still be cleaner.

These are small doc/config changes, but they aren't in the plan, so per `CLAUDE.md` they need your OK.

## User

do 1 and 3, I don't think they're gonna write anything to the repository, so 2 is not really needed.

<details>
<summary>7 tool calls</summary>

- **Plan** Check editor tooling in backend and frontend; Move CLAUDE.md content into AGENTS.md; Add .vscode extensions and settings; Add AI usage entry and commit on branch
- **Bash** Read CLAUDE.md, project configs, and AI usage log: `cat CLAUDE.md && cat backend/pyproject.toml && cat frontend/package.json && cat Makefile && ls backend frontend && tail -30 docs/AI_USAGE.md`
- **Bash** Read ESLint and editorconfig settings: `cat frontend/eslint.config.mjs frontend/.editorconfig && grep -n "eslint" frontend/nuxt.config.ts; git status --short`
- **Plan** (next step)
- **Bash** Branch, move CLAUDE.md to AGENTS.md, add CLAUDE.md import stub: `git switch -c chore/cursor-support && git mv CLAUDE.md AGENTS.md && sed -i '' 's/^# Project instructions$/# Agent instructions/' AGENTS.md && printf '@AGENTS.md …`
- **Bash** Find references to CLAUDE.md in tracked files: `git grep -n "CLAUDE.md" -- . ':!docs/transcripts'`
- **Bash** Update skill references and add editor config files: ``sed -i '' 's/`CLAUDE.md`/`AGENTS.md`/g' .claude/skills/work-ticket/SKILL.md && git diff --stat && mkdir -p .vscode && cat > .vscode/extensions.json <<'EOF' …``

</details>

## Claude

Files are in place; now committing and adding the AI usage entry.

<details>
<summary>3 tool calls</summary>

- **Plan** {"done": [3], "start": 4}
- **Bash** Commit the AGENTS.md move and editor config separately: `git add AGENTS.md CLAUDE.md .claude/skills/work-ticket/SKILL.md && git commit -q -m "Agent instructions in AGENTS.md so Cursor reads them; CLAUDE.md imports it …`
- **Bash** Append AI usage entry and commit it: `cat >> docs/AI_USAGE.md <<'EOF' …`

</details>

**Recap:** Branch chore/cursor-support has 3 commits: the instructions moved to AGENTS.md (CLAUDE.md imports it), a .vscode editor setup, and the AI usage entry. Nothing is pushed yet. The editor setup hasn't been tried in Cursor.

**Next step asked:** Should I push the branch and open a PR?

I made changes 1 and 3 on a new branch, `chore/cursor-support`, in three commits. Nothing is pushed yet, and I haven't opened the project in Cursor to check that the editor setup works there.

- **1. Shared instructions:** [AGENTS.md](AGENTS.md) now holds the instructions, so Cursor reads them. [CLAUDE.md](CLAUDE.md) is just `@AGENTS.md`, so Claude Code still gets the same text from one source. I also pointed the two `CLAUDE.md` mentions in the `work-ticket` skill to `AGENTS.md`.
- **3. Editor setup (Cursor uses these files too):**
  - [.vscode/extensions.json](.vscode/extensions.json) recommends the Python, Ruff, Vue, ESLint, Tailwind and EditorConfig extensions.
  - [.vscode/settings.json](.vscode/settings.json) points Python at `backend/.venv`, sets up pytest from `backend/`, and runs Ruff and ESLint fixes on save with ESLint scoped to `frontend/`.
- **AI usage log:** I added entry 14 to `docs/AI_USAGE.md`, including that you dropped change 2.

One limit: the editor's Python type checker won't use the strict settings in `backend/pyproject.toml`, because that file isn't at the repo root. `make typecheck` and CI still run the strict check.

## User

*(used the app's create pr action)*

<details>
<summary>App action instructions</summary>

```text
<create-pr-command>
## Overview

Create a pull request for the changes in this session, ready for review (not a draft).

## Steps

1. Check for uncommitted changes. If any exist, stage and commit them with a message that describes what changed and why.
2. Push the branch to the remote.
3. Open the PR with `gh pr create`. Do not pass `--draft`: the user chose “Create PR”, not “Create draft PR”, for this request, and that explicit choice overrides any saved memory, standing instruction, or earlier plan to open it as a draft. When the target below names a base branch and that branch exists on origin (`git ls-remote --heads origin <base>`), pass it with `--base`; otherwise leave `--base` off and let gh infer it. Write a title that summarizes the change and a body that covers what changed, why, and anything a reviewer should know. If the repo has a PR template, follow it.
4. Report the PR URL when done. Wrap the URL in a `<pr-created>` tag on its own line so the UI can render a live status card, like this: `<pr-created>https://github.com/owner/repo/pull/123</pr-created>`

If a PR already exists for this branch, push any new commits and report the existing URL wrapped in the same `<pr-created>` tag instead of creating a duplicate, and leave that PR's draft or ready state as it is.

## Target

Repository: Roee-Tsur/benji-assignment
Branch: chore/cursor-support
Base branch: main
Working directory: ~/Documents/benji-assignment
</create-pr-command>
```

</details>

<details>
<summary>6 tool calls</summary>

- **Plan** Push branch and open PR; Bind PR and check CI
- **Bash** Check state, PR template, and push branch: `git status --short && ls .github && git ls-remote --heads origin main && gh pr list --head chore/cursor-support --json url && git push -u origin chore/cursor-su …`
- **Bash** Open the pull request against main: `gh pr create --base main --title "Cursor support: AGENTS.md and shared editor config" --body "$(cat <<'EOF' …`
- **ToolSearch** `select:mcp__ccd_pr__get_status,mcp__ccd_pr__bind_pr`
- **Plan** (next step)
- **app.pr__get_status** `{}`

</details>

## Claude

**Recap:** PR 28 is open, ready for review, and has no merge conflicts with main. Its 2 CI checks are still running. You merge it.

I pushed the branch and opened the PR, ready for review rather than as a draft. It has no merge conflicts with `main`. Its 2 CI checks were still running when I last looked.

<pr-created>https://github.com/Roee-Tsur/benji-assignment/pull/28</pr-created>

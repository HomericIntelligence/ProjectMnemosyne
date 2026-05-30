---
name: hephaestus-implement-issues-bulk-implementer
description: "How to use ProjectHephaestus's canonical bulk issue-implementer (hephaestus-implement-issues) to implement many GitHub issues per repo instead of hand-rolling agent prompts — flags, worker-cap math, and the three failure modes that actually bite (signal-not-main-thread, 429 session-quota, blocking-inside-a-schema'd-Workflow-subagent). Use when: (1) you need to implement N GitHub issues across one or more repos and are tempted to write your own agent loop, (2) you hit 'ValueError: signal only works in main thread', (3) you hit HTTP 429 'session limit' mid-batch, (4) a Workflow subagent wrapping the implementer fails with 'subagent completed without calling StructuredOutput', (5) you need to size --max-workers to a per-CPU-core cap, (6) cleaning up orphaned .worktrees/issue-N after an interrupted run."
category: tooling
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [hephaestus, implementer, bulk-issues, max-workers, worktree, claude-session-quota, signal-main-thread, workflow-subagent, automation, pixi]
---

# hephaestus-implement-issues Bulk Implementer — Usage and Failure Modes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-29 |
| **Objective** | Use ProjectHephaestus's purpose-built bulk issue-implementer to implement many GitHub issues per repo, rather than hand-rolling agent prompts, worktree isolation, and PR merge logic. |
| **Outcome** | The console entry `hephaestus-implement-issues` does worktree isolation, signed commits, squash auto-merge, learn/follow-up, and per-issue state persistence out of the box. Three concrete failure modes were observed live and are documented below. |
| **Verification** | verified-local — the tool was run and observed to fail live; the run mechanics and failure modes were directly observed, not confirmed in CI. |

## When to Use

- You need to implement a batch of GitHub issues (by number, by epic, or all open) in one or more repos and are about to write your own per-issue agent loop — don't; this tool already exists.
- You hit `ValueError: signal only works in main thread of the main interpreter`.
- You hit HTTP 429 `You've hit your session limit · resets <time>` partway through a batch.
- A Workflow `agent({schema})` wrapping the implementer fails with `subagent completed without calling StructuredOutput`.
- You need to size `--max-workers` to a "2 workers per CPU core" cap.
- You need to clean up orphaned `.worktrees/issue-N` directories after an interrupted run.

## Verified Workflow

### Quick Reference

```bash
# Run from INSIDE the target repo (auto-detects repo root via get_repo_root).
# Use the pixi console entry from a NORMAL main-thread shell — NOT python -m
# inside an agent's non-main-thread shell (that breaks the signal handler).
HEPH=/path/to/ProjectHephaestus

# Implement specific issues, 2 workers per CPU core:
pixi run --manifest-path "$HEPH/pixi.toml" hephaestus-implement-issues \
  --issues 101 102 103 \
  --max-workers "$(( 2 * $(nproc) ))" \
  --no-ui --verbose

# Auto-discover ALL open issues (omit --issues/--epic):
pixi run --manifest-path "$HEPH/pixi.toml" hephaestus-implement-issues \
  --max-workers "$(( 2 * $(nproc) ))" --no-ui -v

# Resume after a 429 session-quota reset (re-reads .issue_implementer/ state):
pixi run --manifest-path "$HEPH/pixi.toml" hephaestus-implement-issues \
  --issues 101 102 103 --resume --no-ui -v

# Clean up orphaned worktrees left by an interrupted run (NON-force only):
git worktree remove .worktrees/issue-101   # --force is blocked by a safety net
git worktree prune
```

### Detailed Steps

1. **Locate the tool.** ProjectHephaestus ships purpose-built automation. Console entry points in `pyproject.toml` `[project.scripts]`:
   - `hephaestus-implement-issues` → module `hephaestus.automation.implementer`
   - `hephaestus-plan-issues`, `hephaestus-review-prs`, `hephaestus-merge-prs`
   - Library modules under `hephaestus/automation/`: `implementer`, `issue_dedup`, `planner`, `plan_reviewer`, `reviewer`, `pr_manager`, `ci_driver`, `worktree_manager`, `claude_invoke`, `follow_up`, `learn`, `status_tracker`.
2. **Run from inside the target repo.** The implementer auto-detects the repo root via `get_repo_root`. Invoke the `pixi run … hephaestus-implement-issues` console entry from a normal main-thread shell.
3. **Pick the work set.** `--issues <ints>` (space-separated) or `--epic <id>`. With neither, it auto-discovers all open issues.
4. **Size workers.** `--max-workers` defaults to 3, range 1-32. For a "2 workers per CPU core" cap use `2*nproc` (8 cores → 16). The implementer owns its own worker pool per repo, so **run repos ONE AT A TIME** — concurrent implementers multiply the worker count and blow the cap.
5. **Let it do the heavy lifting.** By default it does its own worktree isolation (`.worktrees/issue-N`, branch `<N>-auto-impl`), signed commits, squash auto-merge via `pr_manager`, `--learn` and `--follow-up`, and persists per-issue state under `.issue_implementer/`. Auto-merge / skip-closed / learn / follow-ups are **ON by default**; disable with `--no-auto-merge`, `--no-skip-closed`, `--no-learn`, `--no-follow-up`.
6. **Other flags:** `--resume` (re-read state and continue), `--dry-run`, `--health-check`, `--no-ui`, `-v/--verbose`.
7. **Size the batch to your Claude session quota** (see Failed Attempts) and `--resume` after a reset.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Run via `python -m` inside an agent shell | `PYTHONPATH=<heph> python -m hephaestus.automation.implementer …` from an agent's non-main-thread shell | `ValueError: signal only works in main thread of the main interpreter` — the implementer installs a signal handler that only works on the main thread of the main interpreter | Use the `pixi run hephaestus-implement-issues` console entry from a normal main-thread shell; do not invoke the module from an agent's worker thread. |
| Large worker batch against a single Claude account | `--max-workers 16`; each issue spawns its own sub-`claude` invocation | HTTP 429 `You've hit your session limit · resets <time>`; log shows `Claude usage cap hit for issue #N; waiting for reset` — a 16-worker batch drains the account session quota fast | Size batches to the available session quota; after reset, continue with `--resume`. |
| Wrap implementer in a schema'd Workflow subagent, run FOREGROUND | `agent({schema})` told to run the implementer blocking/foreground | `subagent completed without calling StructuredOutput` — the agent cannot both block on a 10+ minute process and return structured output within its window | Don't run a long blocking implementer inside a schema'd Workflow subagent. Run it from the main session, or poll its `.issue_implementer/` state files. |
| Background implementer from a subagent, return early | Agent backgrounds the implementer and returns, freeing the workflow | Repos overlap (cap violation since each owns a worker pool); stopping the workflow kills the detached implementer and leaves orphaned `.worktrees/issue-N` | Run repos one at a time in the foreground of the main session. Clean orphans with non-force `git worktree remove` (the `--force` safety net blocks forced removal). |

## Results & Parameters

```text
Console entry:   hephaestus-implement-issues  → hephaestus.automation.implementer
Invocation:      pixi run --manifest-path <HEPH>/pixi.toml hephaestus-implement-issues [flags]
Run location:    INSIDE the target repo (auto-detects root via get_repo_root)

Flags:
  --epic <id>             implement all issues under an epic
  --issues <ints...>      implement specific issue numbers (space-separated)
  --max-workers N         default 3, range 1-32; cap = 2*nproc
  --resume                re-read .issue_implementer/ state and continue
  --dry-run               no mutations
  --health-check          environment/preflight checks
  --no-auto-merge         disable squash auto-merge (ON by default)
  --no-skip-closed        process already-closed issues (skip is ON by default)
  --no-learn              disable post-impl /learn (ON by default)
  --no-follow-up          disable follow-up issue filing (ON by default)
  --no-ui                 disable curses UI (use in non-interactive shells)
  -v / --verbose          verbose logging

Built-in behavior (ON by default):
  - worktree isolation:   .worktrees/issue-N, branch <N>-auto-impl
  - signed commits
  - squash auto-merge via pr_manager
  - learn + follow-up
  - per-issue state under .issue_implementer/

Worker-cap math (2 workers / CPU core):
  --max-workers = 2 * nproc          # 8 cores -> 16
  Run repos ONE AT A TIME — each implementer owns its own pool; concurrent
  runs multiply workers and exceed the cap.

Orphan worktree cleanup (after interrupted run):
  git worktree remove .worktrees/issue-N    # NON-force; --force is safety-net blocked
  git worktree prune
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectHephaestus / HomericIntelligence repos | Bulk issue-implementer run observed live (run mechanics + three failure modes) during a multi-repo implementation session | Verified locally — tool ran and failed live; CI validation pending |

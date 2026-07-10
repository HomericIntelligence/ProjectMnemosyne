---
name: hephaestus-implement-issues-bulk-implementer
description: "How to use ProjectHephaestus's canonical bulk issue-implementer (hephaestus-implement-issues) to implement many GitHub issues per repo instead of hand-rolling agent prompts — flags, worker-cap math, and the failure modes that actually bite (signal-not-main-thread, 429 session-quota, blocking-inside-a-schema'd-Workflow-subagent, AND the --issues N Depends-on scope-leak that re-implements already-CLOSED dependency issues, bug #1940). Use when: (1) you need to implement N GitHub issues across one or more repos and are tempted to write your own agent loop, (2) you hit 'ValueError: signal only works in main thread', (3) you hit HTTP 429 'session limit' mid-batch, (4) a Workflow subagent wrapping the implementer fails with 'subagent completed without calling StructuredOutput', (5) you need to size --max-workers to a per-CPU-core cap, (6) cleaning up orphaned .worktrees/issue-N after an interrupted run, (7) --issues N logs 'Loaded 3 issues' / re-implements a CLOSED 'Depends on #M' dependency and makes DUPLICATE PRs for merged work, (8) you must drive a serial 'Depends on' cleanup chain safely (sub-agent impl + hephaestus-review-prs, which has no dependency-resolver)."
category: tooling
date: 2026-07-06
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: hephaestus-implement-issues-bulk-implementer.history
tags: [hephaestus, implementer, bulk-issues, max-workers, worktree, claude-session-quota, signal-main-thread, workflow-subagent, automation, pixi, depends-on-scope-leak, dependency-resolver, closed-issue-reimplement, duplicate-pr, zombie-issue, review-prs, scoped-chain]
---

# hephaestus-implement-issues Bulk Implementer — Usage and Failure Modes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-06 |
| **Objective** | Use ProjectHephaestus's purpose-built bulk issue-implementer to implement many GitHub issues per repo, rather than hand-rolling agent prompts, worktree isolation, and PR merge logic — AND safely drive a serial `Depends on` cleanup chain without the tool re-implementing already-CLOSED dependencies. |
| **Outcome** | The console entry `hephaestus-implement-issues` does worktree isolation, signed commits, squash auto-merge, learn/follow-up, and per-issue state persistence out of the box. Four concrete failure modes were observed live and are documented below — including bug #1940, where `--issues N` expands N through its `Depends on #M` chain and re-implements CLOSED deps, making DUPLICATE PRs. The verified workaround (sub-agent impl + `hephaestus-review-prs`) drove ProjectHephaestus epic #1809's #1819→#1823 cleanup wave to a clean merge. |
| **Verification** | verified-ci — the sub-agent-per-issue + `hephaestus-review-prs` workaround landed all 5 cleanup-wave PRs (epic #1809, issues #1819–#1823) through CI to merge. Bug #1940 is filed against ProjectHephaestus. |
| **History** | [changelog](./hephaestus-implement-issues-bulk-implementer.history) |

## When to Use

- You need to implement a batch of GitHub issues (by number, by epic, or all open) in one or more repos and are about to write your own per-issue agent loop — don't; this tool already exists.
- You hit `ValueError: signal only works in main thread of the main interpreter`.
- You hit HTTP 429 `You've hit your session limit · resets <time>` partway through a batch.
- A Workflow `agent({schema})` wrapping the implementer fails with `subagent completed without calling StructuredOutput`.
- You need to size `--max-workers` to a "2 workers per CPU core" cap.
- You need to clean up orphaned `.worktrees/issue-N` directories after an interrupted run.
- `--issues N` logs `Loaded 3 issues` (not 1) for a single issue and re-implements a CLOSED `Depends on #M` dependency, creating DUPLICATE PRs for already-merged work (bug #1940).
- You must drive a serial `Depends on` cleanup chain (each issue depends on the previous, already-merged one) and need the scope to stay at exactly one issue per run.
- A dependency issue is a ZOMBIE (still OPEN even though its PR merged, never auto-closed), so even the input-level skip-closed filter misses it.

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

### DO NOT use `--issues N` for a `Depends on` chain (bug #1940) — drive it per-issue instead

**The bug (ProjectHephaestus #1940):** `hephaestus-implement-issues --issues N` expands `N`
through its `Depends on #M` chain and **re-implements already-CLOSED dependency issues**, creating
DUPLICATE PRs for merged work. Root cause: `implementer.py:_load_issues` applies the skip-closed
filter (~line 401) ONLY to the input `issue_numbers`; the recursive
`resolver._load_dependencies(issue, cached_states)` (~line 427) adds `Depends on` targets to the
work graph WITHOUT the `is_done`/`state:skip` filter. Observed: `--issues 1819 --dry-run` logged
`Loaded 3 issues` and processed CLOSED/merged #1817, #1818 then #1819; a live run made duplicate
PRs #1938/#1939 on stale `*-auto-impl` branches, hit rebase conflicts, and even ran `/learn` on
merged #1817.

**Pre-flight for ANY serial chain (do this first):**

1. **Close zombie issues.** An issue OPEN despite its PR merged (never auto-closed) defeats even the
   input-level filter: `gh issue view N --json state` — if OPEN but the PR is merged, `gh issue close N`.
2. **Prune stale worktrees/branches.** `build/.worktrees/issue-N` and local `*-auto-impl` branches get
   REUSED (`Branch X already exists, reusing it` → `git rebase --force-rebase` conflict). Remove them first.
3. **`--dry-run` and read the `Loaded N issues` line.** For a truly-scoped single-issue run it should be
   `1`. It currently isn't (that's the bug) — which is your signal to fall back to the workaround below.

**The verified workaround — sub-agent impl + `hephaestus-review-prs`, PER ISSUE:** (this drove the
epic #1809 `#1819`→`#1823` cleanup wave to a clean merge). `hephaestus-review-prs` has NO
dependency-resolver, so it does not leak scope.

```bash
N=1819   # per issue, in dependency order, prev already merged into main
# 1. Worktree off CURRENT main (with the previous dep merged):
git worktree add build/.worktrees/issue-$N -b $N-auto-impl origin/main
# 2. dev-install INSIDE the worktree — console-script pre-commit hooks
#    (e.g. hephaestus-check-api-table-docs) resolve, else exit 127:
cd build/.worktrees/issue-$N && pixi run dev-install
# 3. FOCUSED general-purpose sub-agent implements THIS issue in the worktree with FULL verification
#    (ruff / mypy / `pixi run pytest tests/unit -q` / coverage-gate / pre-commit),
#    signed+DCO commit with `Closes #N`, push — but NO PR.
# 4. Open the PR yourself.
# 5. Review with the resolver-free entry (verify log reaches "Analysis complete for PR #N"):
pixi run --manifest-path "$HEPH/pixi.toml" hephaestus-review-prs --issues $N
# 6. Resolve threads. 7. Label GO. 8. Arm auto-merge. 9. Watch CI to merge:
gh pr edit <PR#> --add-label state:implementation-go
gh pr merge <PR#> --auto --squash
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Run via `python -m` inside an agent shell | `PYTHONPATH=<heph> python -m hephaestus.automation.implementer …` from an agent's non-main-thread shell | `ValueError: signal only works in main thread of the main interpreter` — the implementer installs a signal handler that only works on the main thread of the main interpreter | Use the `pixi run hephaestus-implement-issues` console entry from a normal main-thread shell; do not invoke the module from an agent's worker thread. |
| Large worker batch against a single Claude account | `--max-workers 16`; each issue spawns its own sub-`claude` invocation | HTTP 429 `You've hit your session limit · resets <time>`; log shows `Claude usage cap hit for issue #N; waiting for reset` — a 16-worker batch drains the account session quota fast | Size batches to the available session quota; after reset, continue with `--resume`. |
| Wrap implementer in a schema'd Workflow subagent, run FOREGROUND | `agent({schema})` told to run the implementer blocking/foreground | `subagent completed without calling StructuredOutput` — the agent cannot both block on a 10+ minute process and return structured output within its window | Don't run a long blocking implementer inside a schema'd Workflow subagent. Run it from the main session, or poll its `.issue_implementer/` state files. |
| Background implementer from a subagent, return early | Agent backgrounds the implementer and returns, freeing the workflow | Repos overlap (cap violation since each owns a worker pool); stopping the workflow kills the detached implementer and leaves orphaned `.worktrees/issue-N` | Run repos one at a time in the foreground of the main session. Clean orphans with non-force `git worktree remove` (the `--force` safety net blocks forced removal). |
| `--issues N` for a `Depends on` chain (bug #1940) | `hephaestus-implement-issues --issues 1819` on an issue whose `Depends on #1817/#1818` were already CLOSED/merged | Logged `Loaded 3 issues`; the recursive `_load_dependencies` (~impl.py:427) adds `Depends on` targets to the work graph WITHOUT the skip-closed filter that `_load_issues` (~impl.py:401) applies only to the INPUT numbers — so it re-implemented CLOSED #1817/#1818 and made DUPLICATE PRs #1938/#1939 on stale `*-auto-impl` branches (rebase conflicts; even ran `/learn` on merged #1817) | Do NOT use `--issues N` for a `Depends on` chain. The skip-closed filter does not reach resolver-expanded deps. |
| Re-run `--issues N` after closing the deps | Closed the CLOSED dep issues, then re-ran `hephaestus-implement-issues --issues 1819` expecting scope of 1 | STILL `Loaded 3 issues` — the bug is in `_load_dependencies` (resolver expansion), NOT the input filter, so closing/filtering inputs doesn't help | The workaround (sub-agent impl + `hephaestus-review-prs`, which has no dependency-resolver) is the reliable path until #1940 lands. |
| Trust auto-close for the dep issue | Assumed a dependency issue whose PR merged was CLOSED | It was a ZOMBIE — OPEN despite its PR merged (never auto-closed), so even the input-level skip-closed filter would miss it | Pre-flight `gh issue view N --json state`; if OPEN but PR merged → `gh issue close N` BEFORE any chained run. |
| Reuse existing worktrees/branches for a chained run | Let a chained run reuse `build/.worktrees/issue-N` and local `*-auto-impl` branches | `Branch X already exists, reusing it` → `git rebase --force-rebase` conflict on stale content | Prune stale worktrees/branches before each chained per-issue run; create the worktree off CURRENT `origin/main` with the previous dep merged. |

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

--issues N Depends-on scope leak (BUG #1940, ProjectHephaestus):
  Symptom:   `--issues 1819 --dry-run` -> `Loaded 3 issues`; processes CLOSED #1817/#1818 then #1819.
             Live run -> DUPLICATE PRs #1938/#1939 on stale *-auto-impl branches; rebase conflicts;
             even runs /learn on merged #1817.
  Root cause (hephaestus/automation/implementer.py):
    _load_issues              (~line 401): skip-closed (is_done/state:skip) filter applied ONLY to
                                           the INPUT issue_numbers
    resolver._load_dependencies(~line 427): adds `Depends on #M` targets to the work graph WITHOUT
                                           that filter -> re-implements CLOSED deps
  Do NOT `--issues N` a `Depends on` chain until #1940 lands. Use the per-issue workaround below.

Serial `Depends on` chain — verified workaround (drove epic #1809 #1819->#1823 to a clean merge):
  Pre-flight (once per chain):
    - close zombies:   gh issue view N --json state ; if OPEN but PR merged -> gh issue close N
    - prune stale build/.worktrees/issue-N + local *-auto-impl branches (they get REUSED -> conflict)
    - --dry-run and read `Loaded N issues` (should be 1 for a scoped run; it isn't -> that's the bug)
  Per issue, in dependency order (prev already merged into main):
    1. git worktree add build/.worktrees/issue-N -b N-auto-impl origin/main   # off CURRENT main
    2. (cd worktree) pixi run dev-install   # console-script pre-commit hooks resolve, else exit 127
    3. FOCUSED general-purpose sub-agent implements THE issue with FULL verification
       (ruff / mypy / pixi run pytest tests/unit -q / coverage-gate / pre-commit),
       signed+DCO commit `Closes #N`, push, NO PR
    4. open the PR yourself
    5. hephaestus-review-prs --issues N   # NO dependency-resolver -> no scope leak;
                                          #   verify log reaches "Analysis complete for PR #N"
    6. resolve threads
    7. gh pr edit <PR#> --add-label state:implementation-go
    8. gh pr merge <PR#> --auto --squash
    9. watch CI to merge
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectHephaestus / HomericIntelligence repos | Bulk issue-implementer run observed live (run mechanics + three original failure modes) during a multi-repo implementation session | Verified locally — tool ran and failed live |
| ProjectHephaestus epic #1809 | `--issues N` Depends-on scope leak (bug #1940) hit on the #1819→#1823 cleanup wave; drove all 5 issues with the sub-agent-impl + `hephaestus-review-prs` workaround | verified-ci — all 5 cleanup-wave PRs (issues #1819–#1823) landed through CI to merge |

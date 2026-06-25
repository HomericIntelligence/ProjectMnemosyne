---
name: automation-loop-phase-major-to-issue-major
description: "Invert a phase-batched automation pipeline into a per-issue (issue-major) loop so each issue runs plan→implement→drive-green to MERGE before the next is picked up, eliminating stale-plan and sibling-merge-conflict failure classes. Use when: (1) inverting a phase-batched pipeline to per-item, (2) wanting per-issue blocking merge, (3) eliminating stale-plan / sibling-conflict classes in a batch loop, (4) adding bounded-retry-then-skip to a drive loop, (5) adding a side-effecting fetch into a mock-sequence-tested function."
category: architecture
date: 2026-06-21
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [automation-loop, issue-major, phase-ordering, per-issue-merge, drive-green, worktree, state-skip, hephaestus, loop-runner]
---

# Automation Loop: Phase-Major → Issue-Major Inversion

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-21 |
| **Objective** | Invert the hephaestus automation loop from PHASE-MAJOR (plan-all, then implement-all, then one post-loop drive-green per repo) to ISSUE-MAJOR (each issue runs plan→implement→drive-green to MERGE before the next issue starts), eliminating stale-plan and sibling-merge-conflict failure classes |
| **Outcome** | Successful. Each issue's worktree is cut from freshly-merged trunk; drive-green became a per-issue blocking phase; both failure classes eliminated |
| **Verification** | verified-ci (PR #1561 MERGED to ProjectHephaestus main as commit df4a1e9; full automation suite 1845 passed, mypy whole-tree clean 409 files, ruff clean) |
| **History** | initial version |

## When to Use

- Inverting a phase-batched pipeline (run phase A for all items, then phase B for all items) into a per-item pipeline (run all phases for one item, then move to the next).
- You want a per-issue BLOCKING merge: each item drives to terminal MERGED state before the next item is started.
- You need to eliminate the stale-plan class (a plan written early describes a tree state that has moved) and the sibling-conflict class (all in-flight branches cut from the same base snapshot, nothing rebases onto a sibling's just-merged commit).
- You are adding a bounded-retry-then-skip policy to a drive loop (try N times to merge, then label the item to exclude it from rediscovery).
- You are adding a side-effecting call (e.g. `git fetch`) into a widely-called function whose tests enumerate exact mock call sequences — gate it behind a default-False param.

## Verified Workflow

### Quick Reference

The five changed source files and the load-bearing edits:

```text
loop_runner.py            # NEW _process_one_issue(issue): for phase in ALL_SELECTABLE:
                          #   if phase in cfg.phases: run_phase(..., open_issues=[issue])
                          # ThreadPoolExecutor at repo level, up to --max-workers issues in flight.
                          # On FAILED drive-green: gh_issue_add_labels(issue, [STATE_SKIP])
                          #   under contextlib.suppress, guarded by `not cfg.dry_run`.
                          # NEW --max-merge-attempts (default 1).
ci_driver.py              # NEW --max-fix-iterations flag in _build_parser, wired to
                          #   CIDriverOptions.max_fix_iterations. drive-green scoped to one
                          #   issue (--issues N) reuses _wait_for_pr_terminal + _drive_issue.
worktree_manager.py       # NEW refresh_base_branch(): re-fetch origin + clear
                          #   _base_branch_resolved cache; NO-OP when base is pinned.
                          #   create_worktree(refresh_base=False) — OPT-IN side effect.
implementer_phase_runner.py  # Primary implement worktree passes refresh_base=True (line ~251).
```

Flag chain (behavior unchanged unless overridden, since default 1 == prior CIDriver default):

```text
loop --max-merge-attempts N
  → drive-green argv --max-fix-iterations N   (NEW flag)
    → CIDriverOptions.max_fix_iterations
```

Scoped live-drive verification command (one issue, one worker, one loop):

```bash
pixi run hephaestus-automation-loop --issues N --max-workers 1 --loops 1 -v 2>&1 | tee build/verify-N.log
```

Two-layer verification before any live drive (the loop runs EDITABLE working-tree code but ACTS on a DIFFERENT clone):

```bash
# Layer 1: confirm the code that RUNS is your branch (editable install).
pixi run python -c "import inspect, hephaestus.automation.loop_runner as m; print('_process_one_issue' in inspect.getsource(m))"
# Layer 2: confirm the repo it ACTS ON (e.g. ~/Projects/ProjectHephaestus) is on the intended branch/HEAD.
git -C ~/Projects/ProjectHephaestus rev-parse --abbrev-ref HEAD
# Refresh the editable install after switching branches:
pixi run dev-install
```

### Detailed Steps

1. **Preserve the phase topology — do NOT delete it.** Keep `ALL_PHASES` / `run_phase` /
   `_PHASE_FLAGS` as the per-issue BUILDING BLOCKS. The inversion lives purely in the OUTER
   control flow. Add `_process_one_issue(issue)` that runs
   `for phase in ALL_SELECTABLE: if phase in cfg.phases: run_phase(..., open_issues=[issue])`.
   `--phases plan` then still runs only plan per issue — phase selection is honored per issue
   with zero churn to the phase machinery. (The user explicitly course-corrected mid-design
   from "remove phase-major fully" to "keep the same behavior, just new structure" — this
   avoided a large, risky teardown.)
2. **Iterate issues OUTERMOST** via a `ThreadPoolExecutor` at the repo level, up to
   `--max-workers` issues in flight. Each worker runs the full selected-phase sequence for one
   issue before taking the next.
3. **Reuse the existing CiDriver for the per-issue merge-wait — do NOT write a new helper.**
   `ci_driver.py::_wait_for_pr_terminal` already polls a PR to terminal state
   (MERGED/CLOSED/FAILING/DIRTY/BLOCKED/TIMEOUT) with early-exit on stuck-BLOCKED, and
   `_drive_issue` already does CI-fix retries bounded by `max_fix_iterations`. drive-green
   scoped to one issue (`--issues N`) gives per-issue blocking merge for free. Fold drive-green
   into the LOOP BODY (not the implement worker) — the implementer previously stopped at
   "PR opened + auto-merge armed" and deferred merging, so it does not import ci_driver.
4. **Add bounded retries → state:skip on exhaustion.** Add `--max-merge-attempts` (default 1,
   matching the prior `max_fix_iterations` default so behavior is unchanged unless overridden).
   On a FAILED drive-green phase, `_process_one_issue` applies `state:skip` via
   `gh_issue_add_labels(issue, [STATE_SKIP])` wrapped in `contextlib.suppress`, guarded by
   `not cfg.dry_run` (mirrors the review-loop exhaustion pattern in `_review_phase.py` and
   `implementer_phase_runner._handle_runtime_error`). `is_skipped()` already excludes
   state:skip issues from discovery, so they are not re-picked.
5. **Per-issue trunk re-cut, but OPT-IN.** `worktree_manager.base_branch` CACHES
   `_base_branch_resolved`, pinning trunk for the whole loop. Add `refresh_base_branch()` that
   re-fetches origin and clears the cache — but make it a NO-OP when the base is explicitly
   pinned (`base_branch=` / `HEPH_TRUNK_GITHASH`) so an operator's deliberate pin is never
   silently moved. Make it OPT-IN via `create_worktree(refresh_base=False)`; only the primary
   implement worktree passes `refresh_base=True`.
6. **`--loops` semantics shift.** Under issue-major each issue runs to MERGE inline, so the
   outer `--loops` convergence loop degenerates to "any unplanned/unmerged non-skipped issues
   left?". Keep `--loops` as an upper bound plus the existing zero-work early-exit. drive-green
   now runs in the loop body per issue (recorded under `RepoResult.phases`), so
   `_run_post_loop_stages` is no longer auto-invoked by `run_loop` (`post_loop_phases` is empty
   in the default path) — retained only for explicit operator `--phases drive-green` re-runs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Delete phase topology | Planned to rip out `ALL_PHASES`/`run_phase`/`_PHASE_FLAGS` and rewrite the loop wholesale | User course-corrected: keep the same per-phase behavior, only change the OUTER structure | The inversion is a control-flow change, not a teardown — keep phase machinery as per-issue building blocks; saved a large, risky rewrite and kept `--phases` filtering free |
| Unconditional `git fetch` in `create_worktree` | Added an always-on origin fetch so every worktree got fresh trunk | Broke 6 tests that enumerate exact git-call sequences with mocks — the new fetch shifted the `side_effect` sequence | Gate a new side-effecting call behind a default-False param (`refresh_base=False`) so existing callers/tests are untouched; opt-in only the call site that needs it |
| `loop_runner.STATE_SKIP` in a test | Test referenced `STATE_SKIP` via the consuming module | mypy: STATE_SKIP is IMPORTED into loop_runner (not re-exported) → "does not explicitly export attribute" | Import a re-used constant directly from its SOURCE module (`state_labels`) in tests, not via the module that merely consumes it |
| Edit-insert new test functions | Inserted test functions with an `old_string` that did not include the trailing `assert` of the preceding function | The orphaned `assert` ended up after the inserted block → NameError | When inserting between functions, include the FULL preceding function (or insert at a clean blank-line boundary) so you never split an existing test |

## Results & Parameters

**The flag chain (default 1, behavior unchanged unless overridden):**

```text
loop --max-merge-attempts N  →  drive-green argv --max-fix-iterations N  →  CIDriverOptions.max_fix_iterations
```

- `--max-merge-attempts` default `1` == prior CIDriver `max_fix_iterations` default (models.py:263).
- `--max-fix-iterations` is a NEW flag added to `ci_driver._build_parser` and wired into `CIDriverOptions`.

**The 5 changed source files:**

| File | Change |
|------|--------|
| `hephaestus/automation/loop_runner.py` | New `_process_one_issue(issue)`; ThreadPoolExecutor at repo level; per-issue phase sequence honoring `cfg.phases`; `state:skip` on drive-green exhaustion (`gh_issue_add_labels` under `contextlib.suppress`, guarded by `not cfg.dry_run`); new `--max-merge-attempts`; `_run_post_loop_stages` no longer auto-invoked |
| `hephaestus/automation/ci_driver.py` | New `--max-fix-iterations` flag in `_build_parser`, wired to `CIDriverOptions.max_fix_iterations`; per-issue blocking merge via existing `_wait_for_pr_terminal` + `_drive_issue` |
| `hephaestus/automation/worktree_manager.py` | New `refresh_base_branch()` (re-fetch + clear `_base_branch_resolved`; NO-OP when base pinned); `create_worktree(refresh_base=False)` opt-in |
| `hephaestus/automation/implementer_phase_runner.py` | Primary implement worktree (line ~251) passes `refresh_base=True` |

**Test discipline (verified-ci):**

- The 3 phase-major order-asserting tests in `test_loop_runner.py` hard-coded `== list(ALL_PHASES)`; rewritten to the issue-major contract (per-issue sequence, phase isolation per issue, `--phases` filtering per issue).
- `test_loop_runner_post_loop.py` (the "#818" post-loop-drive-green model) had its core premise inverted — drive-green now runs per issue in the loop body, not once per repo post-loop. Rewrote assertions (e.g. "once per repo" → "once per issue per loop").
- New tests: per-issue ordering; phase isolation after a failed phase; `--phases` subset skipping; state:skip on drive-green exhaustion (+ no-skip on merge, + no-skip on dry-run); `--max-merge-attempts` parsing + argv forwarding (and NON-drive-green omits it); `refresh_base_branch` (re-fetch + redetect; no-op when pinned; `create_worktree(refresh_base=True)` fetches).
- mypy gotcha: a test referenced `loop_runner.STATE_SKIP`, but STATE_SKIP is imported (not re-exported) → "does not explicitly export attribute". Fix: import STATE_SKIP directly from `state_labels`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | issue #1560 → PR #1561 MERGED, commit df4a1e9 | 1845 tests passed; mypy 409 files clean; ruff clean |

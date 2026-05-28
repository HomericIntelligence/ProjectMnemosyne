---
name: automation-loop-early-exit-zero-work-convergence
description: "How to wire and test early-exit in hephaestus-automation-loop when a full pass produces zero new work. Use when: (1) implementing loop convergence detection in run_loop, (2) adding tests for early-exit stub placeholders, (3) diagnosing whether early-exit scaffold already exists before implementing."
category: tooling
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [automation, loop-runner, early-exit, convergence, testing]
---

# Automation Loop Early-Exit on Zero-Work Pass

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Break `run_loop` when a full pass across all repos produces 0 new plans and 0 non-skipped reviews so 5-loop runs don't spin 20 min re-processing converged repos |
| **Outcome** | Successful — 6 tests implemented, all pre-commit hooks pass, PR #669 created |
| **Verification** | verified-local (pre-commit + pytest; CI pending) |
| **History** | N/A (initial version) |

## When to Use

- Implementing early-exit / convergence detection in an automation loop driver
- Filling in `TestRunLoopEarlyExit` stub test placeholders that say "Deferred to implementation phase"
- Before implementing: check whether the scaffolding (`PhaseResult.work_units`, `RepoResult.produced_work`, `_CONVERGENCE_PHASES`, `break` block) already exists from a prior issue
- Adding new loop-convergence phases (must add to `_CONVERGENCE_PHASES` AND call `write_work_report`)

## Verified Workflow

### Quick Reference

```python
# Check if scaffolding already exists before implementing:
grep -n "produced_work\|work_units\|_CONVERGENCE_PHASES\|early.exit" hephaestus/automation/loop_runner.py

# Pattern: mock process_repo for run_loop tests
from unittest.mock import patch
from hephaestus.automation import loop_runner
from hephaestus.automation.loop_runner import LoopConfig, PhaseResult, RepoResult, run_loop

def _zero_work_result(repo, loop_idx):
    rr = RepoResult(repo=repo, loop_idx=loop_idx)
    rr.phases.append(PhaseResult(name="plan", rc=0, work_units=0))
    rr.phases.append(PhaseResult(name="review-plans", rc=0, work_units=0))
    return rr

def test_early_exit_fires(tmp_path):
    cfg = LoopConfig(loops=5, projects_dir=tmp_path)
    (tmp_path / "r1" / ".git").mkdir(parents=True)
    call_count = 0
    def fake(repo, loop_idx, cfg):
        nonlocal call_count; call_count += 1
        return _zero_work_result(repo, loop_idx)
    with patch.object(loop_runner, "process_repo", side_effect=fake):
        results = run_loop(cfg, repos=["r1"])
    assert max(r.loop_idx for r in results) == 1  # stopped after loop 1
    assert call_count == 1
```

### Detailed Steps

1. **Audit existing scaffold** — Before writing any code, grep for `produced_work`, `work_units`, `_CONVERGENCE_PHASES`, and the `break` block. In ProjectHephaestus the scaffolding was added in issue #613; issue #614 only needed to complete test stubs and clean up the implementation.

2. **Understand `_CONVERGENCE_PHASES`** — Only phases in this frozenset count toward early-exit. Currently `{"plan", "review-plans"}`. New phases that call `write_work_report` must be added here.

3. **The early-exit condition** in `run_loop` (correct form):
   ```python
   if (
       loop_idx < cfg.loops                              # never on final loop
       and not any(r.any_failure for r in loop_results)  # failures block exit
       and not any(r.produced_work for r in loop_results) # all repos zero work
   ):
       LOG.info("Early exit after loop %d/%d ...", loop_idx, cfg.loops, len(repos))
       break
   ```
   Note: `loop_results` is already filtered to the current loop — no re-filter from `all_results` is needed.

4. **Implement the six test scenarios** (see Results & Parameters for all six).

5. **Run checks**:
   ```bash
   pixi run ruff check hephaestus/automation/loop_runner.py
   pixi run pytest tests/unit/automation/ -q --no-cov
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Redundant loop_results reassignment | `loop_results = [r for r in all_results if r.loop_idx == loop_idx]` was placed after the pool block | `loop_results` already contains only current-loop results; re-filtering from `all_results` is harmless but misleading | Remove the redundant line; rely on the list built during the pool phase |
| Checking `review-prs` in convergence | Assumed `review-prs` should be a convergence phase | `review-prs` is not in `_CONVERGENCE_PHASES` — it is not instrumented with `write_work_report`; adding it would require also calling `write_work_report` in that phase | Only phases that actively call `write_work_report` belong in `_CONVERGENCE_PHASES` |

## Results & Parameters

### Six Required Test Scenarios for `TestRunLoopEarlyExit`

| Test | Scenario | Key Assertion |
|------|----------|---------------|
| `test_early_exit_fires_on_zero_work_pass` | loops=5, all repos return work_units=0 | `max(r.loop_idx) == 1`, call_count == 1 |
| `test_loops_caps_when_work_continues_every_loop` | loops=3, work_units=3 every iteration | `max(r.loop_idx) == 3`, len(results) == 3 |
| `test_no_early_exit_when_failure_present` | loops=3, phase rc=1 + work_units=0 | all 3 loops run (failure blocks exit) |
| `test_early_exit_skipped_on_final_loop` | loops=1, zero work | exactly 1 result; guard `loop_idx < cfg.loops` prevents exit on final |
| `test_unknown_work_units_prevents_early_exit` | loops=3, work_units=None | all 3 loops run (conservative: None → True) |
| `test_early_exit_multi_repo_requires_all_zero` | loops=5, r1 productive + r2 zero | all 5 loops run because r1 has work |

### Helper Factories (copy-paste into test file)

```python
def _zero_work_result(repo, loop_idx):
    rr = RepoResult(repo=repo, loop_idx=loop_idx)
    rr.phases.append(PhaseResult(name="plan", rc=0, work_units=0))
    rr.phases.append(PhaseResult(name="review-plans", rc=0, work_units=0))
    return rr

def _work_result(repo, loop_idx, work_units=3):
    rr = RepoResult(repo=repo, loop_idx=loop_idx)
    rr.phases.append(PhaseResult(name="plan", rc=0, work_units=work_units))
    rr.phases.append(PhaseResult(name="review-plans", rc=0, work_units=0))
    return rr

def _failed_result(repo, loop_idx):
    rr = RepoResult(repo=repo, loop_idx=loop_idx)
    rr.phases.append(PhaseResult(name="plan", rc=1, work_units=0))
    rr.phases.append(PhaseResult(name="review-plans", rc=0, work_units=0))
    return rr

def _unknown_work_result(repo, loop_idx):
    rr = RepoResult(repo=repo, loop_idx=loop_idx)
    rr.phases.append(PhaseResult(name="plan", rc=0, work_units=None))
    return rr
```

### Net Change

- `hephaestus/automation/loop_runner.py`: 14 LOC net (removed redundant reassignment, improved log message with loop/total/repo count)
- `tests/unit/automation/test_loop_runner_early_exit.py`: +137 LOC net (6 stubs → 6 real tests + 4 helper factories)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #614 — early-exit loop on zero-work pass | PR #669; 736 automation tests pass locally; all pre-commit hooks pass |

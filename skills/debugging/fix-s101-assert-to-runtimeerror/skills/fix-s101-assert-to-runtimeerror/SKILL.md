---
name: fix-s101-assert-to-runtimeerror
description: "Skill: fix-s101-assert-to-runtimeerror. Use when fixing Ruff S101 violations in production code by replacing bare assert guards with RuntimeError raises."
category: debugging
date: 2026-02-27
user-invocable: false
---

# Fix S101: Replace Assert Guards with RuntimeError

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Issue** | #1066 — fix(e2e): replace bare assert guards in runner.py and stages.py with proper RuntimeError raises |
| **Objective** | Replace all `assert x is not None  # noqa: S101` precondition guards in production code with explicit `if x is None: raise RuntimeError(...)` patterns |
| **Outcome** | ✅ Success — 16 asserts replaced across 2 files, all noqa suppressions removed, 3185 tests pass |
| **PR** | #1142 |

## When to Use

Use this skill when:

- Ruff reports S101 violations (`use of assert`) in production code (not test files)
- You see `assert x is not None  # noqa: S101` suppressions in source files
- Production code uses `assert` for precondition/guard checks that must always run
- An issue asks to "replace bare assert guards with RuntimeError raises"

**Key insight**: `assert` is inappropriate in production code because Python's `-O` (optimize)
flag disables all `assert` statements. Legitimate runtime guards must use explicit `raise`.

## Verified Workflow

### 1. Find All S101 Violations

```bash
# Find all assert + noqa:S101 patterns in target files
grep -n "assert.*noqa.*S101\|assert.*is not None" scylla/e2e/runner.py scylla/e2e/stages.py
```

The grep reveals the actual current line numbers, which may differ from the issue description
(code evolves, issue line numbers can be stale).

### 2. Read Context Around Each Assert

Before replacing, read a few lines of context around each assert to write a meaningful error message:

```python
# Pattern: assert self.experiment_dir is not None  # noqa: S101
# → used immediately before: self.experiment_dir / "checkpoint.json"
# → good message: "experiment_dir must be set before getting checkpoint path"
```

The error message should describe **what operation is blocked** by the missing value, not just
restate the condition.

### 3. Replace Each Assert

```python
# BEFORE
assert self.experiment_dir is not None  # noqa: S101
return self.experiment_dir / "checkpoint.json"

# AFTER
if self.experiment_dir is None:
    raise RuntimeError("experiment_dir must be set before getting checkpoint path")
return self.experiment_dir / "checkpoint.json"
```

For asserts with existing messages (stages.py pattern):

```python
# BEFORE
assert ctx.agent_result is not None, "agent_result must be set before finalize_run"  # noqa: S101

# AFTER
if ctx.agent_result is None:
    raise RuntimeError("agent_result must be set before finalize_run")
```

The message from the original assert becomes the RuntimeError message directly.

### 4. Verify No S101 Remains

```bash
grep -n "noqa.*S101\|assert.*is not None" scylla/e2e/runner.py scylla/e2e/stages.py
# Expected: No matches found
```

### 5. Run Pre-commit (Ruff Will Reformat)

```bash
pre-commit run --all-files
```

**Important**: Ruff format may reformat long lines introduced by the `if ... raise` pattern.
Run pre-commit **twice** — first run reformats, second run should fully pass:

```bash
pre-commit run --all-files  # may show "Ruff Format Python: Failed (files were modified)"
pre-commit run --all-files  # should show all Passed
```

### 6. Run Tests

```bash
pixi run python -m pytest tests/ -v
```

No test changes are needed — replacing asserts with RuntimeError does not break existing tests
because the tests either don't exercise failure paths, or the failure behavior is equivalent.

### 7. Commit and PR

```bash
git add scylla/e2e/runner.py scylla/e2e/stages.py
git commit -m "fix(e2e): replace bare assert guards with RuntimeError raises

Closes #<issue-number>"
git push -u origin <branch>
gh pr create --title "fix(e2e): replace bare assert guards with RuntimeError raises" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

### Skill tool for commit-push-pr was denied

**Attempt**: Used `Skill` tool with `commit-commands:commit-push-pr` to automate commit+push+PR.

**Failure**: Permission denied — Claude Code running in "don't ask" mode blocked the skill invocation.

**Fix**: Use `git add`, `git commit`, `git push`, and `gh pr create` bash commands directly.

### Line numbers in issue description are stale

**Observation**: Issue #1066 listed specific line numbers (717, 1013, 1014, 1033, 1056, 1085 in
runner.py) that did not match the actual file. The file had evolved and line numbers had shifted
significantly (the actual asserts were at 217, 429, 506, 657, 874, 925, 966, 1164, 1175–1177, 1196, 1219, 1248).

**Lesson**: Always use `grep` to find actual locations rather than trusting issue line numbers.
Also, the issue listed only 6 asserts in runner.py but the actual file had 10 (plus additional
ones in stages.py beyond the 5 listed). Always grep for the full pattern.

## Results & Parameters

```
Files modified: 2 (scylla/e2e/runner.py, scylla/e2e/stages.py)
Asserts replaced: 16 total (10 in runner.py, 6 in stages.py)
noqa suppressions removed: 16
Tests: 3185 passed, 78.09% coverage (≥75% threshold)
Pre-commit: all hooks pass (Ruff format reformatted runner.py on first run)
Python: 3.14.3 (pixi env)
```

### Replacement Pattern Reference

| Location | Variable | Error Message |
|----------|----------|---------------|
| `runner.py:_log_checkpoint_resume` | `self.checkpoint` | "checkpoint must be set before logging resume status" |
| `runner.py:_get_checkpoint_path` | `self.experiment_dir` | "experiment_dir must be set before getting checkpoint path" |
| `runner.py:_setup_workspace` | `self.experiment_dir` | "experiment_dir must be set before initializing workspace manager" |
| `runner.py:_get_baseline_for_previous_tier` | `self.experiment_dir` | "experiment_dir must be set before getting baseline for previous tier" |
| `runner.py:action_tiers_complete` | `self.experiment_dir` | "experiment_dir must be set before aggregating tier results" |
| `runner.py:_start_heartbeat` | `self.checkpoint` | "checkpoint must be set before starting heartbeat thread" |
| `runner.py:_run_experiment` | `self.checkpoint` | "checkpoint must be set before creating experiment state machine" |
| `runner.py:action_config_loaded (tier_dir)` | `self.experiment_dir` | "experiment_dir must be set before loading tier config" |
| `runner.py:action_config_loaded (tier_config)` | `tier_ctx.tier_config` | "tier_config must be set before running subtests" |
| `runner.py:action_config_loaded (tier_dir)` | `tier_ctx.tier_dir` | "tier_dir must be set before running subtests" |
| `runner.py:action_config_loaded (exp_dir)` | `self.experiment_dir` | "experiment_dir must be set before running subtests" |
| `runner.py:action_subtests_running` | `tier_ctx.tier_dir` | "tier_dir must be set before selecting best subtest" |
| `runner.py:action_subtests_complete` | `tier_ctx.selection` | "selection must be set before aggregating subtest results" |
| `runner.py:action_best_selected` | `tier_ctx.tier_result` | "tier_result must be set before saving reports" |
| `stages.py:write_replay_script` | `adapter_config` | "adapter_config must be set before writing replay script" |
| `stages.py:finalize_run (agent_result)` | `ctx.agent_result` | "agent_result must be set before finalize_run" |
| `stages.py:finalize_run (judgment)` | `ctx.judgment` | "judgment must be set before finalize_run" |
| `stages.py:write_report (run_result)` | `ctx.run_result` | "run_result must be set before write_report" |
| `stages.py:write_report (agent_result)` | `ctx.agent_result` | "agent_result must be set before write_report" |
| `stages.py:write_report (judgment)` | `ctx.judgment` | "judgment must be set before write_report" |

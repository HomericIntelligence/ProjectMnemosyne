---
name: fix-ruff-pre-commit-failures
description: 'Systematically fix ruff pre-commit CI failures (N806, E501, format)
  on a PR branch. Use when: pre-commit CI is failing with ruff N806/E501/format errors
  on a PR branch.'
category: ci-cd
date: 2026-03-13
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Goal** | Fix ruff pre-commit CI failures without changing logic |
| **Trigger** | Pre-commit CI red on a PR with ruff N806, E501, or format errors |
| **Output** | Clean commit pushed to PR branch; CI goes green |
| **Risk** | Low — purely cosmetic/style changes, no logic modified |

## When to Use

- Pre-commit CI is failing with `ruff check` or `ruff format` errors on a PR
- Errors are one or more of: N806 (uppercase variable in function), E501 (line too long), format (un-formatted code)
- The PR logic and tests are already correct; only style is blocking CI

## Verified Workflow

### Quick Reference

```bash
# 1. Checkout branch
git fetch origin <branch> && git checkout <branch>

# 2. Grep for offending variables/lines
grep -n "_STATE_ORDER\|_STATE_RANK\|UPPERCASE_VAR" scripts/manage_experiment.py

# 3. Apply fixes (see per-error steps below)

# 4. Verify locally
pixi run --environment lint pre-commit run --all-files

# 5. Commit and push
git add <files>
git commit -m "fix(<scope>): fix ruff N806/E501/format pre-commit failures"
git push origin <branch>
```

### Step 1 — Checkout the PR branch

```bash
git fetch origin <branch-name> && git checkout <branch-name>
git log --oneline -5   # confirm you're on the right branch
```

Check if branch has diverged from remote before starting:

```bash
git status   # look for "have diverged"
```

If diverged, pull first: `git pull --rebase origin <branch-name>`

### Step 2 — Fix N806: Uppercase variable inside function

Ruff N806 flags `UPPER_CASE` variables defined inside a function body (they look like module-level
constants but aren't).

**Find offenders:**

```bash
grep -n "^    [A-Z_]\{2,\} = " scripts/manage_experiment.py
```

**Fix pattern** — rename to lowercase snake_case:

```python
# BEFORE (triggers N806)
def _reconcile_checkpoint_with_disk(...):
    _STATE_ORDER = ["pending", "dir_structure_created", ...]
    _STATE_RANK = {s: i for i, s in enumerate(_STATE_ORDER)}
    ...
    current_rank = _STATE_RANK.get(current_state, 0)
    inferred_rank = _STATE_RANK.get(inferred_state, 0)

# AFTER (N806 resolved)
def _reconcile_checkpoint_with_disk(...):
    state_order = ["pending", "dir_structure_created", ...]
    state_rank = {s: i for i, s in enumerate(state_order)}
    ...
    current_rank = state_rank.get(current_state, 0)
    inferred_rank = state_rank.get(inferred_state, 0)
```

**Important**: Update ALL references — definition + every usage site.

### Step 3 — Fix E501: Line too long in docstrings

Ruff E501 flags lines exceeding the configured limit (commonly 100 chars). Docstrings are the
most common offender because they aren't auto-collapsed by ruff-format.

**Find offenders:**

```bash
grep -n ".\{101\}" tests/unit/e2e/test_manage_experiment_run.py | head -20
```

**Fix pattern** — wrap the docstring to multiple lines:

```python
# BEFORE (106 chars — triggers E501)
"""_checkpoint_has_retryable_runs returns True for judge-failed runs (worktree_cleaned+failed)."""

# AFTER (wrapped)
"""_checkpoint_has_retryable_runs returns True for judge-failed runs.

worktree_cleaned state with completed_runs status == "failed".
"""
```

### Step 4 — Fix ruff-format: Un-formatted code

Ruff-format auto-collapses multi-line expressions that fit within the line limit. The CI diff
shows exactly what collapsed form is expected.

**Common pattern** — multi-line `logger.info(...)` collapsed to one line:

```python
# BEFORE (un-formatted — triggers ruff-format)
if reconcile_count > 0:
    logger.info(
        f"--retry-errors: reconciled {reconcile_count} run state(s) with disk"
    )

# AFTER (ruff-format collapses since it fits in 100 chars)
if reconcile_count > 0:
    logger.info(f"--retry-errors: reconciled {reconcile_count} run state(s) with disk")
```

**How to identify**: Run `pixi run --environment lint pre-commit run ruff-format --all-files`
and read the diff output — it shows exactly what reformatting is needed.

### Step 5 — Verify locally before pushing

```bash
pixi run --environment lint pre-commit run --all-files 2>&1 | grep -E "^(Ruff|Failed|Passed)"
```

Expected output (all Passed):
```
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Ruff Complexity Check (C901).............................................Passed
```

Ignore failures in `ProjectMnemosyne/` subdirectory — those are pre-existing unrelated issues.

### Step 6 — Commit and push

```bash
git add <modified-files>
git commit -m "fix(<scope>): fix ruff N806/E501/format pre-commit failures"
git push origin <branch-name>
```

**If push rejected** (branch diverged):

```bash
git pull --rebase origin <branch-name>
git push origin <branch-name>
```

The push hook runs the full test suite (~135s) before pushing. Wait for it to complete.

### Step 7 — Verify CI

```bash
gh pr checks <PR-number> --repo <owner>/<repo>
```

All checks should transition from `pending` → `passing` within a few minutes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| First push | `git push origin <branch>` after committing fixes | Branch had diverged (remote had 1 commit not in local) — rejected with non-fast-forward error | Always check `git status` for divergence before pushing; use `git pull --rebase` to reconcile |
| Ignoring ProjectMnemosyne tier-label failures | Pre-commit output included many tier-label check failures | Those failures are pre-existing in `ProjectMnemosyne/` subdirectory, not caused by our changes | Filter pre-commit output with `grep -E "^(Ruff|Failed|Passed)"` to see only relevant checks |

## Results & Parameters

### Environment

```toml
# pixi.toml — lint environment used for pre-commit
[feature.lint.dependencies]
pre-commit = "*"
ruff = "*"
```

### Ruff Configuration (pyproject.toml)

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "N", "C901", ...]

[tool.ruff.format]
# ruff-format collapses expressions that fit within line-length
```

### Key Commands

```bash
# Run only ruff checks (fast)
pixi run --environment lint pre-commit run ruff --all-files
pixi run --environment lint pre-commit run ruff-format --all-files

# Run all pre-commit hooks
pixi run --environment lint pre-commit run --all-files

# Find N806 candidates
grep -n "^    [A-Z_][A-Z_]* = " scripts/*.py

# Find E501 candidates
grep -n ".\{101\}" tests/**/*.py | head -30
```

### Timing

- Local pre-commit run: ~10s (ruff only), ~30s (all hooks)
- Push hook (full test suite): ~135s
- CI checks: ~5 min for all checks to complete

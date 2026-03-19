---
name: fix-review-feedback-missing-assertion
description: "---"
category: testing
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
---
name: "Skill: Fix Review Feedback — Missing Mock Assertion"
description: "Pattern for fixing a misleading test that names/documents both setup and baseline assertions but only asserts one — add the missing mock capture and assertion"
category: testing
date: 2026-03-02
user-invocable: false
---
# Skill: Fix Review Feedback — Missing Mock Assertion in Patch Context Manager

## Overview

| Item | Details |
|------|---------|
| **Date** | 2026-03-02 |
| **Objective** | Fix a test that claims to verify two calls but only asserts one — the missing `as mock_X` capture and `assert_called_once()` |
| **Context** | PR #1313 review feedback for issue #1216 — `test_calls_setup_and_baseline` in `tests/unit/e2e/test_runner_experiment_actions.py` |
| **Outcome** | ✅ Single assertion added; all 18 tests pass; pre-commit clean (ruff auto-formatted long line) |
| **PR** | #1313 (review fix committed to branch `1216-auto-impl`) |

## When to Use This Skill

Use this pattern when:

1. **A test name/docstring claims to assert A and B**, but only `assert_called_once()` for B exists
2. **A `patch.object` context manager is missing `as mock_X`** — the mock handle is discarded
3. **Code review flags a test that would pass even if the patched method were deleted** from production code
4. **A test's name includes "and" (e.g. `test_calls_setup_and_baseline`)** but only one side is checked

**Trigger phrases:**
- "test would still pass if this line were deleted"
- "missing assertion for [method name]"
- "test name says 'and' but only asserts one side"
- "patch.object missing `as mock_X`"
- "add assert_called_once to verify setup is called"

## Verified Workflow

### Step 1: Read the failing test

Identify the `patch.object` line that is **missing `as mock_X`**:

```python
# BEFORE — mock handle discarded, no assertion possible
with (
    patch.object(runner, "_setup_workspace_and_scheduler", return_value=mock_scheduler),
    patch.object(runner, "_capture_experiment_baseline") as mock_baseline,
):
    runner._action_exp_dir_created(scheduler_ref)

mock_baseline.assert_called_once()
# BUG: _setup_workspace_and_scheduler is never asserted
```

### Step 2: Add `as mock_X` and the assertion

```python
# AFTER — both mocks captured, both asserted
with (
    patch.object(
        runner, "_setup_workspace_and_scheduler", return_value=mock_scheduler
    ) as mock_setup,
    patch.object(runner, "_capture_experiment_baseline") as mock_baseline,
):
    runner._action_exp_dir_created(scheduler_ref)

mock_setup.assert_called_once()
mock_baseline.assert_called_once()
```

Key changes:
- Add `as mock_setup` to the first `patch.object` call
- Add `mock_setup.assert_called_once()` before the existing baseline assertion

### Step 3: Run the target test file

```bash
pixi run pytest tests/unit/e2e/test_runner_experiment_actions.py -v
```

All tests in the file should pass. The fixed test now guards against deletion of the
production line `scheduler_ref[0] = self._setup_workspace_and_scheduler()`.

### Step 4: Run pre-commit

```bash
pre-commit run --all-files
```

**Note:** Ruff format may auto-break the long `patch.object(... return_value=mock_scheduler) as mock_setup`
line onto multiple lines. This is expected — run pre-commit a second time to confirm clean.

### Step 5: Commit

```bash
git add tests/unit/e2e/test_runner_experiment_actions.py
git commit -m "fix: Address review feedback for PR #NNNN

Add missing mock_setup.assert_called_once() assertion to
test_calls_setup_and_baseline so the test actually verifies that
_setup_workspace_and_scheduler is called.

Closes #NNNN

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## Failed Attempts

None — the fix was straightforward: a single `as mock_X` capture + one `assert_called_once()` line.
The only wrinkle was ruff reformatting the long line, which required running pre-commit twice.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| File changed | `tests/unit/e2e/test_runner_experiment_actions.py` |
| Lines changed | +4 insertions, -1 deletion |
| Tests in file | 18 (all pass) |
| Pre-commit hooks | All pass (ruff-format auto-applied on first run) |
| Commit message prefix | `fix: Address review feedback for PR #NNNN` |

## Root Cause Pattern

When a `unittest.mock.patch` context manager uses `return_value=X` but omits `as mock_name`,
the mock object is created but the handle is discarded — making it impossible to assert on the call.
This is a silent bug: the test appears to test the method but provides zero coverage of "was it called?".

Detection heuristic: grep for test names containing "and" where only one `assert_called_once` exists:

```bash
grep -A 20 "def test_calls_.*_and_" tests/ -r | grep "assert_called_once"
# If count of "and" parts > count of assert_called_once lines → missing assertion
```

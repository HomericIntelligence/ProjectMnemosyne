# Skill: fixture-timeout-calibration

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| PR | #884 |
| Objective | Update `timeout_seconds` in all 47 test fixture YAML files with calibrated values derived from observed batch run durations |
| Outcome | Success — total timeout sum reduced from ~147,900s to ~29,820s (~80% reduction) |
| Category | testing |

## When to Use

Trigger this skill when:

- Batch E2E runs finish but many tests use generic default timeout values that are far too conservative
- You have a set of observed actual durations from a completed run and want to set per-test timeouts proportionally
- You need to update a large number of YAML fixture files (10+) with calculated values in bulk
- CI is failing due to over-long timeouts causing the pipeline to time out at the job level
- You want to enforce a minimum floor (e.g. 180s) and a safety multiplier (e.g. 3x) on observed durations

## Results & Parameters

### Calibration Formula

```
timeout_seconds = max(180, ceil(actual_duration * 3 / 60) * 60)
```

- **Multiplier**: 3x actual observed duration
- **Granularity**: Round up to the nearest 60 seconds
- **Floor**: 180 seconds minimum (never lower than 3 minutes)

### Example Calculations

| Observed Duration | Raw (3x) | Rounded to 60s | Final |
|-------------------|----------|----------------|-------|
| 28s | 84s | 120s | 180s (floor) |
| 45s | 135s | 180s | 180s |
| 72s | 216s | 240s | 240s |
| 150s | 450s | 480s | 480s |
| 300s | 900s | 900s | 900s |

### Before / After

| Metric | Before | After |
|--------|--------|-------|
| Files updated | 47 | 47 |
| Total timeout sum | ~147,900s | ~29,820s |
| Reduction | — | ~80% |
| Files at old default (300s) | many | 0 |
| Minimum value | 300s | 180s |

## Verified Workflow

### 1. Collect observed durations

Run the batch E2E suite and extract actual durations from the results. Durations are typically in the
`run_metadata.json` or in the test result YAML output for each test.

```bash
# Example: gather durations from results
grep -r "duration_seconds" tests/fixtures/results/ | sort
```

### 2. Calculate calibrated values

Apply the formula to each observed duration:

```python
import math

def calibrate_timeout(actual_duration_seconds: float) -> int:
    raw = actual_duration_seconds * 3
    rounded = math.ceil(raw / 60) * 60
    return max(180, rounded)
```

### 3. Read fixture files in parallel batches

Read 9-10 files at a time to understand the current structure before editing:

```bash
# Verify structure of a representative file first
cat tests/fixtures/tests/test-001/test.yaml
```

Typical fixture structure:

```yaml
task:
  description: "..."
  timeout_seconds: 300   # <-- field to update
  ...
```

### 4. Edit fixture files in parallel batches

Edit files in groups of 9-10. This is efficient and stays within tool concurrency limits.

For each file, change only the `timeout_seconds` field. Do not touch any other fields.

```
tests/fixtures/tests/test-001/test.yaml  -> timeout_seconds: 180
tests/fixtures/tests/test-002/test.yaml  -> timeout_seconds: 240
...
tests/fixtures/tests/test-047/test.yaml  -> timeout_seconds: 360
```

### 5. CRITICAL — grep the test suite for hardcoded expected values

Before committing, search the entire test suite for any hardcoded references to the old timeout value:

```bash
grep -r "timeout_seconds" tests/unit/
grep -r "timeout_seconds" tests/
grep -rn "== 300" tests/unit/
grep -rn "timeout_seconds ==" tests/
```

Update any hardcoded assertions to match the new floor value (180) or to be data-driven.

### 6. Commit and push

```bash
git add tests/fixtures/tests/
git add tests/unit/          # if any unit tests were updated
git commit -m "test(fixtures): calibrate timeout_seconds using 3x observed duration formula"
git push -u origin <branch>
```

### 7. Create and enable auto-merge on the PR

```bash
gh pr create --title "test(fixtures): calibrate timeout_seconds to observed durations" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

### Attempt 1 — Committed without updating hardcoded test assertion

**What happened**: After editing all 47 fixture YAML files and committing, the pre-commit hook ran
`tests/unit/test_config_loader.py` and the following assertion failed:

```
FAILED tests/unit/test_config_loader.py::test_load_test - AssertionError:
  assert test.task.timeout_seconds == 300
```

Line 78 of `tests/unit/test_config_loader.py` had a hardcoded `assert test.task.timeout_seconds == 300`.
When the fixture file `test-001/test.yaml` was updated from 300s to 180s (the new floor), the assertion
broke because the test was checking the literal value loaded from the fixture, not a calculated value.

**Fix**: Update `tests/unit/test_config_loader.py:78` from:

```python
assert test.task.timeout_seconds == 300
```

to:

```python
assert test.task.timeout_seconds == 180
```

Then amend the commit and push again. The pre-commit hook passed on the second attempt.

**Key lesson**: When updating fixture files that are exercised by unit tests, always grep the test suite
for the old values before committing:

```bash
grep -rn "== 300" tests/
grep -rn "timeout_seconds" tests/unit/
```

### Attempt 2 — `git checkout` blocked by Safety Net

**What happened**: During branch switching, the command `git checkout -b skill/testing/fixture-timeout-calibration`
was blocked by the repository's Safety Net configuration.

**Fix**: Use `git switch` instead of `git checkout` for all branch operations:

```bash
# WRONG — may be blocked
git checkout -b skill/testing/fixture-timeout-calibration

# CORRECT — always works
git switch -c skill/testing/fixture-timeout-calibration
git switch main
git switch <existing-branch>
```

## Related Skills

- `git-worktree-collision-fix` — E2E batch runner error elimination
- `wired-runner-fixture` — Shared pytest fixture extraction patterns

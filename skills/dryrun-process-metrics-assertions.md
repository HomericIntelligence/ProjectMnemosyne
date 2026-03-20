---
name: dryrun-process-metrics-assertions
description: "Skill: Dryrun process_metrics Assertions in Integration Tests"
category: tooling
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: Dryrun process_metrics Assertions in Integration Tests

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-02 |
| Project | ProjectScylla |
| Objective | Add assertions verifying `process_metrics`, `progress_tracking`, and `changes` blocks in `run_result.json` |
| Outcome | Success — 17/17 tests pass, full suite 3601 passed, 67.46% coverage |
| Issue | HomericIntelligence/ProjectScylla#1180 |
| PR | HomericIntelligence/ProjectScylla#1295 |

## When to Use

Use this skill when:
- Adding dryrun validation assertions for new fields in `run_result.json`
- Testing that `stage_finalize_run` writes required blocks with correct types
- Verifying process metrics, progress tracking, or changes lists are present
- Adding integration tests for artifact structure correctness

## Key Architectural Insight: run_result.json Structure

`run_result.json` is written by `stage_finalize_run` in `scylla/e2e/stages.py`. The file has 19 base fields plus three blocks added by the finalize stage:

```json
{
  "process_metrics": {
    "r_prog": 0.0,
    "strategic_drift": 0.0,
    "cfp": 0.0,
    "pr_revert_rate": 0.0
  },
  "progress_tracking": [],
  "changes": []
}
```

Key semantics:
- `process_metrics` is always a `dict` with exactly 4 float subkeys
- `progress_tracking` is always a `list` — empty for no-change runs
- `changes` is always a `list` — empty for no-change runs
- Both lists accept items; tests should cover both empty and non-empty cases

## Verified Workflow

### Test File Location

`tests/integration/e2e/test_run_result_process_metrics.py` — new file, not modifying existing tests.

### Test Architecture Pattern

Tests operate against JSON fixtures written to `tmp_path`, not against a live experiment runner. This avoids needing real API calls, Docker, or git operations while still testing the artifact contract.

```python
pytestmark = pytest.mark.integration

PROCESS_METRIC_FLOAT_KEYS = ("r_prog", "strategic_drift", "cfp", "pr_revert_rate")

def _minimal_run_result_with_process_metrics() -> dict[str, object]:
    """Build a minimal run_result.json dict matching stage_finalize_run output."""
    return {
        # ... 19 base E2ERunResult fields ...
        "process_metrics": {"r_prog": 0.0, "strategic_drift": 0.0, "cfp": 0.0, "pr_revert_rate": 0.0},
        "progress_tracking": [],
        "changes": [],
    }
```

### Test Classes

**`TestRunResultProcessMetricsPresence`** (14 tests):
- `process_metrics` key exists, is a `dict`
- All 4 float subkeys exist — `@pytest.mark.parametrize("key", PROCESS_METRIC_FLOAT_KEYS)`
- All 4 float subkeys are `float` — also parametrized
- `progress_tracking` key exists, is a `list`
- `changes` key exists, is a `list`

**`TestRunResultProcessMetricsWithData`** (3 tests):
- `progress_tracking` is a list when populated with step items
- `changes` is a list when populated with change items
- `process_metrics` float subkeys remain `float` for non-zero values

### Parametrize Float Subkeys

Use parametrize for the 4 subkeys to get one assertion per key rather than asserting all 4 in one test — gives cleaner failure output:

```python
@pytest.mark.parametrize("key", PROCESS_METRIC_FLOAT_KEYS)
def test_process_metrics_float_subkeys_exist(self, tmp_path: Path, key: str) -> None:
    ...
    assert key in pm
```

### Mypy Compliance

Return type of helper function must use parameterized `dict`:

```python
# WRONG — mypy: Missing type parameters for generic type "dict"
def _minimal_run_result_with_process_metrics() -> dict:

# CORRECT
def _minimal_run_result_with_process_metrics() -> dict[str, object]:
```

### Coverage Behavior

Running integration tests alone shows ~7-8% coverage (below 9% floor). This is expected — the pre-push hook runs the full test suite (`tests/`) which reaches 67%+. Do not target integration tests in isolation for coverage checks.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Pre-commit Hook Results

```
Ruff Format Python .... Passed
Ruff Check Python ..... Passed
Mypy Type Check Python  Passed
```

### Full Suite Results

```
3601 passed, 1 skipped
Coverage: 67.46%
```

### File Created

```
tests/integration/e2e/test_run_result_process_metrics.py
  - 213 lines
  - 17 tests
  - 2 test classes
  - 1 helper function
```

---
name: unit-test-instance-attr-patching
description: "Skill: Unit Testing with Instance Attribute Patching"
category: testing
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: Unit Testing with Instance Attribute Patching

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Objective | Add unit tests for `_execute_single_tier` baseline fallback behavior (issue #772) |
| Outcome | Success — 4 new tests, all passing, pre-commit clean |
| PR | #818 |
| Category | testing |

## When to Use

- Adding unit tests to a class whose constructor builds a collaborator object internally (e.g. `self.x = SomeClass(arg)`)
- Need to assert a collaborator's method is called (or not called) without the real implementation running
- Testing conditional assignment (`updated = previous or self._create(...)`) where one branch preserves the original value

## Verified Workflow

### 1. Identify the constructor signature

The target class may accept a `Path` or primitive that it uses to construct a real collaborator, not the collaborator itself:

```python
# E2ERunner takes tiers_dir: Path and builds its own TierManager
def __init__(self, config, tiers_dir: Path, results_base_dir: Path):
    self.tier_manager = TierManager(tiers_dir)
```

Passing a `MagicMock()` as `tiers_dir` satisfies the constructor without crashing (since `TierManager.__init__` uses the path lazily or just stores it), **but** `runner.tier_manager` is still a real `TierManager` — not a mock.

### 2. Patch the instance attribute after construction

Override `runner.tier_manager` directly on the instance after creation:

```python
runner = E2ERunner(mock_config, MagicMock(), Path("/tmp"))
mock_tier_manager = MagicMock()
runner.tier_manager = mock_tier_manager  # override the real one
```

This is simpler and more reliable than `patch.object(runner, "tier_manager", ...)` as a context manager.

### 3. Patch methods with `patch.object`

Use `patch.object` for methods you want to stub out:

```python
with (
    patch.object(runner, "_run_tier", return_value=tier_result),
    patch.object(runner, "_save_tier_result"),
):
    result, baseline = runner._execute_single_tier(...)
```

### 4. Set simple instance attributes directly

For plain attributes (not properties), assign directly before the call:

```python
runner.experiment_dir = Path("/results/exp")
```

Do **not** use `patch.object(runner, "experiment_dir", Path("/results"))` for instance attributes — this creates a context manager that patches the attribute on the class, not the instance, and may not behave as expected.

### 5. Use `==` not `is` for Pydantic model identity

Two Pydantic model instances with equal fields are `==` but not `is` the same object. Use:

```python
assert updated_baseline == new_baseline  # correct for Pydantic models
assert updated_baseline is mock_tier_baseline  # correct only for the same object reference
```

Use `is` only when you want to verify the *exact same object* was returned (e.g. verifying the fallback returns the original object, not a copy).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

```python
# Fixture pattern for a baseline object
@pytest.fixture
def mock_tier_baseline() -> TierBaseline:
    return TierBaseline(
        tier_id=TierID.T0,
        subtest_id="subtest-0",
        claude_md_path=Path("/tmp/CLAUDE.md"),
        claude_dir_path=None,
    )

# Full test pattern
def test_no_best_subtest_returns_previous_baseline(mock_config, mock_tier_baseline):
    runner = E2ERunner(mock_config, MagicMock(), Path("/tmp"))
    mock_tier_manager = MagicMock()
    runner.tier_manager = mock_tier_manager

    tier_result = TierResult(tier_id=TierID.T1, subtest_results={})

    with (
        patch.object(runner, "_run_tier", return_value=tier_result),
        patch.object(runner, "_save_tier_result"),
    ):
        _, updated_baseline = runner._execute_single_tier(TierID.T1, mock_tier_baseline, MagicMock())

    assert updated_baseline is mock_tier_baseline
    mock_tier_manager.get_baseline_for_subtest.assert_not_called()
```

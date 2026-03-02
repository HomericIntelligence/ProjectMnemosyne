# Skill: Extract Closures into Private Methods

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-02 |
| Project | ProjectScylla |
| Objective | Extract inline action closures from `_build_experiment_actions()` into private `_action_exp_*` methods on `E2ERunner`, enabling direct unit testing of RuntimeError guards |
| Outcome | Success — 18 new direct tests, `_build_experiment_actions()` reduced from ~60 to ~15 lines, full suite 3528 passed |
| Issue | HomericIntelligence/ProjectScylla#1216 |
| PR | HomericIntelligence/ProjectScylla#1313 |

## When to Use

Use this skill when:
- A method defines multiple closures over 3+ variables from the enclosing scope
- Closures contain `if x is None: raise RuntimeError(...)` guards that cannot be tested in isolation
- The method body is 40+ lines due to inline closure definitions
- Tests rely on `patch.object(StateMachine, 'advance_to_completion')` to indirectly exercise closures
- A closure uses `nonlocal` to rebind a captured variable (a sign the closure should be a method)

**Companion skill**: See `runtime-error-guard-tests` for writing the direct tests after extraction.

## Key Decisions

### 1. Method-per-action, `_action_<scope>_<state>` naming

Each closure becomes exactly one private method. Naming convention:
- `_action_exp_<state>` for experiment-level actions (e.g., `_action_exp_tiers_complete`)
- `_action_tier_<state>` for tier-level actions (mirrors `TierActionBuilder` convention)

### 2. Mutable-box for `nonlocal` variables

When a closure uses `nonlocal x` to rebind a captured variable, the extracted method cannot use
`nonlocal` (it has no enclosing scope). Use a **single-element list as a mutable box**:

```python
# Before (closure with nonlocal)
def action_dir_created() -> None:
    nonlocal scheduler
    scheduler = self._setup_workspace_and_scheduler()

# After (extracted method)
def _action_exp_dir_created(self, scheduler_ref: list[ParallelismScheduler | None]) -> None:
    scheduler_ref[0] = self._setup_workspace_and_scheduler()

# Builder: initialise box before the return dict
scheduler_ref: list[ParallelismScheduler | None] = [scheduler]
# TIERS_RUNNING lambda reads scheduler_ref[0] to get the updated value
```

**Why not return the value?** The caller is a `Callable[[], None]` (zero-arg). Returning would require
wrapper lambdas that capture and reassign — more complex. The mutable box is the standard Python idiom
and matches how `tier_results` (a dict) is already mutated in-place.

### 3. Thin builder: only `scheduler_ref` init + return dict

After extraction, `_build_experiment_actions()` contains:
1. One line: `scheduler_ref: list[...] = [scheduler]`
2. A `return {...}` dict with 6 entries — direct method refs or lambdas that forward captured args

```python
return {
    ExperimentState.INITIALIZING: self._action_exp_initializing,
    ExperimentState.DIR_CREATED: lambda: self._action_exp_dir_created(scheduler_ref),
    ExperimentState.REPO_CLONED: lambda: self._action_exp_repo_cloned(tier_groups),
    ExperimentState.TIERS_RUNNING: lambda: self._action_exp_tiers_running(
        tier_groups, scheduler_ref[0], tier_results
    ),
    ExperimentState.TIERS_COMPLETE: lambda: self._action_exp_tiers_complete(
        tier_results, start_time
    ),
    ExperimentState.REPORTS_GENERATED: self._action_exp_reports_generated,
}
```

**No-arg actions** (no captured state): use `self._method` directly (no lambda needed).
**Actions with captured args**: wrap with a lambda that forwards them.

### 4. TDD: write tests alongside extraction, not after

Write the test file for extracted methods first (or at least in parallel). This validates each
extraction immediately and catches parameter-passing bugs before they accumulate.

## Verified Workflow

### Step 1 — Identify closures to extract

```bash
grep -n "def action_" scylla/e2e/runner.py
```

Collect the list. Note which closures use `nonlocal` (those need the mutable-box treatment).

### Step 2 — Extract one at a time, simplest first

Order: no-captured-vars → single-captured-var → multi-captured-var → nonlocal.

After each extraction:
```bash
pre-commit run --files scylla/e2e/runner.py
```

If ruff D401 fires on the docstring, reword to imperative mood:
- BAD:  `"""INITIALIZING -> DIR_CREATED: No-op; setup done in ..."""`
- GOOD: `"""Handle INITIALIZING -> DIR_CREATED transition.\n\nNo-op: ..."""`

### Step 3 — Write direct unit tests

Create `tests/unit/e2e/test_runner_experiment_actions.py`. Key fixture:

```python
@pytest.fixture
def runner(tmp_path: Path) -> E2ERunner:
    config = ExperimentConfig(
        experiment_id="test",
        task_repo="https://github.com/test/repo",
        task_commit="abc123",
        task_prompt_file=tmp_path / "prompt.md",
        language="python",
        tiers_to_run=[TierID.T0],
    )
    return E2ERunner(config, tmp_path / "tiers", tmp_path)
```

**ExperimentConfig requires `language` field** — omitting it causes a Pydantic validation error.

### Step 4 — Test patterns for each action type

| Action type | Test pattern |
|-------------|-------------|
| No-op | Call directly; assert nothing raised |
| Mutable-box update | Assert `ref[0]` is the mock return value after call |
| Side-effect sequence | Use `call_order` list with `side_effect` to verify order |
| RuntimeError guard | `runner.experiment_dir = None; pytest.raises(RuntimeError, match="...")` |
| Logging | `patch("scylla.e2e.runner.logger"); assert mock_logger.info.call_args[0][0]` contains substring |
| Builder wiring | Call `DIR_CREATED` action then `TIERS_RUNNING` action inside same patch context; assert `_execute_tier_groups` got the scheduler set by `DIR_CREATED` |

### Step 5 — Assert mock inside `with` block

A common mistake: calling `mock.assert_called_once_with(...)` **outside** the `with patch.object(...)` block. Outside the block, the attribute has been restored to the original function object (which has no `.assert_*` methods).

```python
# WRONG — mock is gone outside the with block
with patch.object(runner, "_execute_tier_groups", return_value={}) as mock_exec:
    runner._action_exp_tiers_running(...)
mock_exec.assert_called_once_with(...)  # AttributeError: 'function' has no attr

# CORRECT — assert inside the with block
with patch.object(runner, "_execute_tier_groups", return_value={}) as mock_exec:
    runner._action_exp_tiers_running(...)
    mock_exec.assert_called_once_with(...)  # OK
```

This applies whenever `patch.object` targets an instance method that was not originally a Mock.

### Step 6 — Run full suite

```bash
pixi run python -m pytest tests/unit/ -v
```

Confirm no regressions in existing `test_runner.py` tests (especially `TestResumeTierConfigPreload`).

## Results & Parameters

### Files modified

| File | Change |
|------|--------|
| `scylla/e2e/runner.py` | +74 lines (6 private methods + scheduler_ref in builder) |
| `scylla/e2e/runner.py` | -46 lines (removed closure definitions) |
| `tests/unit/e2e/test_runner_experiment_actions.py` | New file, 18 tests |

### Metrics

| Metric | Before | After |
|--------|--------|-------|
| `_build_experiment_actions()` body lines | ~60 | ~15 |
| Directly testable actions | 0 | 6 |
| Tests for action guards | 0 | 1 (RuntimeError on tiers_complete) |
| New test file | — | 18 tests |
| Full suite pass rate | 3510 | 3528 |

### Ruff rules triggered

| Rule | Description | Fix |
|------|-------------|-----|
| D401 | Docstring not in imperative mood | Reword first line: `"""Handle X -> Y transition.\n\nNo-op: ..."""` |
| E501 | Line too long in test docstrings | Shorten to ≤100 chars |

## Failed Attempts

### Attempt: assert mock outside `with patch.object` block

**What happened**: Final builder wiring test called `runner._execute_tier_groups.assert_called_once_with(...)` after the `with` block exited. `_execute_tier_groups` is a real method on the class — once the patch context exits, the attribute reverts to the original function, which has no `.assert_*` attributes.

**Error**: `AttributeError: 'function' object has no attribute 'assert_called_once_with'`

**Fix**: Moved the assertion inside the `with patch.object(...)` block.

### Attempt: bind `mock_exec` after context exit

Same root cause as above. The fix is simple: capture the mock with `as mock_exec` and assert inside the `with` block.

# Skill: Test Internal Methods with Mocks in E2ERunner

| Field      | Value                                                           |
|------------|-----------------------------------------------------------------|
| Date       | 2026-02-20                                                      |
| Objective  | Add unit tests for an internal method that delegates to injected collaborators |
| Outcome    | Success — 3 tests added, all 2208 unit tests pass (73.54% coverage) |
| Issue      | #773 (follow-up from #712)                                      |
| PR         | #819                                                            |

## When to Use

Use this skill when:

- Adding tests for an `E2ERunner` internal method that calls `self.tier_manager` or uses `self.experiment_dir`
- The method has conditional logic gated on `self.config.tiers_to_run`
- You need to isolate the method under test from filesystem and network access

Trigger phrases:

- "no unit tests for `_<method>`"
- "add coverage for internal runner method"
- "test method that delegates to tier_manager"

## Verified Workflow

### 1. Understand the method signature and logic

Read `scylla/e2e/runner.py` around the target method. Note:

- Which `self.*` attributes it reads (`self.config`, `self.experiment_dir`, `self.tier_manager`)
- What it returns and under what conditions it returns `None`

### 2. Understand model constructors

Check `scylla/e2e/models.py` for required fields:

- `TierBaseline` requires `tier_id`, `subtest_id`, `claude_md_path`, `claude_dir_path`
- `TierResult` requires `tier_id`, `subtest_results`; `best_subtest` defaults to `None`
- `SubTestResult` requires `subtest_id`, `tier_id`, `runs` (can be `[]`); `pass_rate` and `mean_cost` are optional

### 3. Use the correct E2ERunner constructor

```python
# E2ERunner.__init__ takes: config, tiers_dir (Path), results_base_dir (Path)
runner = E2ERunner(config, Path("/tmp"), Path("/tmp"))
# experiment_dir starts as None — set it explicitly for path-building tests:
runner.experiment_dir = Path("/tmp/exp")
# Replace the real TierManager with a mock:
runner.tier_manager = mock_tier_manager
```

**Critical**: `E2ERunner(config, tiers_dir, results_base_dir)` — the 2nd arg is `tiers_dir: Path`, NOT a `TierManager`. Passing a `MagicMock` as `tiers_dir` is silently accepted (TierManager stores it without validation) but `runner.tier_manager` is then a real `TierManager` with a mock path. Always reassign `runner.tier_manager` after construction.

### 4. Control `tiers_to_run` explicitly in fixtures

```python
# Fixture WITHOUT T5 (for "early-return" tests)
ExperimentConfig(..., tiers_to_run=[TierID.T0, TierID.T1])

# Fixture WITH T5 (for "normal path" tests)
ExperimentConfig(..., tiers_to_run=[TierID.T0, TierID.T1, TierID.T5])
```

**Warning**: `tiers_to_run` defaults to `list(TierID)` (all tiers, including T5). A fixture that omits `tiers_to_run` will always include T5, breaking "T5 absent" tests silently.

### 5. Build helper factory for TierResult with CoP

```python
def _make_tier_result(
    tier_id: TierID,
    subtest_id: str,
    mean_cost: float,
    pass_rate: float,
) -> TierResult:
    subtest = SubTestResult(
        subtest_id=subtest_id,
        tier_id=tier_id,
        runs=[],
        pass_rate=pass_rate,
        mean_cost=mean_cost,
    )
    return TierResult(
        tier_id=tier_id,
        subtest_results={subtest_id: subtest},
        best_subtest=subtest_id,
    )
```

`cost_of_pass` is a property: `mean_cost / pass_rate`. Pass `pass_rate > 0` to get a finite CoP.

### 6. Three standard test cases for filtering+selection methods

| Test | Config | Input | Expected |
|------|--------|-------|----------|
| Gate condition false | T5 absent | Any tier_results | `None`, no calls to `tier_manager` |
| Selection logic | T5 present | Multiple tiers with different CoP | Baseline from lowest-CoP tier |
| Missing winner | T5 present | Tier with `best_subtest=None` | `None`, no calls to `tier_manager` |

## Failed Attempts

### Attempt 1: Passing MagicMock as tier_manager argument

```python
# WRONG — mock_tier_manager ends up as tiers_dir, not runner.tier_manager
runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
```

This silently creates `runner.tier_manager = TierManager(mock_tier_manager)`. Assertions on `mock_tier_manager.get_baseline_for_subtest` always fail because the real `TierManager` (not the mock) is called.

**Fix**: Create runner with `Path("/tmp")` as `tiers_dir`, then reassign:

```python
runner = E2ERunner(mock_config, Path("/tmp"), Path("/tmp"))
runner.tier_manager = mock_tier_manager
```

### Attempt 2: Omitting tiers_to_run in the "no T5" fixture

The default `tiers_to_run=list(TierID)` includes T5. The "early return" test would never trigger.

**Fix**: Always pass `tiers_to_run=[TierID.T0, TierID.T1]` explicitly for fixtures intended to exclude T5.

### Attempt 3: Not setting experiment_dir

`_select_best_baseline_from_group` builds `self.experiment_dir / tier_id.value / subtest_id`. If `experiment_dir` is `None` (the default), this raises `TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'`.

**Fix**: `runner.experiment_dir = Path("/tmp/exp")` before calling the method.

## Results & Parameters

- **File modified**: `tests/unit/e2e/test_runner.py`
- **Tests added**: 3 (`TestSelectBestBaselineFromGroup`)
- **Helper added**: `_make_tier_result` module-level function
- **Fixture added**: `mock_config_with_t5`
- **Fixture updated**: `mock_config` (added explicit `tiers_to_run`)
- **All tests**: 2208 passed, 73.54% coverage
- **Pre-commit**: ruff-format auto-reformatted import block (multi-line); re-stage required

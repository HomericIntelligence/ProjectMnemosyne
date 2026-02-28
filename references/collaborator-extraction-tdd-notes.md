# collaborator-extraction-tdd: Raw Session Notes

## Session Context

- **Date**: 2026-02-28
- **Project**: ProjectScylla
- **Issue**: #1146 — [Refactor] runner.py still exceeds 800-line target (1509 lines)
- **PR**: #1230
- **Branch**: `1146-auto-impl`

## Objective

Reduce `scylla/e2e/runner.py` from 1527 lines to under 1000 lines by extracting three method groups:
1. `_build_tier_actions()` + 6 action closures → `TierActionBuilder`
2. `_execute_tier_groups()`, `_execute_parallel_tier_group()`, `_select_best_baseline_from_group()`, `_execute_single_tier()`, `_create_baseline_from_tier_result()` → `ParallelTierRunner`
3. `_save_tier_result()`, `_save_final_results()`, `_generate_report()`, `_find_frontier()`, `_aggregate_token_stats()`, `_aggregate_results()` → `ExperimentResultWriter`

## Files Created

- `scylla/e2e/tier_action_builder.py` (~200 lines)
- `scylla/e2e/parallel_tier_runner.py` (~230 lines)
- `scylla/e2e/experiment_result_writer.py` (~220 lines)
- `tests/unit/e2e/test_tier_action_builder.py` (27 tests)
- `tests/unit/e2e/test_parallel_tier_runner.py` (19 tests)
- `tests/unit/e2e/test_experiment_result_writer.py` (23 tests)

## Files Modified

- `scylla/e2e/runner.py` (1527 → 1105 lines)
- `tests/unit/e2e/test_runner.py` (updated patch targets, rewrote 2 test classes)
- `tests/unit/e2e/test_runner_state_machine.py` (removed unused variable, updated one test)

## Errors Encountered and Solutions

### 1. Pydantic ValidationError for ExperimentConfig
**Error**: `pydantic_core._pydantic_core.ValidationError` — missing required fields
**Root cause**: `ExperimentConfig` requires `experiment_id`, `task_repo`, `task_commit`, `task_prompt_file`, `language`
**Fix**: Added all 5 required fields to every test instantiation

### 2. `wait_for_rate_limit()` Wrong Signature
**Error**: Called `wait_for_rate_limit(tier_id)` in `action_pending` closure
**Root cause**: Real signature is `wait_for_rate_limit(retry_after, checkpoint, checkpoint_path)`
**Fix**: Implemented full rate limit check pattern using `check_api_rate_limit_status()` first, then conditionally calling `wait_for_rate_limit` with correct args

### 3. MagicMock Not Accepted by Pydantic TierResult
**Error**: `TierResult.subtest_results` validation rejects `MagicMock` values
**Root cause**: Pydantic validates all dict values against `SubTestResult` schema
**Fix**: Created `_make_subtest_result()` helper returning real `SubTestResult` instances

### 4. Circular Import
**Error**: `ImportError: cannot import name 'is_shutdown_requested' from partially initialized module`
**Root cause**: `parallel_tier_runner.py` has top-level `from scylla.e2e.runner import is_shutdown_requested`; `runner.py` imports `ParallelTierRunner` from `parallel_tier_runner.py`
**Fix**: Used lazy local import inside `execute_tier_groups()` body (same pattern as `parallel_executor.py`)

### 5. `cost_of_pass` is a Property, Not a Field
**Error**: `Unexpected keyword argument "cost_of_pass" for "TierResult"`
**Root cause**: `cost_of_pass` is computed via `@property` from `best_subtest.mean_cost / best_subtest.pass_rate`
**Fix**: Removed `cost_of_pass=cost_of_pass` from `TierResult()` constructor calls; designed `_make_subtest_result()` so that `mean_cost / pass_rate` computes the desired value

### 6. Patch Target Stale After Extraction
**Error**: 3 tests in `TestResumeTierConfigPreload` that patched `scylla.e2e.runner.run_tier_subtests_parallel` stopped working
**Root cause**: After extraction, `run_tier_subtests_parallel` is imported in `tier_action_builder.py`, not `runner.py`
**Fix**: Changed patch target to `scylla.e2e.tier_action_builder.run_tier_subtests_parallel`

### 7. `_execute_single_tier` Removed
**Error**: `test_run_tier_calls_advance_to_completion` called `runner._execute_single_tier(TierID.T0, None, None)`
**Root cause**: `_execute_single_tier` is now internal to `ParallelTierRunner`
**Fix**: Changed test to call `runner._run_tier(TierID.T0, None, None)` directly (equivalent public API)

### 8. Mypy Type Errors in Test Files
**Errors (9 total)**:
- `Item "None" of "TierResult | None" has no attribute "tier_id"/"token_stats"` — accessing `tier_ctx.tier_result` attributes without None guard
- `Unexpected keyword argument "cost_of_pass"` — property passed as constructor arg
- `run_tier_fn` type mismatch — `MagicMock | None` hint can't accept plain `Callable`
- `F841 Local variable assigned to but never used` — `mock_tier_result` created but not used

**Fixes**:
- Added `assert tier_ctx.tier_result is not None` before attribute access (2 locations)
- Removed `cost_of_pass=cost_of_pass` from `TierResult()` constructor
- Changed type hint: `run_tier_fn: Callable[..., TierResult] | MagicMock | None`
- Added `from collections.abc import Callable` import
- Removed the unused `mock_tier_result` variable entirely

## Line Count Analysis

Why did we miss the 1000-line target?

The implementation plan projected:
- PR-A: 1527 → ~1383 (-144 lines)
- PR-B: 1383 → ~1220 (-163 lines)
- PR-C: 1220 → ~1000 (-220 lines)

Actual result: 1105 lines. The plan underestimated:
1. Delegation stubs add back lines (~5-8 lines per extracted method instead of 2-3)
2. `_result_writer()` helper method adding 8 lines
3. Import lines for the 3 new modules

The 1105-line result is still a 28% reduction and satisfies the "realistic near-term target" from the issue.

## Key Design Decisions

### Explicit Dependency Injection vs. Full Host Reference
Each collaborator receives only the state it needs, never `self` (the runner). This:
- Avoids circular coupling (collaborator → runner → collaborator)
- Makes collaborator unit tests simpler (only mock what it needs)
- Makes the extracted class independently testable

### Lazy Import for Circular Dependency
`is_shutdown_requested` is a module-level function in `runner.py`. Since `runner.py` imports `ParallelTierRunner`, importing from `runner` at the top of `parallel_tier_runner.py` creates a circular import. Lazy import inside the method body breaks the cycle cleanly.

### `_result_writer()` Helper Pattern
Instead of creating `ExperimentResultWriter` once in `__init__`, we create it lazily per-call:
```python
def _result_writer(self) -> ExperimentResultWriter:
    return ExperimentResultWriter(
        experiment_dir=self.experiment_dir,
        tier_manager=self.tier_manager,
    )
```
This avoids issues where `experiment_dir` might change after construction and keeps the delegation wrappers simple.

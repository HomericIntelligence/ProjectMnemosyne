# Type Alias Consolidation - Detailed Notes

## Session Context

**Date:** 2026-02-15
**Issue:** #679 - Consolidate 5 RunResult types
**PR:** #699
**Branch:** 679-auto-impl

## Problem Statement

From the code quality audit (#594), we discovered 5 RunResult type definitions in the codebase:

1. `RunResultBase` - Base Pydantic model (scylla/core/results.py)
2. `MetricsRunResult` - Metrics aggregation variant
3. `ExecutorRunResult` - Executor tracking variant
4. `E2ERunResult` - E2E testing variant
5. `ReportingRunResult` - Persistence variant

Each domain module created a `RunResult = DomainVariant` type alias, causing:

- Import confusion (which RunResult?)
- Violated explicit-is-better-than-implicit
- Made code harder to understand

## Discovery Process

### Finding Type Aliases

```bash
$ grep -rn "^RunResult\s*=" scylla/ --include="*.py"
scylla/metrics/aggregator.py:53:RunResult = MetricsRunResult
scylla/executor/runner.py:108:RunResult = ExecutorRunResult
scylla/e2e/models.py:349:RunResult = E2ERunResult
scylla/reporting/result.py:100:RunResult = ReportingRunResult
```

### Finding All Class Definitions

```bash
$ grep -rn "class.*RunResult" scylla/ --include="*.py"
scylla/metrics/aggregator.py:25:class MetricsRunResult(RunResultBase):
scylla/executor/runner.py:88:class ExecutorRunResult(RunResultBase):
scylla/core/results.py:35:class RunResultBase(BaseModel):
scylla/core/results.py:94:class BaseRunResult:  # Deprecated dataclass
scylla/e2e/models.py:263:class E2ERunResult(RunResultBase):
scylla/reporting/result.py:51:class ReportingRunResult(RunResultBase):
```

### Finding All Import Locations

```bash
$ grep -rn "from.*import.*RunResult\b" scylla/ tests/ --include="*.py"
scylla/e2e/rerun.py:25:from scylla.e2e.models import ExperimentConfig, RunResult, ...
scylla/orchestrator.py:13:from scylla.reporting import ResultWriter, RunResult, ...
tests/unit/core/test_results.py:3:from scylla.core.results import BaseRunResult
tests/unit/e2e/test_regenerate.py:7:from scylla.e2e.models import ..., RunResult, ...
```

## Implementation Sequence

### Phase 1: Remove Type Aliases (Files 1-4)

1. ✅ `scylla/metrics/aggregator.py` - Removed line 53, updated all internal usages
2. ✅ `scylla/executor/runner.py` - Removed line 108, updated all internal usages
3. ✅ `scylla/e2e/models.py` - Removed line 349 (already using E2ERunResult internally)
4. ✅ `scylla/reporting/result.py` - Removed line 100, updated all internal usages

### Phase 2: Update **init**.py Exports (Files 5-8)

1. ✅ `scylla/e2e/__init__.py` - Changed import/export from `RunResult` to `E2ERunResult`
2. ✅ `scylla/executor/__init__.py` - Changed import/export from `RunResult` to `ExecutorRunResult`
3. ✅ `scylla/metrics/__init__.py` - Changed import/export from `RunResult` to `MetricsRunResult`
4. ✅ `scylla/reporting/__init__.py` - Changed import/export from `RunResult` to `ReportingRunResult`

### Phase 3: Update Dependent Modules (Files 9-12)

1. ✅ `scylla/e2e/rerun.py` - Updated to use `E2ERunResult`
2. ✅ `scylla/orchestrator.py` - Updated to use `ReportingRunResult`
3. ✅ `scylla/e2e/subtest_executor.py` - Updated to use `E2ERunResult`
4. ✅ `scylla/e2e/regenerate.py` - Used sed to bulk replace `RunResult` → `E2ERunResult`

### Phase 4: Cleanup Core Module (Files 13-14)

1. ✅ `scylla/core/results.py` - Removed deprecated `BaseRunResult` dataclass (lines 93-109)
2. ✅ `scylla/core/__init__.py` - Removed `BaseRunResult` from imports and exports

### Phase 5: Update Tests (Files 15-21)

1. ✅ `tests/unit/core/test_results.py` - Removed import and all tests for `BaseRunResult`
2. ✅ `tests/unit/e2e/test_regenerate.py` - Updated to use `E2ERunResult`
3. ✅ `tests/unit/e2e/test_models.py` - Updated to use `E2ERunResult`
4. ✅ `tests/unit/e2e/test_run_report.py` - Used sed to update to `E2ERunResult`
5. ✅ `tests/unit/executor/test_runner.py` - Updated to use `ExecutorRunResult`
6. ✅ `tests/unit/metrics/test_aggregator.py` - Updated to use `MetricsRunResult`
7. ✅ `tests/unit/reporting/test_result.py` - Updated to use `ReportingRunResult`

## Key Decisions

### Why NOT consolidate into one class?

**Decision:** Keep 4 separate domain variants, just remove type aliases

**Reasoning:**

- Different domains need different fields:
  - `MetricsRunResult`: run_id (string), pass_rate, impl_rate
  - `ExecutorRunResult`: status, execution_info, judgment, error_message
  - `E2ERunResult`: exit_code, token_stats, judges, workspace_path, logs_path
  - `ReportingRunResult`: test_id, tier_id, execution, metrics, judgment, grading
- Current inheritance hierarchy is correct and intentional
- Problem is naming confusion, not architectural duplication

### Why remove type aliases instead of keeping them for "backward compatibility"?

**Decision:** Remove all type aliases completely

**Reasoning:**

- Type aliases don't provide backward compatibility in Python - they just create ambiguity
- No external API to maintain (internal codebase only)
- Explicit names make code clearer and more maintainable
- One-time refactoring cost vs. ongoing confusion cost

### Why bottom-up dependency order?

**Decision:** Domain modules → **init**.py → dependent modules → tests

**Reasoning:**

- Keeps code working at each step
- Tests catch issues immediately
- Clear dependency chain to follow
- Easy to verify each phase

## Challenges Encountered

### Challenge 1: Finding all usages

**Issue:** Generic name `RunResult` appeared in many contexts

**Solution:**

- Used grep with word boundaries: `\bRunResult\b`
- Checked both source and test directories
- Verified **init**.py exports separately

### Challenge 2: Bulk updates in large files

**Issue:** Some files (regenerate.py, subtest_executor.py) had many references

**Solution:**

- Used sed for bulk replacement: `sed -i 's/\bRunResult\b/E2ERunResult/g'`
- Verified with git diff
- Ran tests after each bulk update

### Challenge 3: Test collection errors

**Issue:** Tests failed to collect due to import errors

**Solution:**

- Fixed **init**.py exports first
- Then fixed test imports
- Used `pytest -x` to stop at first error
- Fixed errors one at a time

### Challenge 4: Pre-commit auto-formatting

**Issue:** Ruff formatter modified files after our edits

**Solution:**

- Expected behavior - linters auto-fix formatting
- Re-ran pre-commit until all checks passed
- Committed auto-formatted code

## Test Results

### Before Consolidation

```bash
$ grep -rn "^RunResult\s*=" scylla/ --include="*.py" | wc -l
4
```

### After Consolidation

```bash
$ grep -rn "^RunResult\s*=" scylla/ --include="*.py" | wc -l
0
```

### Test Suite Results

```bash
$ pixi run pytest tests/ -q
2131 passed, 2 skipped, 8 warnings in 40.91s
```

### Pre-commit Results

```bash
$ pre-commit run --all-files
Check for shell=True (Security)..........................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Mypy Type Check Python...................................................Passed
Markdown Lint............................................................Passed
YAML Lint................................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```

## Metrics

- **Files modified:** 22
- **Lines added:** 189
- **Lines removed:** 288
- **Net reduction:** 99 lines
- **Test pass rate:** 100% (2131 passed, 2 skipped)
- **Time to complete:** ~2 hours (including discovery, implementation, testing)

## Commit Details

**Branch:** 679-auto-impl
**Commit:** ec36099
**Message:**

```
refactor(types): Consolidate 5 RunResult types into explicit variant names

Remove all RunResult type aliases and use explicit domain-specific names:
- MetricsRunResult (metrics/aggregator.py)
- ExecutorRunResult (executor/runner.py)
- E2ERunResult (e2e/models.py)
- ReportingRunResult (reporting/result.py)
- RunResultBase remains as canonical base type

Also remove deprecated BaseRunResult dataclass (replaced by RunResultBase).

This follows the explicit-is-better-than-implicit principle and eliminates
naming confusion from type alias shadowing.

Closes #679

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## PR Details

**PR:** #699
**URL:** <https://github.com/HomericIntelligence/ProjectScylla/pull/699>
**Status:** Open, auto-merge enabled (rebase)
**Label:** refactoring

## Lessons Learned

1. **Always map dependencies first** - Understanding the import graph before making changes prevents broken intermediate states

2. **Use bulk tools wisely** - sed is faster than manual edits, but verify each change

3. **Bottom-up is safer** - Start with leaf modules, work up to dependent modules

4. **One phase at a time** - Complete each phase before moving to the next

5. **Verify continuously** - Run tests after each major change

6. **Let formatters do their job** - Pre-commit auto-fixes are expected and helpful

7. **Explicit names win** - Type aliases for "backward compatibility" just create confusion

## Future Applications

This pattern can be applied to:

- Other domain model consolidations
- Post-migration cleanup (Pydantic, dataclasses → Pydantic, etc.)
- Any situation where type aliases shadow explicit names
- Improving type clarity in large Python codebases

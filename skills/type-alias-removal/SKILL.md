# Type Alias Removal Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Objective** | Remove redundant type aliases that shadow domain-specific variants to improve code clarity and maintainability |
| **Outcome** | ✅ Successfully removed 4 type aliases, updated 13 files, all tests passing |
| **Issue** | #679 - Consolidate RunResult Types |
| **PR** | #703 |

## When to Use This Skill

Use this workflow when you need to:

- **Remove type aliases** that shadow domain-specific class names (e.g., `RunResult = MetricsRunResult`)
- **Consolidate duplicate type names** across multiple modules
- **Make implicit types explicit** throughout a codebase
- **Refactor type hierarchies** to use clear, specific variant names
- **Improve type clarity** in large codebases with similar types

**Trigger Conditions:**

- Multiple modules define `TypeName = DomainVariantName` aliases
- Code uses generic type name when specific variant would be clearer
- Type hierarchy exists but naming is confusing/shadowed
- Import errors occur due to ambiguous type names

## Verified Workflow

### Phase 1: Discovery and Planning

1. **Identify all type aliases** using grep:

   ```bash
   grep -rn "^TypeName\s*=" scylla/ --include="*.py"
   ```

2. **Map the type hierarchy:**
   - 1 base type (e.g., `RunResultBase`)
   - N domain variants (e.g., `MetricsRunResult`, `ExecutorRunResult`)
   - N type aliases (e.g., `RunResult = MetricsRunResult`)

3. **Find all import usages:**

   ```bash
   grep -rn "from.*import.*TypeName\b" scylla/ --include="*.py"
   ```

4. **Document the plan:**
   - List all aliases to remove
   - List all imports to update
   - List all module `__init__.py` files to update
   - Identify deprecated code to remove

### Phase 2: Remove Type Aliases (Bottom-Up)

**CRITICAL:** Work in dependency order - remove aliases from domain modules first, then update dependent modules.

1. **Remove type aliases** from each domain module:

   ```python
   # BEFORE
   RunResult = MetricsRunResult

   # AFTER
   # (delete the line)
   ```

2. **Update all usages** within the same file:

   ```python
   # BEFORE
   def foo(runs: list[RunResult]) -> RunResult:

   # AFTER
   def foo(runs: list[MetricsRunResult]) -> MetricsRunResult:
   ```

3. **Update docstrings** to use specific variant names:

   ```python
   # BEFORE
   Returns:
       RunResult with execution details.

   # AFTER
   Returns:
       MetricsRunResult with execution details.
   ```

### Phase 3: Update Module Exports

**CRITICAL:** Update `__init__.py` files to export specific variant names.

1. **Update imports** in `__init__.py`:

   ```python
   # BEFORE
   from scylla.metrics.aggregator import (
       RunResult,
       RunAggregator,
   )

   # AFTER
   from scylla.metrics.aggregator import (
       MetricsRunResult,
       RunAggregator,
   )
   ```

2. **Update `__all__` list**:

   ```python
   # BEFORE
   __all__ = [
       "RunResult",
       "RunAggregator",
   ]

   # AFTER
   __all__ = [
       "MetricsRunResult",
       "RunAggregator",
   ]
   ```

### Phase 4: Update Dependent Modules

1. **Update imports** in dependent files:

   ```python
   # BEFORE
   from scylla.e2e.models import RunResult

   # AFTER
   from scylla.e2e.models import E2ERunResult
   ```

2. **Update type annotations:**

   ```python
   # BEFORE
   def process(result: RunResult) -> None:
       ...

   # AFTER
   def process(result: E2ERunResult) -> None:
       ...
   ```

3. **Update variable declarations:**

   ```python
   # BEFORE
   results: list[RunResult] = []

   # AFTER
   results: list[E2ERunResult] = []
   ```

### Phase 5: Remove Deprecated Code (Optional)

If there's a deprecated base class that was replaced:

1. **Remove deprecated class** from source:

   ```python
   # Delete from scylla/core/results.py
   @dataclass
   class BaseRunResult:  # DEPRECATED
       ...
   ```

2. **Remove from exports:**

   ```python
   # Remove from scylla/core/__init__.py
   from scylla.core.results import (
       BaseExecutionInfo,
       # BaseRunResult,  # <-- Remove
   )
   ```

3. **Remove tests** for deprecated class:

   ```python
   # Delete from tests/unit/core/test_results.py
   class TestBaseRunResult:  # <-- Delete entire class
       ...
   ```

### Phase 6: Verification

Run all verification checks to ensure correctness:

1. **Verify no aliases remain:**

   ```bash
   grep -rn "^RunResult\s*=" scylla/ --include="*.py"
   # Expected: No results
   ```

2. **Verify specific imports:**

   ```bash
   grep -rn "from.*import.*RunResult\b" scylla/ --include="*.py"
   # Expected: Should see specific variant names only
   ```

3. **Test imports:**

   ```bash
   pixi run python -c "from scylla.metrics.aggregator import MetricsRunResult; print('✓')"
   pixi run python -c "from scylla.executor.runner import ExecutorRunResult; print('✓')"
   pixi run python -c "from scylla.e2e.models import E2ERunResult; print('✓')"
   pixi run python -c "from scylla.reporting.result import ReportingRunResult; print('✓')"
   ```

4. **Run tests:**

   ```bash
   pixi run pytest tests/unit/core/test_results.py -v
   ```

5. **Run pre-commit hooks:**

   ```bash
   pre-commit run --all-files
   ```

## Failed Attempts

### ❌ Attempt 1: Missed Module Exports

**What I tried:** Only updated the type alias definitions and imports in source files, forgot about `__init__.py` exports.

**What happened:** Import errors when running verification:

```python
from scylla.executor.runner import ExecutorRunResult
# ImportError: cannot import name 'ExecutorRunResult'
```

**Why it failed:** The `__init__.py` files were still exporting the old `RunResult` name, not the specific variants.

**Fix:** Updated all `__init__.py` files to import and export specific variant names.

### ❌ Attempt 2: Top-Down Removal Order

**What I tried:** Started by updating dependent modules before removing aliases from domain modules.

**What happened:** Circular dependency issues and unclear which variant to use.

**Why it failed:** Dependent modules couldn't import specific variants because aliases were still present, creating ambiguity.

**Fix:** Switched to bottom-up approach - remove aliases from domain modules first, then update dependents.

### ❌ Attempt 3: Incomplete Search Patterns

**What I tried:** Used simple grep without word boundaries:

```bash
grep -rn "RunResult" scylla/
```

**What happened:** Too many false positives (docstrings, comments, class names).

**Why it failed:** Pattern matched "RunResult" in any context, not just type alias definitions.

**Fix:** Used more specific patterns:

- Type aliases: `^RunResult\s*=`
- Imports: `from.*import.*RunResult\b`
- Class inheritance: `class.*RunResult.*RunResultBase`

## Results & Parameters

### Before State

```
5 RunResult types in codebase:
- 1 base type: RunResultBase (Pydantic model)
- 4 domain variants:
  - MetricsRunResult (metrics/aggregator.py)
  - ExecutorRunResult (executor/runner.py)
  - E2ERunResult (e2e/models.py)
  - ReportingRunResult (reporting/result.py)
- 4 type aliases (PROBLEM):
  - RunResult = MetricsRunResult
  - RunResult = ExecutorRunResult
  - RunResult = E2ERunResult
  - RunResult = ReportingRunResult
- 1 deprecated type: BaseRunResult (dataclass)
```

### After State

```
5 RunResult types in codebase:
- 1 base type: RunResultBase (Pydantic model)
- 4 domain variants:
  - MetricsRunResult (metrics/aggregator.py)
  - ExecutorRunResult (executor/runner.py)
  - E2ERunResult (e2e/models.py)
  - ReportingRunResult (reporting/result.py)
- 0 type aliases ✅
- 0 deprecated types ✅
```

### Files Modified

```
Total: 13 files
- Core: scylla/core/results.py, scylla/core/__init__.py
- Metrics: scylla/metrics/aggregator.py, scylla/metrics/__init__.py
- Executor: scylla/executor/runner.py, scylla/executor/__init__.py
- E2E: scylla/e2e/models.py, scylla/e2e/rerun.py, scylla/e2e/__init__.py
- Reporting: scylla/reporting/result.py, scylla/reporting/__init__.py
- Orchestrator: scylla/orchestrator.py
- Tests: tests/unit/core/test_results.py, tests/unit/e2e/test_regenerate.py
```

### Verification Results

```
✅ No type aliases remain
✅ All imports use explicit variant names
✅ All module exports updated
✅ Tests pass (17/17 in core/test_results.py)
✅ Pre-commit hooks pass (ruff, mypy, markdownlint)
✅ All 5 RunResult variants import correctly
```

### Commands Used

**Discovery:**

```bash
# Find type aliases
grep -rn "^RunResult\s*=" scylla/ --include="*.py"

# Find imports
grep -rn "from.*import.*RunResult\b" scylla/ --include="*.py"

# Count inheritance hierarchy
grep -rn "class.*RunResult.*RunResultBase" scylla/ --include="*.py" | wc -l
```

**Verification:**

```bash
# Verify no aliases
grep -rn "^RunResult\s*=" scylla/ --include="*.py" || echo "✓ No aliases found"

# Test imports
pixi run python -c "from scylla.core.results import RunResultBase; print('✓ RunResultBase')"
pixi run python -c "from scylla.metrics.aggregator import MetricsRunResult; print('✓ MetricsRunResult')"
pixi run python -c "from scylla.executor.runner import ExecutorRunResult; print('✓ ExecutorRunResult')"
pixi run python -c "from scylla.e2e.models import E2ERunResult; print('✓ E2ERunResult')"
pixi run python -c "from scylla.reporting.result import ReportingRunResult; print('✓ ReportingRunResult')"

# Run tests
pixi run pytest tests/unit/core/test_results.py -v --tb=short

# Pre-commit hooks
pre-commit run --all-files
```

## Key Learnings

1. **Module exports matter:** Always update `__init__.py` files when changing exported names
2. **Bottom-up approach:** Remove aliases from domain modules before updating dependents
3. **Specific grep patterns:** Use precise patterns (`^TypeName\s*=`) to avoid false positives
4. **Comprehensive verification:** Test imports, run tests, and pre-commit hooks
5. **Explicit is better:** Using specific variant names (`MetricsRunResult`) is clearer than generic aliases (`RunResult`)

## Related Skills

- `codebase-consolidation` - Finding and consolidating duplicate types
- `dry-consolidation-workflow` - Systematic discovery commands
- `pydantic-model-dump` - Using `.model_dump()` for Pydantic serialization

## References

- Issue: <https://github.com/HomericIntelligence/ProjectScylla/issues/679>
- PR: <https://github.com/HomericIntelligence/ProjectScylla/pull/703>
- Related commit: 38a3df1 (Pydantic v2 migration)

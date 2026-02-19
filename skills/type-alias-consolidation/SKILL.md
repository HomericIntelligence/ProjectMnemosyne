# Type Alias Consolidation

| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Category** | architecture |
| **Objective** | Consolidate multiple type definitions by removing shadowing type aliases |
| **Outcome** | ✅ Successfully removed 4 type aliases, updated all imports, all tests pass |
| **Issue** | #679 |
| **PR** | #699 |

## Overview

This skill documents the process of consolidating multiple type definitions where each domain module created a local type alias that shadowed the specific variant name. The problem violated the "explicit is better than implicit" principle and made it unclear which variant was being used.

## When to Use

Use this workflow when you need to:

- Remove type aliases that shadow explicit domain-specific names
- Consolidate duplicate type definitions across a codebase
- Make type usage more explicit throughout a Python project
- Clean up post-migration technical debt (e.g., after Pydantic migration)

**Trigger conditions:**

- Multiple `TypeName = SpecificVariant` aliases exist across different modules
- Type imports are ambiguous (which `RunResult` are we importing?)
- Code uses generic names when specific variant names would be clearer
- Grep searches for a type return results from multiple locations

## Architecture Pattern

**Before (Anti-pattern):**

```python
# Base module: scylla/core/results.py
class RunResultBase(BaseModel):
    """Canonical base type"""
    pass

# Domain module 1: scylla/metrics/aggregator.py
class MetricsRunResult(RunResultBase):
    pass
RunResult = MetricsRunResult  # ❌ Shadows the variant name

# Domain module 2: scylla/executor/runner.py
class ExecutorRunResult(RunResultBase):
    pass
RunResult = ExecutorRunResult  # ❌ Shadows the variant name

# Usage becomes ambiguous
from scylla.metrics import RunResult  # Which one?
from scylla.executor import RunResult  # Which one?
```

**After (Correct pattern):**

```python
# Base module: scylla/core/results.py
class RunResultBase(BaseModel):
    """Canonical base type"""
    pass

# Domain module 1: scylla/metrics/aggregator.py
class MetricsRunResult(RunResultBase):
    pass
# ✅ No type alias - use explicit name

# Domain module 2: scylla/executor/runner.py
class ExecutorRunResult(RunResultBase):
    pass
# ✅ No type alias - use explicit name

# Usage is explicit
from scylla.metrics import MetricsRunResult  # Clear!
from scylla.executor import ExecutorRunResult  # Clear!
```

## Verified Workflow

### Phase 1: Discovery (5-10 minutes)

**1. Find all type aliases:**

```bash
# Find type alias definitions
grep -rn "^TypeName\s*=" scylla/ --include="*.py"

# Example output shows the problem:
# scylla/metrics/aggregator.py:53:RunResult = MetricsRunResult
# scylla/executor/runner.py:108:RunResult = ExecutorRunResult
# scylla/e2e/models.py:349:RunResult = E2ERunResult
# scylla/reporting/result.py:100:RunResult = ReportingRunResult
```

**2. Map the inheritance hierarchy:**

```bash
# Find base type
grep -rn "class.*Base" scylla/core/results.py

# Find all variants
grep -rn "class.*RunResult.*(" scylla/ --include="*.py"
```

**3. Map all import locations:**

```bash
# Find all imports
grep -rn "from.*import.*RunResult\b" scylla/ tests/ --include="*.py"
```

### Phase 2: Remove Type Aliases (Bottom-up)

**4. Remove aliases from domain modules:**

For each module with a type alias:

```python
# BEFORE
class DomainRunResult(RunResultBase):
    pass

RunResult = DomainRunResult  # ❌ Remove this line
```

```python
# AFTER
class DomainRunResult(RunResultBase):
    pass

# No type alias - just use DomainRunResult explicitly
```

**5. Update all usages in the same file:**

```python
# BEFORE
def process(result: RunResult) -> None:
    pass

results: list[RunResult] = []
```

```python
# AFTER
def process(result: DomainRunResult) -> None:
    pass

results: list[DomainRunResult] = []
```

### Phase 3: Update Imports (Dependent Modules)

**6. Update **init**.py exports:**

```python
# BEFORE - scylla/metrics/__init__.py
from scylla.metrics.aggregator import (
    RunResult,  # ❌ Generic name
    ...
)

__all__ = [
    "RunResult",  # ❌
    ...
]
```

```python
# AFTER - scylla/metrics/__init__.py
from scylla.metrics.aggregator import (
    MetricsRunResult,  # ✅ Explicit name
    ...
)

__all__ = [
    "MetricsRunResult",  # ✅
    ...
]
```

**7. Update dependent module imports:**

```bash
# Find modules that import the generic name
grep -rn "from scylla.metrics import.*RunResult" scylla/ tests/

# Update each import
# BEFORE: from scylla.metrics import RunResult
# AFTER:  from scylla.metrics import MetricsRunResult
```

**8. Update usages in dependent modules:**

Use sed for bulk updates if there are many files:

```bash
# Update all RunResult references to DomainRunResult
sed -i 's/\bRunResult\b/DomainRunResult/g' scylla/module/file.py
```

Or use the Edit tool for targeted updates.

### Phase 4: Update Tests

**9. Update test imports:**

```python
# BEFORE - tests/unit/metrics/test_aggregator.py
from scylla.metrics.aggregator import RunResult

def test_create():
    result = RunResult(...)  # ❌ Generic name
```

```python
# AFTER - tests/unit/metrics/test_aggregator.py
from scylla.metrics.aggregator import MetricsRunResult

def test_create():
    result = MetricsRunResult(...)  # ✅ Explicit name
```

**10. Update test class names (optional but recommended):**

```python
# BEFORE
class TestRunResult:
    """Tests for RunResult dataclass."""

# AFTER
class TestRunResult:  # Can keep class name
    """Tests for MetricsRunResult dataclass."""  # Update docstring
```

### Phase 5: Cleanup and Verification

**11. Remove deprecated legacy types:**

If there are old dataclass versions that were replaced:

```python
# scylla/core/results.py
# BEFORE
@dataclass
class BaseRunResult:  # ❌ Deprecated
    """Legacy base run result with common fields.

    DEPRECATED: Use RunResultBase (Pydantic) instead.
    """
    pass

# AFTER
# Delete the entire deprecated class
```

**12. Update core module exports:**

```python
# scylla/core/__init__.py
# BEFORE
from scylla.core.results import (
    BaseRunResult,  # ❌ Deprecated
)

# AFTER
# Remove from imports and __all__
```

**13. Run verification checks:**

```bash
# Verify no type aliases remain
grep -rn "^RunResult\s*=" scylla/ --include="*.py"
# Expected: No results

# Verify explicit names are used
grep -rn "from.*import.*RunResult\b" scylla/ --include="*.py"
# Expected: No results (all should use specific variant names)

# Verify base type is still the base
grep -rn "class.*RunResult.*RunResultBase" scylla/ --include="*.py"
# Expected: 4 results (the 4 domain variants)
```

**14. Run full test suite:**

```bash
pixi run pytest tests/ -v
# All tests should pass
```

**15. Run pre-commit hooks:**

```bash
pre-commit run --all-files
# All checks should pass (formatters may auto-fix)
```

## Failed Attempts & Lessons Learned

### ❌ Failed Approach 1: Trying to consolidate into one class

**What we tried:**
Initially considered merging all 4 domain variants into a single `RunResult` class.

**Why it failed:**

- Different domains need different fields (execution_info, judgment, workspace_path, etc.)
- Current inheritance hierarchy is correct and intentional
- Problem was naming confusion from type aliases, not architectural duplication

**Lesson:**
Not all "duplicate" types are true duplicates. Distinguish between:

- **True duplicates**: Same structure, same purpose, should be merged
- **Intentional variants**: Different domains, different fields, should stay separate

### ❌ Failed Approach 2: Updating imports before removing aliases

**What we tried:**
Started by updating import statements before removing the type aliases from source modules.

**Why it failed:**

- Created broken intermediate state
- Tests failed during transition
- Hard to track which modules were updated

**Lesson:**
Follow dependency order (bottom-up):

1. Remove aliases from domain modules first
2. Then update imports in dependent modules
3. This keeps code working at each step

### ❌ Failed Approach 3: Manual search and replace

**What we tried:**
Manually searching for each `RunResult` reference and updating one by one.

**Why it failed:**

- Too slow for files with many references
- Easy to miss usages in comments or docstrings
- Inconsistent updates

**Lesson:**

- Use `sed` for bulk updates in files with many references
- Use targeted Edit tool calls for files with few references
- Always verify with grep after bulk updates

### ✅ What Worked: Systematic bottom-up approach

**Success factors:**

1. **Discovery phase**: Mapped all locations before starting
2. **Bottom-up order**: Domain modules → **init**.py → dependent modules → tests
3. **Verification at each phase**: grep + tests after each major change
4. **Bulk updates**: sed for files with many references
5. **Clean commit**: All changes in one atomic commit

## Results & Parameters

### Files Modified (22 total)

**Core modules:**

- `scylla/core/__init__.py` - Removed BaseRunResult export
- `scylla/core/results.py` - Removed deprecated BaseRunResult dataclass

**Domain modules (4):**

- `scylla/metrics/aggregator.py` - Removed `RunResult = MetricsRunResult`
- `scylla/executor/runner.py` - Removed `RunResult = ExecutorRunResult`
- `scylla/e2e/models.py` - Removed `RunResult = E2ERunResult`
- `scylla/reporting/result.py` - Removed `RunResult = ReportingRunResult`

**Module **init**.py files (4):**

- `scylla/metrics/__init__.py` - Export `MetricsRunResult`
- `scylla/executor/__init__.py` - Export `ExecutorRunResult`
- `scylla/e2e/__init__.py` - Export `E2ERunResult`
- `scylla/reporting/__init__.py` - Export `ReportingRunResult`

**Dependent modules (3):**

- `scylla/e2e/rerun.py` - Use `E2ERunResult`
- `scylla/e2e/subtest_executor.py` - Use `E2ERunResult`
- `scylla/e2e/regenerate.py` - Use `E2ERunResult`
- `scylla/orchestrator.py` - Use `ReportingRunResult`

**Test files (6):**

- `tests/unit/core/test_results.py` - Removed BaseRunResult tests
- `tests/unit/e2e/test_models.py` - Use `E2ERunResult`
- `tests/unit/e2e/test_regenerate.py` - Use `E2ERunResult`
- `tests/unit/e2e/test_run_report.py` - Use `E2ERunResult`
- `tests/unit/executor/test_runner.py` - Use `ExecutorRunResult`
- `tests/unit/metrics/test_aggregator.py` - Use `MetricsRunResult`
- `tests/unit/reporting/test_result.py` - Use `ReportingRunResult`

### Final Architecture

```
RunResultBase (core/results.py) - Base Pydantic model
├── MetricsRunResult - Statistical aggregation
├── ExecutorRunResult - Execution tracking
├── E2ERunResult - E2E testing
└── ReportingRunResult - Persistence
```

### Test Results

```bash
# Before
- 5 type definitions found (1 base + 4 variants)
- 4 type aliases shadowing variant names
- Import confusion across modules

# After
- 5 type definitions remain (1 base + 4 variants)
- 0 type aliases
- Explicit imports everywhere
- All 2131 tests pass
- Pre-commit hooks pass
```

### Commit Message Template

```
refactor(types): Consolidate N TypeName types into explicit variant names

Remove all TypeName type aliases and use explicit domain-specific names:
- DomainARunResult (module/a.py)
- DomainBRunResult (module/b.py)
- DomainCRunResult (module/c.py)

Also remove deprecated LegacyTypeName dataclass (replaced by TypeNameBase).

This follows the explicit-is-better-than-implicit principle and eliminates
naming confusion from type alias shadowing.

Closes #<issue-number>
```

## Commands Reference

```bash
# Discovery
grep -rn "^TypeName\s*=" scylla/ --include="*.py"
grep -rn "class.*TypeName.*(" scylla/ --include="*.py"
grep -rn "from.*import.*TypeName\b" scylla/ tests/ --include="*.py"

# Bulk updates (use carefully)
sed -i 's/\bTypeName\b/DomainTypeName/g' scylla/module/file.py

# Verification
grep -rn "^TypeName\s*=" scylla/ --include="*.py"  # Should be empty
pixi run pytest tests/ -v
pre-commit run --all-files
```

## Related Skills

- `dry-consolidation-workflow` - General DRY principle consolidation
- `codebase-consolidation` - Finding and consolidating duplicate types
- `pydantic-model-dump` - Pydantic v2 migration patterns

## Tags

`#architecture` `#refactoring` `#type-consolidation` `#python` `#pydantic` `#technical-debt` `#explicit-over-implicit`

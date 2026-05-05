---
name: type-alias-consolidation
description: "Use when: (1) multiple modules define TypeName = DomainVariant aliases causing naming confusion and you need to remove redundant type aliases that shadow domain-specific variant names; (2) applying the Pydantic inheritance pattern to metrics/judgment/cost types (MetricsInfo, JudgmentInfo) or other evaluation data types; (3) a Pydantic base class lacks frozen=True while its sibling base types all use ConfigDict(frozen=True) and you need an immutability consistency audit; (4) discovering and categorizing duplicate code (true-vs-intentional-variant taxonomy) for codebase-wide consolidation; (5) migrating Python @dataclass classes to Pydantic BaseModel in bulk (24-class checklist, pytest fixture migration); (6) fixing AttributeError from Pydantic v2 .to_dict() vs .model_dump() regression."
category: architecture
date: 2026-02-15
version: 3.1.0
user-invocable: false
tags: [refactoring, type-consolidation, python, architecture, pydantic, frozen, immutability, dataclass, migration, serialization, duplicate-discovery]
absorbed:
- pydantic-type-consolidation-metrics-judgment (v1.0.0, 2026-05-03)
- pydantic-frozen-consistency (v1.0.0, 2026-05-03)
- codebase-consolidation (v1.0.0, 2026-05-04)
- migrate-dataclass-to-pydantic (v1.0.0, 2026-05-04)
- pydantic-model-dump (v1.0.0, 2026-05-04)
---
# Type Alias Consolidation

| Field | Value |
| ------- | ------- |
| **Date** | 2026-02-15 |
| **Category** | architecture |
| **Objective** | Consolidate multiple type definitions by removing shadowing type aliases |
| **Outcome** | ✅ Successfully removed 4 type aliases, updated all imports, all tests pass. Merged 2026-05-03: absorbed pydantic-type-consolidation-metrics-judgment (v1.0.0) and pydantic-frozen-consistency (v1.0.0). |
| **Issue** | #679 - Consolidate RunResult Types |
| **PRs** | #699, #703, #788 (MetricsInfo/JudgmentInfo), #846 (frozen consistency) |

**Absorbed**: pydantic-type-consolidation-metrics-judgment, pydantic-frozen-consistency on 2026-05-03; codebase-consolidation, migrate-dataclass-to-pydantic, pydantic-model-dump on 2026-05-04

## Overview

This skill documents the process of consolidating multiple type definitions where each domain module created a local type alias that shadowed the specific variant name. The problem violated the "explicit is better than implicit" principle and made it unclear which variant was being used.

## When to Use

Use this workflow when you need to:

- Remove type aliases that shadow explicit domain-specific names
- Consolidate duplicate type definitions across a codebase
- Make type usage more explicit throughout a Python project
- Clean up post-migration technical debt (e.g., after Pydantic migration)
- Apply Pydantic inheritance to metrics/cost types (tokens, cost_usd) or judgment/grading types (passed, impl_rate)
- Extract a base class proactively for single-module types to enable future reuse
- Audit and enforce `frozen=True` immutability consistency across Pydantic base classes

**Trigger conditions:**

- Multiple `TypeName = SpecificVariant` aliases exist across different modules
- Type imports are ambiguous (which `RunResult` are we importing?)
- Code uses generic names when specific variant names would be clearer
- Grep searches for a type return results from multiple locations
- "apply same consolidation pattern to [Type]" / "MetricsInfo needs a base class" / "JudgmentInfo variants across modules"
- A Pydantic `BaseModel` subclass uses `ConfigDict()` with no arguments while sibling base classes use `ConfigDict(frozen=True)`
- Issue asking to "evaluate whether X should also be frozen, or document why it is intentionally mutable"
- Subtypes override `model_config` dropping inherited settings (e.g., `arbitrary_types_allowed=True` without `frozen=True`)

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

**6. Update docstrings** to use specific variant names:

```python
# BEFORE
Returns:
    RunResult with execution details.

# AFTER
Returns:
    MetricsRunResult with execution details.
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

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Consolidate all variants into one class | Merging all 4 domain `RunResult` variants into a single class | Different domains need different fields; hierarchy was intentional, not duplicated | Not all "duplicate" types are true duplicates — distinguish true duplicates (same structure/purpose) from intentional variants (different domains/fields) |
| Update imports before removing aliases | Updating import statements before removing type aliases from source modules | Created broken intermediate state; tests failed during transition; hard to track progress | Follow bottom-up dependency order: remove aliases from domain modules first, then update imports in dependents |
| Manual search and replace | Manually searching for each `RunResult` reference and updating one by one | Too slow for files with many references; easy to miss usages in comments or docstrings | Use `sed` for bulk updates in files with many references; use targeted edits for files with few references; always verify with grep after bulk updates |
| Assumed mutation sites on similar field names blocked `frozen=True` | Grepped for `.cost_usd =` or `.duration_seconds =` mutation patterns and assumed they blocked freezing | The mutations were on dataclasses or other Pydantic models with the same field names, not on the target base class | Always verify the *type* of the mutated object before concluding `frozen=True` is incompatible |

### ✅ What Worked: Systematic bottom-up approach

**Success factors:**

1. **Discovery phase**: Mapped all locations before starting
2. **Bottom-up order**: Domain modules → **init**.py → dependent modules → tests
3. **Verification at each phase**: grep + tests after each major change
4. **Bulk updates**: sed for files with many references
5. **Clean commit**: All changes in one atomic commit
6. **Ruff formatter runs automatically** on commit — let pre-commit fix formatting, then recommit (not a real failure)
7. **`frozen=True` subtype audit**: After adding `frozen=True` to a base, grep all subtypes for their own `model_config` and explicitly add `frozen=True` to each one that overrides it

## Pydantic Type Consolidation — Metrics & Judgment Workflow

*(Absorbed from pydantic-type-consolidation-metrics-judgment v1.0.0, Issue #729, PR #788)*

Use this sub-workflow when consolidating types that hold **metrics/cost data** (tokens, cost_usd) or **judgment/grading data** (passed, impl_rate), especially when the type exists only in one module and no duplicates exist yet — proactive extraction for future reuse.

### Key Differences from RunResult Pattern

| Aspect | RunResult (#679) | MetricsInfo/JudgmentInfo (#729) |
| -------- | --------------------- | --------------------------------- |
| Starting variants | Multiple definitions across modules | 1 definition each (reporting only) |
| Discovery scope | Found duplicates via grep | No duplicates — preemptive extraction |
| Field defaults | `duration_seconds=0.0`, `timed_out=False` | `cost_usd=0.0`, `impl_rate=0.0` |
| Required base fields | `exit_code` | `tokens_input/output`, `passed` |
| Subtype additions | `status`, `container_id`, etc. | `api_calls` (reporting), `letter_grade` (reporting) |

### Step 1: Identify the Pattern Match

```bash
# Check if types already have a base class
grep -n "class MetricsInfo\|class JudgmentInfo" <project-root>/reporting/result.py
# Result: both inherit from BaseModel directly — consolidation candidate
```

### Design Base Fields

For **MetricsInfoBase** — core token/cost concepts:

- `tokens_input: int = Field(...)` — always required
- `tokens_output: int = Field(...)` — always required
- `cost_usd: float = Field(default=0.0)` — optional (may not be known yet)

For **JudgmentInfoBase** — core judgment concepts:

- `passed: bool = Field(...)` — always required
- `impl_rate: float = Field(default=0.0)` — optional (may not be computed)

### Add Base Types and Deprecate Legacy Dataclass

```python
class MetricsInfoBase(BaseModel):
    """Base token and cost metrics shared across modules."""

    model_config = ConfigDict(frozen=True)

    tokens_input: int = Field(..., description="Input tokens")
    tokens_output: int = Field(..., description="Output tokens")
    cost_usd: float = Field(default=0.0, description="Cost in USD")


class JudgmentInfoBase(BaseModel):
    """Base judge evaluation results shared across modules."""

    model_config = ConfigDict(frozen=True)

    passed: bool = Field(..., description="Whether the run passed")
    impl_rate: float = Field(default=0.0, description="Implementation rate (0.0-1.0)")
```

**Placement**: After `ExecutionInfoBase`, before `@dataclass` legacy types.

### Deprecate the Legacy Dataclass (doc-only change)

```python
@dataclass
class BaseRunMetrics:
    """Base metrics shared across run result types.

    .. deprecated::
        Use MetricsInfoBase (Pydantic model) instead. This dataclass is kept
        for backward compatibility only. New code should use MetricsInfoBase
        and its domain-specific subtypes (MetricsInfo in reporting/result.py).
    """

    tokens_input: int
    tokens_output: int
    cost_usd: float
```

### Update Domain Subtypes to Inherit

```python
# Before:
class MetricsInfo(BaseModel):
    tokens_input: int = Field(...)
    tokens_output: int = Field(...)
    cost_usd: float = Field(...)
    api_calls: int = Field(...)

class JudgmentInfo(BaseModel):
    passed: bool = Field(...)
    impl_rate: float = Field(...)
    letter_grade: str = Field(...)

# After:
class MetricsInfo(MetricsInfoBase):
    """Inherits tokens_input, tokens_output, cost_usd from MetricsInfoBase."""
    api_calls: int = Field(..., description="Number of API calls")

class JudgmentInfo(JudgmentInfoBase):
    """Inherits passed, impl_rate from JudgmentInfoBase."""
    letter_grade: str = Field(..., description="Letter grade")
```

**Key**: Remove the redefined fields from the subtype — they are inherited.

### Export from `core/__init__.py`

```python
from scylla.core.results import (
    ExecutionInfoBase,
    JudgmentInfoBase,    # New
    MetricsInfoBase,     # New
)

__all__ = [
    "ExecutionInfoBase",
    "JudgmentInfoBase",
    "MetricsInfoBase",
]
```

### Update Module Docstring

Add hierarchy documentation in `<project-root>/core/results.py`:

```python
"""
MetricsInfo inheritance hierarchy (Issue #729):
- MetricsInfoBase (this module) - Base Pydantic model with token/cost fields
  └── MetricsInfo (reporting/result.py) - Result persistence with api_calls

JudgmentInfo inheritance hierarchy (Issue #729):
- JudgmentInfoBase (this module) - Base Pydantic model with judgment fields
  └── JudgmentInfo (reporting/result.py) - Result persistence with letter_grade

Legacy dataclasses (deprecated):
- BaseExecutionInfo - Kept for backward compatibility, use ExecutionInfoBase instead
- BaseRunMetrics - Kept for backward compatibility, use MetricsInfoBase instead
"""
```

### Test Coverage Pattern

```python
class TestMetricsInfoBase:
    def test_construction_basic(self):
        m = MetricsInfoBase(tokens_input=100, tokens_output=50)
        assert m.cost_usd == 0.0  # Default

    def test_immutability(self):
        m = MetricsInfoBase(tokens_input=100, tokens_output=50)
        with pytest.raises(ValidationError):
            m.tokens_input = 200  # frozen=True

    def test_model_dump(self):
        m = MetricsInfoBase(tokens_input=100, tokens_output=50, cost_usd=0.01)
        assert m.model_dump() == {"tokens_input": 100, "tokens_output": 50, "cost_usd": 0.01}

class TestMetricsInfoInheritance:
    def test_metrics_info_is_metrics_info_base(self):
        m = MetricsInfo(tokens_input=100, tokens_output=50, cost_usd=0.01, api_calls=3)
        assert isinstance(m, MetricsInfoBase)

    def test_model_dump_includes_all_fields(self):
        m = MetricsInfo(tokens_input=100, tokens_output=50, cost_usd=0.01, api_calls=3)
        data = m.model_dump()
        assert data == {"tokens_input": 100, "tokens_output": 50, "cost_usd": 0.01, "api_calls": 3}

class TestBaseRunMetricsDeprecation:
    def test_dataclass_and_pydantic_have_same_fields(self):
        dataclass_m = BaseRunMetrics(tokens_input=1000, tokens_output=500, cost_usd=0.05)
        pydantic_m = MetricsInfoBase(tokens_input=1000, tokens_output=500, cost_usd=0.05)
        assert dataclass_m.tokens_input == pydantic_m.tokens_input
        assert dataclass_m.tokens_output == pydantic_m.tokens_output
        assert dataclass_m.cost_usd == pydantic_m.cost_usd
```

### Test Coverage Summary (MetricsInfo/JudgmentInfo)

```
tests/unit/core/test_metrics_judgment.py — 33 new tests
  - TestMetricsInfoBase ..................... 11 tests
  - TestJudgmentInfoBase ................... 10 tests
  - TestMetricsInfoInheritance .............. 6 tests
  - TestJudgmentInfoInheritance ............. 6 tests (+ @parametrize for 5 grades)

tests/unit/core/test_results.py — 2 new tests
  - TestBaseRunMetricsDeprecation ........... 2 tests

All 2247 existing tests: ✅ passing (no regressions)
```

### Verification Commands (Pydantic Type Consolidation)

```bash
# Core imports
pixi run python -c "from scylla.core import MetricsInfoBase, JudgmentInfoBase; print('core OK')"

# Inheritance
pixi run python -c "
from scylla.reporting.result import MetricsInfo, JudgmentInfo
from scylla.core import MetricsInfoBase, JudgmentInfoBase
m = MetricsInfo(tokens_input=100, tokens_output=50, cost_usd=0.01, api_calls=1)
j = JudgmentInfo(passed=True, impl_rate=0.9, letter_grade='A')
print('MetricsInfo is MetricsInfoBase:', isinstance(m, MetricsInfoBase))
print('JudgmentInfo is JudgmentInfoBase:', isinstance(j, JudgmentInfoBase))
"

# Backward compat
pixi run python -c "from scylla.core.results import BaseRunMetrics; m = BaseRunMetrics(tokens_input=100, tokens_output=50, cost_usd=0.01); print('BaseRunMetrics OK')"

# Full test suite
pixi run python -m pytest tests/ --no-cov -q
```

### Pre-commit (Pydantic Type Consolidation)

```bash
pre-commit run --all-files
# All hooks pass: ruff-format, ruff-check, mypy, markdownlint, yamllint, shellcheck, etc.
```

---

## Pydantic Frozen Consistency Workflow

*(Absorbed from pydantic-frozen-consistency v1.0.0, Issue #799, PR #846)*

Use this sub-workflow when auditing `frozen=True` immutability consistency across sibling Pydantic base classes.

### Step 1: Confirm No Post-Construction Mutations Exist

```bash
# Find all subclasses
grep -rn "class.*TargetBase\|TargetBase" <project-root>/ --include="*.py" | grep "class "

# Check for post-construction mutations on those types
grep -rn "\.(field_name)\s*=" <project-root>/ --include="*.py"
```

**Key insight**: Mutation sites may exist on Pydantic models with similar field names but on *different* classes (dataclasses, other Pydantic models). Always verify the type of the mutated object before concluding `frozen=True` is incompatible.

### Step 2: Update the Base Class

```python
# Before
model_config = ConfigDict()

# After
model_config = ConfigDict(frozen=True)
```

### Step 3: Update Subtypes That Override `model_config`

Pydantic subclasses that define their own `model_config` **do not inherit** the parent's config — they replace it entirely. Find all subtypes that override:

```bash
grep -n "model_config" <project-root>/path/to/subtype.py
```

For each subtype with its own `model_config`, explicitly include `frozen=True`:

```python
# Before (in subtype)
model_config = ConfigDict(arbitrary_types_allowed=True)

# After
model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
```

Subtypes that do **not** define `model_config` automatically inherit `frozen=True` from the base — no change needed.

### Step 4: Add Immutability Tests

```python
class TestTargetBase:
    def test_immutability(self) -> None:
        """Test that instances are frozen (immutable)."""
        result = TargetBase(field=value)
        with pytest.raises(ValidationError):
            result.field = other_value  # type: ignore

    def test_construction_defaults(self) -> None: ...
    def test_construction_explicit(self) -> None: ...
    def test_model_dump(self) -> None: ...
    def test_equality(self) -> None: ...
```

### Step 5: Run Tests

```bash
pixi run python -m pytest tests/ -v
```

---

## Key Insights

1. **Not all "duplicates" should merge** — Distinguish true duplicates (same structure/purpose) from intentional variants (different domains/fields).
2. **Bottom-up dependency order** — Remove aliases from domain modules first, then propagate to imports and dependents.
3. **Use sed for bulk updates**, Edit tool for targeted changes; always verify with grep after bulk updates.
4. **Pattern scales cleanly** — Second and third applications of pydantic-type-consolidation required no new patterns.
5. **Default strategy**: Required fields = always semantically meaningful; Optional+default = may not be known at construction time.
6. **Even single-module types benefit from base extraction** — No duplicate needed; base is created proactively for future reuse.
7. **Ruff formatter runs automatically** on commit — let pre-commit fix it, then recommit (not a real failure).
8. **`BaseRunMetrics` deprecation is doc-only** — No behavior change, just a `.. deprecated::` docstring.
9. **Pydantic config inheritance is NOT additive** — When a subclass defines its own `model_config`, it replaces (not merges with) the parent's config. Subtypes with NO `model_config` inherit `frozen=True` automatically; subtypes WITH their own `model_config` must explicitly repeat `frozen=True`.
10. **Mutation false positives** — Field-name grep hits for `cost_usd =` or `duration_seconds =` may be on dataclasses or unrelated models; always confirm the object type before ruling out `frozen=True`.

---

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
- `pydantic-type-consolidation` - Foundational pattern (ExecutionInfo, #658)
- `migrate-dataclass-to-pydantic` - General dataclass → Pydantic migration

## References

- Issue #679: <https://github.com/HomericIntelligence/ProjectScylla/issues/679>
- PR #699: Initial consolidation
- PR #703: <https://github.com/HomericIntelligence/ProjectScylla/pull/703>
- Related commit: 38a3df1 (Pydantic v2 migration)
- Issue #729 (MetricsInfo/JudgmentInfo): <https://github.com/HomericIntelligence/ProjectScylla/issues/729>
- PR #788 (MetricsInfo/JudgmentInfo): <https://github.com/HomericIntelligence/ProjectScylla/pull/788>
- Issue #799 (frozen consistency): #799
- PR #846 (frozen consistency): #846
- Prior application: ExecutionInfo consolidation (#658, PR #726)

## Tags

`#architecture` `#refactoring` `#type-consolidation` `#python` `#pydantic` `#technical-debt` `#explicit-over-implicit`

---

## Duplicate Discovery & Consolidation Taxonomy

*(Absorbed from codebase-consolidation v1.0.0, 2026-01-02)*

Use this sub-workflow when auditing a codebase for duplicate implementations before deciding whether to merge them.

### True Duplicate vs. Intentional Variant

Before merging anything, categorize every duplication candidate:

| Type | Example | Action |
| ------ | --------- | -------- |
| True duplicates | Same function in 3 files | Consolidate to single source |
| Intentional variants | 4 RunResult types for different domains | Document with cross-references |

This taxonomy prevents the most common failure mode: merging types that look identical but have different domain semantics.

### Discovery Grep Patterns

```bash
# Find duplicate function names
grep -r "def calculate_mean\|def calculate_median" src/

# Find duplicate class names
grep -r "class RunResult\|class ExecutionInfo" src/

# Find similar field signatures
grep -r "tokens_input.*tokens_output" src/
```

### Issue Planning Template (before coding)

Create a GitHub issue with this structure before any refactor:

```markdown
## Objective
Reduce duplication of X by creating unified base types.

## Problem
### X - N separate definitions:
| Location | Purpose | Key Fields |
|----------|---------|------------|
| file1.py:L-L | Purpose A | field1, field2 |
| file2.py:L-L | Purpose B | field1, field3 |

## Implementation Plan
1. Create shared module with base types
2. Update each file to import from shared module
3. Add type aliases for backward compatibility
```

### Dependency-Ordered Execution

Execute consolidations in dependency order (lower deps first):

```
statistics.py (no deps)
    ↓
grading.py (uses statistics)
    ↓
aggregator.py (uses grading + statistics)
    ↓
pricing.py (used by adapters)
    ↓
result types (documentation only)
```

### Backward-Compatible Alias Patterns

**Type alias for renamed types:**
```python
# In the new location
from scylla.metrics.statistics import Statistics

# In the old location (backward compat)
from scylla.metrics.statistics import Statistics
AggregatedStats = Statistics  # Backward-compatible alias
```

**Function alias for moved functions:**
```python
from scylla.metrics.grading import assign_letter_grade
assign_grade = assign_letter_grade  # Backward-compatible alias
```

**Cross-reference docstring for intentional variants:**
```python
class RunResult:
    """Result for statistical aggregation.

    This is a simplified result type used for aggregation.
    For detailed execution results, see:
    - executor/runner.py:RunResult (execution tracking)
    - e2e/models.py:RunResult (E2E test results)
    - reporting/result.py:RunResult (persistence)
    """
```

### Standard Grading Thresholds (Industry-Aligned)

```yaml
grade_scale:
  S: 1.00   # Amazing - exceptional
  A: 0.80   # Excellent - production ready
  B: 0.60   # Good - minor improvements
  C: 0.40   # Acceptable - functional with issues
  D: 0.20   # Marginal - significant issues
  F: 0.00   # Failing
```

### Pricing Configuration Template

```python
class ModelPricing(BaseModel):
    model_id: str
    input_cost_per_million: float   # Always use per-million
    output_cost_per_million: float
    cached_cost_per_million: float = 0.0

MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-20250514": ModelPricing(
        model_id="claude-sonnet-4-20250514",
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
    ),
}
```

### Consolidation Results Reference

| Category | Before | After |
| ---------- | -------- | ------- |
| Statistics functions | 3 copies | 1 source + 2 imports |
| Grade assignment functions | 5 implementations | 1 canonical + aliases |
| Pricing implementations | 2 (different units) | 1 centralized (per-million) |
| Result types | 4 undocumented variants | 4 cross-referenced variants |

---

## Dataclass → Pydantic BaseModel Migration

*(Absorbed from migrate-dataclass-to-pydantic v1.0.0, PR #592, 2026-02-13)*

Use this sub-workflow when bulk-migrating `@dataclass` classes to Pydantic `BaseModel` (verified: 24 classes across 8 files).

### Migration Checklist (Per File)

- [ ] Update imports (`dataclass`/`field` → `BaseModel`/`Field`)
- [ ] Remove `@dataclass` decorators
- [ ] Convert class to inherit from `BaseModel`
- [ ] Convert `field(default_factory=...)` → `Field(default_factory=...)`
- [ ] Add `ConfigDict(arbitrary_types_allowed=True)` if needed (Path/Enum fields)
- [ ] Convert `__post_init__` to `@model_validator` or `Field(default_factory=...)`
- [ ] Handle forward references with string annotations + `model_rebuild()`
- [ ] Keep custom `to_dict()`, `from_dict()`, `@property` methods
- [ ] Run tests: `<package-manager> python -m pytest tests/unit/<module>/ -v`
- [ ] Run linters: `pre-commit run --all-files`

### Core Conversion Pattern

```python
# Before
from dataclasses import dataclass, field

@dataclass
class TokenStats:
    input_tokens: int = 0
    output_tokens: int = 0
    items: list[str] = field(default_factory=list)

# After
from pydantic import BaseModel, ConfigDict, Field

class TokenStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    items: list[str] = Field(default_factory=list)
```

### Add `model_config` for Non-Standard Types

```python
class ExperimentConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    experiment_id: str
    task_prompt_file: Path  # Requires arbitrary_types_allowed
    tiers_to_run: list[TierID] = Field(default_factory=list)
```

### `__post_init__` Conversion Patterns

**Validation → `@model_validator`:**
```python
# Before
@dataclass
class RateLimitInfo:
    source: str
    def __post_init__(self) -> None:
        if self.source not in ("agent", "judge"):
            raise ValueError(f"Invalid source: {self.source}")

# After
class RateLimitInfo(BaseModel):
    source: str
    @model_validator(mode="after")
    def validate_source(self) -> RateLimitInfo:
        if self.source not in ("agent", "judge"):
            raise ValueError(f"Invalid source: {self.source}")
        return self
```

**Default init → `Field(default_factory=...)`:**
```python
# Before
@dataclass
class RerunJudgeStats:
    per_slot_stats: dict[int, dict[str, int]] = None
    def __post_init__(self):
        if self.per_slot_stats is None:
            self.per_slot_stats = {}

# After
class RerunJudgeStats(BaseModel):
    per_slot_stats: dict[int, dict[str, int]] = Field(default_factory=dict)
```

### Forward Reference Fix

```python
# In models.py
class SubTestResult(BaseModel):
    rate_limit_info: "RateLimitInfo | None" = None

# At end of file
from scylla.e2e.rate_limit import RateLimitInfo  # noqa: E402
SubTestResult.model_rebuild()
```

### Common Issues

**Path serialization in JSON** — use `mode="json"`:
```python
# ❌ Fails: Path → PosixPath (not JSON serializable)
config_dict = config.model_dump()
json.dumps(config_dict)

# ✅ Works: Path → str
config_dict = config.model_dump(mode="json")
json.dumps(config_dict)
```

**Pydantic requires keyword arguments** (positional args fail):
```python
# ❌ Fails with Pydantic
vote = JudgeVote("01", 0.85, 0.9, "Good")

# ✅ Use keyword arguments
vote = JudgeVote(subtest_id="01", score=0.85, confidence=0.9, reasoning="Good")
```

**Keep custom `to_dict()` methods** — `model_dump()` does not handle Enum→value or Path→str:
```python
class SubTestConfig(BaseModel):
    tier_id: TierID
    claude_md_path: Path | None

    # Keep this for custom serialization
    def to_dict(self) -> dict[str, Any]:
        return {
            "tier_id": self.tier_id.value,   # Enum → str
            "claude_md_path": str(self.claude_md_path) if self.claude_md_path else None,
        }
```

### Patterns Preserved Seamlessly

```python
# ✅ Properties work as-is
@property
def total_tokens(self) -> int:
    return self.input_tokens + self.output_tokens

# ✅ Dunder methods work as-is
def __add__(self, other: TokenStats) -> TokenStats:
    return TokenStats(
        input_tokens=self.input_tokens + other.input_tokens,
        output_tokens=self.output_tokens + other.output_tokens,
    )

# ✅ Class methods work as-is
@classmethod
def load(cls, path: Path) -> ExperimentConfig:
    with open(path) as f:
        data = json.load(f)
    return cls(**data)
```

### Pytest Fixture Migration Note

Tests that construct dataclass instances with positional arguments must be updated to keyword arguments. Fixtures that patch or mock dataclasses may also need updating if the fixture relies on `dataclasses.asdict()` — replace with `.model_dump()`.

### Migration Statistics (Reference Run)

| Metric | Value |
| -------- | ------- |
| Classes migrated | 24 |
| Files modified | 10 |
| Lines changed | +94, -80 |
| Tests passing | 2,044 (100%) |
| E2E tests passing | 430 (100%) |

---

## Pydantic v2 `.model_dump()` Quick-Reference Fix

*(Absorbed from pydantic-model-dump v1.0.0, PR #136, 2026-01-04)*

Use when encountering `AttributeError: 'ModelName' object has no attribute 'to_dict'` after a Pydantic v1 → v2 migration.

### Root Cause

Pydantic v2 removed `.dict()` and does not define `.to_dict()`. Code that called `.to_dict()` on a `BaseModel` instance crashes:

```
AttributeError: 'AdapterTokenStats' object has no attribute 'to_dict'
```

### Fix Pattern

```python
# Before (FAILS on Pydantic v2 BaseModel):
result_data = {
    "token_stats": result.token_stats.to_dict(),  # ❌
}

# After (WORKS):
result_data = {
    "token_stats": result.token_stats.model_dump(),  # ✅
}
```

### Audit Workflow

```bash
# 1. Find all .to_dict() calls
grep -r "\.to_dict()" src/

# 2. For each hit, check if the class inherits from BaseModel
grep -B 5 "class.*BaseModel" src/

# 3. Replace only Pydantic model calls; leave dataclass .to_dict() untouched
```

Dataclasses with a custom `.to_dict()` method are **fine** — only replace calls on Pydantic `BaseModel` subclasses.

### Verification

```bash
# Find remaining .to_dict() on Pydantic models
rg "\.to_dict\(\)" src/ | while read line; do echo "$line"; done

# Run the previously-crashing script
python scripts/run_e2e_experiment.py
```

### Key Rules

1. **Always use `.model_dump()`** for Pydantic v2 BaseModel serialization.
2. **Selective replacement**: Only replace `.to_dict()` on Pydantic models, not dataclasses.
3. **Audit the whole codebase**: One missed call causes a runtime crash.
4. **Ruff/mypy can catch these** if properly configured — add to pre-commit.

### Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #136 — E2E runner crash fix | AttributeError on AdapterTokenStats |

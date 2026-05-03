---
name: type-alias-consolidation
description: "Use when: (1) multiple modules define TypeName = DomainVariant aliases causing naming confusion and you need to remove redundant type aliases that shadow domain-specific variant names; (2) applying the Pydantic inheritance pattern to metrics/judgment/cost types (MetricsInfo, JudgmentInfo) or other evaluation data types; (3) a Pydantic base class lacks frozen=True while its sibling base types all use ConfigDict(frozen=True) and you need an immutability consistency audit."
category: architecture
date: 2026-02-15
version: 3.0.0
user-invocable: false
tags: [refactoring, type-consolidation, python, architecture, pydantic, frozen, immutability]
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

**Absorbed**: pydantic-type-consolidation-metrics-judgment, pydantic-frozen-consistency on 2026-05-03

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

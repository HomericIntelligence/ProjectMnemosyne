# Pydantic Type Consolidation — MetricsInfo & JudgmentInfo

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-19 |
| **Objective** | Apply Pydantic inheritance hierarchy to MetricsInfo, JudgmentInfo, and deprecate BaseRunMetrics dataclass |
| **Outcome** | ✅ Successfully consolidated MetricsInfo and JudgmentInfo with full backward compatibility |
| **Issue** | #729 |
| **PR** | #788 |
| **Pattern** | Second application of pydantic-type-consolidation from #658 |
| **Follow-up from** | #658 (ExecutionInfo consolidation) |

## When to Use This Skill

This is the **second application** of the `pydantic-type-consolidation` pattern.
See that skill for the foundational pattern. Use this skill when:

- The type being consolidated holds **metrics/cost data** (tokens, cost_usd)
- The type being consolidated holds **judgment/grading data** (passed, impl_rate)
- A legacy dataclass has **no base class** and no downstream inheritance yet
- The type exists only in one module (reporting) with no reuse — time to extract base

**Trigger phrases**:

- "apply same consolidation pattern to [Type]"
- "MetricsInfo needs a base class"
- "JudgmentInfo variants across modules"
- "follow the pydantic-type-consolidation skill for [Type]"

## Key Differences from ExecutionInfo Pattern (#658)

| Aspect | ExecutionInfo (#658) | MetricsInfo/JudgmentInfo (#729) |
|--------|---------------------|---------------------------------|
| Starting variants | 3 definitions (executor, reporting, core dataclass) | 1 definition each (reporting only) |
| Discovery scope | Found duplicates via grep | No duplicates — preemptive extraction |
| Field defaults | `duration_seconds=0.0`, `timed_out=False` | `cost_usd=0.0`, `impl_rate=0.0` |
| Required base fields | `exit_code` (always present) | `tokens_input/output`, `passed` |
| Subtype additions | `status` (reporting), `container_id` etc (executor) | `api_calls` (reporting), `letter_grade` (reporting) |

## Verified Workflow

### 1. Identify the Pattern Match

```bash
# Check if types already have a base class
grep -n "class MetricsInfo\|class JudgmentInfo" scylla/reporting/result.py
# Result: both inherit from BaseModel directly — consolidation candidate
```

### 2. Design Base Fields

For **MetricsInfoBase** — core token/cost concepts:

- `tokens_input: int = Field(...)` — always required
- `tokens_output: int = Field(...)` — always required
- `cost_usd: float = Field(default=0.0)` — optional (may not be known yet)

For **JudgmentInfoBase** — core judgment concepts:

- `passed: bool = Field(...)` — always required
- `impl_rate: float = Field(default=0.0)` — optional (may not be computed)

### 3. Add Base Types to `scylla/core/results.py`

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

**Placement**: After `ExecutionInfoBase`, before the `@dataclass` legacy types.

### 4. Deprecate the Legacy Dataclass

```python
@dataclass
class BaseRunMetrics:
    """Base metrics shared across run result types.

    .. deprecated::
        Use MetricsInfoBase (Pydantic model) instead. This dataclass is kept
        for backward compatibility only. New code should use MetricsInfoBase
        and its domain-specific subtypes (MetricsInfo in reporting/result.py).

    For the new Pydantic-based hierarchy, see:
    - MetricsInfoBase (this module) - Base Pydantic model
    - MetricsInfo (reporting/result.py) - Result persistence with api_calls
    """

    tokens_input: int
    tokens_output: int
    cost_usd: float
```

### 5. Update Domain Subtypes in `reporting/result.py`

```python
# Before:
from scylla.core.results import ExecutionInfoBase, RunResultBase

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
from scylla.core.results import ExecutionInfoBase, JudgmentInfoBase, MetricsInfoBase, RunResultBase

class MetricsInfo(MetricsInfoBase):
    """Inherits tokens_input, tokens_output, cost_usd from MetricsInfoBase."""
    api_calls: int = Field(..., description="Number of API calls")

class JudgmentInfo(JudgmentInfoBase):
    """Inherits passed, impl_rate from JudgmentInfoBase."""
    letter_grade: str = Field(..., description="Letter grade")
```

**Key**: Remove the redefined fields from the subtype — they are inherited.

### 6. Export from `scylla/core/__init__.py`

```python
from scylla.core.results import (
    BaseExecutionInfo,
    BaseRunMetrics,
    ExecutionInfoBase,
    JudgmentInfoBase,    # New
    MetricsInfoBase,     # New
)

__all__ = [
    "BaseExecutionInfo",
    "BaseRunMetrics",
    "ExecutionInfoBase",
    "JudgmentInfoBase",  # New
    "MetricsInfoBase",   # New
]
```

### 7. Update Module Docstring

Add hierarchy documentation in `scylla/core/results.py`:

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

### 8. Test Strategy

Create `tests/unit/core/test_metrics_judgment.py`:

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

## Failed Attempts

### ❌ Attempt: Keeping `cost_usd` Required in MetricsInfoBase

**What we considered**:

```python
cost_usd: float = Field(..., description="Cost in USD")  # Required
```

**Why we didn't do it**:

- `BaseRunMetrics` (legacy dataclass) had `cost_usd` as a required positional field
- But `MetricsInfoBase` is a *base* type — downstream contexts may not have cost yet
- Making it required would force `cost_usd=0.0` workarounds at every construction site

**Solution**: `cost_usd: float = Field(default=0.0, ...)` — optional with zero default.
Matches the `duration_seconds=0.0` pattern from `ExecutionInfoBase`.

### ❌ Attempt: Keeping `impl_rate` Required in JudgmentInfoBase

**What we considered**:

```python
impl_rate: float = Field(..., description="Implementation rate")  # Required
```

**Why we didn't do it**:

- In contexts where judgment only produces a pass/fail, `impl_rate` may not be computed
- The base should support minimal construction (`passed=True` is enough)

**Solution**: `impl_rate: float = Field(default=0.0, ...)`.

## Results & Parameters

### Test Coverage

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

### Verification Commands

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

### Pre-commit

```bash
pre-commit run --all-files
# All hooks pass: ruff-format, ruff-check, mypy, markdownlint, yamllint, shellcheck, etc.
```

### Files Modified

| File | Change |
|------|--------|
| `scylla/core/results.py` | Added `MetricsInfoBase`, `JudgmentInfoBase`; deprecated `BaseRunMetrics` |
| `scylla/core/__init__.py` | Exported `MetricsInfoBase`, `JudgmentInfoBase` |
| `scylla/reporting/result.py` | `MetricsInfo` → inherits `MetricsInfoBase`; `JudgmentInfo` → inherits `JudgmentInfoBase` |
| `tests/unit/core/test_metrics_judgment.py` | New (33 tests) |
| `tests/unit/core/test_results.py` | Added `TestBaseRunMetricsDeprecation` (2 tests) |

## Key Takeaways

1. **Pattern scales cleanly** — Second application of `pydantic-type-consolidation` required no new patterns
2. **Default strategy**: Required fields = always semantically meaningful; Optional+default = may not be known at construction
3. **Even single-module types benefit from extraction** — No duplicate needed; base is created proactively for future reuse
4. **Ruff formatter runs automatically** on commit — Let pre-commit fix it, then recommit (not a real failure)
5. **`BaseRunMetrics` deprecation is doc-only** — No behavior change, just a `.. deprecated::` docstring

## Related Skills

- `pydantic-type-consolidation` — Foundational pattern (ExecutionInfo, #658)
- `migrate-dataclass-to-pydantic` — General dataclass → Pydantic migration
- `type-alias-consolidation` — Managing backward-compatible aliases

## References

- Issue: <https://github.com/HomericIntelligence/ProjectScylla/issues/729>
- PR: <https://github.com/HomericIntelligence/ProjectScylla/pull/788>
- Prior application: ExecutionInfo consolidation (#658, PR #726)
- Foundational skill: `pydantic-type-consolidation`

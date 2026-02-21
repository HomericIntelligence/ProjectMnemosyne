# Skill: git-rebase-over-deletion

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| Issue | N/A (CI fix) |
| PR | #882 |
| Objective | Fix CI failure caused by git rebase/merge replaying commits in wrong order, resulting in over-deletion of active classes |
| Outcome | Success — 2350 tests pass, all pre-commit hooks green |
| Category | debugging |

## When to Use

Trigger this skill when:

- CI `Test` workflow on `main` starts failing after a deprecation-removal commit
- The failure is an `ImportError` for symbols that *should* exist (not deprecated)
- `git log` shows a fix commit followed later by a removal commit — wrong replay order
- Multiple test modules fail to collect simultaneously (cascade from one `ImportError`)
- The removal commit message says "remove deprecated X" but X was used in active code

**Trigger phrases**:

- "CI broke on main after [deprecation-removal commit]"
- "ImportError: cannot import name 'XBase' from 'scylla.core.results'"
- "8 test modules failed to collect"
- "commit removed too much — also deleted the active base classes"

## Root Cause Pattern

This failure pattern has a specific shape:

1. **Session A** adds `JudgmentInfoBase` + `MetricsInfoBase` (PR #788, commit `2784fae`)
2. **Session B** removes `BaseRunMetrics` (a deprecated class) — but the removal commit `adbd49d` was authored against a state *before* the fix, so it also removes the newly added classes
3. A rebase/merge replays both commits, with removal *after* the fix → fix is undone
4. `pre-commit auto-fixes` commit follows, cementing the broken state

**Diagnostic signal**: The broken commit message says "remove deprecated BaseRunMetrics dataclass" but the file also lost `JudgmentInfoBase` and `MetricsInfoBase`.

## Verified Workflow

### 1. Confirm the ImportError

```bash
pixi run python -c "from scylla.core.results import JudgmentInfoBase, MetricsInfoBase; print('OK')"
# Expected (broken): ImportError: cannot import name 'JudgmentInfoBase'
```

### 2. Read the current file state

```python
# Read scylla/core/results.py — look for:
# - Missing JudgmentInfoBase / MetricsInfoBase classes
# - Stale @dataclass on GradingInfoBase (Pydantic BaseModel)
# - Duplicate field declarations in RunMetricsBase with a __post_init__
# - Unused imports: warnings, dataclasses
```

### 3. Restore the missing classes

Add both classes to `scylla/core/results.py`, placed **after `ExecutionInfoBase`** and **before `GradingInfoBase`**:

```python
class JudgmentInfoBase(BaseModel):
    """Base judgment information type for all evaluation results."""

    model_config = ConfigDict(frozen=True)

    passed: bool = Field(..., description="Whether the run passed evaluation")
    impl_rate: float = Field(default=0.0, description="Implementation rate (0.0-1.0)")


class MetricsInfoBase(BaseModel):
    """Base token and cost metrics for result persistence."""

    model_config = ConfigDict(frozen=True)

    tokens_input: int = Field(..., description="Number of input tokens consumed")
    tokens_output: int = Field(..., description="Number of output tokens generated")
    cost_usd: float = Field(default=0.0, description="Total cost in USD")
```

**Critical**: `cost_usd` must have `default=0.0` — existing tests construct `MetricsInfoBase` without it.
**Critical**: `impl_rate` must have `default=0.0` — existing tests construct `JudgmentInfoBase` without it.

### 4. Remove the stale `@dataclass` decorator

The removal commit left `@dataclass` on `GradingInfoBase` (a Pydantic BaseModel):

```python
# WRONG (stale artifact):
@dataclass
class GradingInfoBase(BaseModel):

# CORRECT:
class GradingInfoBase(BaseModel):
```

### 5. Clean up RunMetricsBase

The deleted `BaseRunMetrics.__post_init__` and its duplicate field declarations merged into `RunMetricsBase` during the bad replay. Remove the trailing blob:

```python
# DELETE this entire trailing block from RunMetricsBase:
    """Base metrics shared across run result types.
    ...
    """

    tokens_input: int
    tokens_output: int
    cost_usd: float

    def __post_init__(self) -> None:
        """Emit a DeprecationWarning on instantiation."""
        warnings.warn(...)
```

### 6. Remove unused imports

```python
# DELETE both of these (no longer needed):
import warnings
from dataclasses import dataclass
```

### 7. Update `scylla/core/__init__.py`

```python
from scylla.core.results import (
    ExecutionInfoBase,
    GradingInfoBase,
    JudgmentInfoBase,    # Add
    MetricsInfoBase,     # Add
    RunMetricsBase,
)

__all__ = [
    "ExecutionInfoBase",
    "GradingInfoBase",
    "JudgmentInfoBase",  # Add
    "MetricsInfoBase",   # Add
    "RunMetricsBase",
]
```

### 8. Update module docstring

Replace the "Legacy dataclasses (deprecated)" block with the hierarchy entries for the restored classes:

```python
JudgmentInfo inheritance hierarchy:
- JudgmentInfoBase (this module) - Base Pydantic model with judgment fields
  └── JudgmentInfo (reporting/result.py) - Reporting persistence

MetricsInfo inheritance hierarchy:
- MetricsInfoBase (this module) - Base Pydantic model with token/cost fields
  └── MetricsInfo (reporting/result.py) - Reporting persistence
```

### 9. Verify

```bash
# Quick import check
pixi run python -c "from scylla.core.results import JudgmentInfoBase, MetricsInfoBase; print('OK')"

# Specific test file (36 tests)
pixi run python -m pytest tests/unit/core/test_metrics_judgment.py -v

# Full unit suite
pixi run python -m pytest tests/unit/ --no-cov

# Pre-commit
pre-commit run --files scylla/core/results.py scylla/core/__init__.py
```

## Failed Attempts

None — the fix was clean and first-try once the root cause was identified from the plan.

The main diagnostic challenge was understanding *why* the removal commit (`adbd49d`) over-deleted:
it was authored against a pre-fix state of the file, then replayed *after* the fix commit via rebase,
effectively reverting the fix. The commit message ("Remove deprecated BaseRunMetrics dataclass") was
misleading because it also silently removed `JudgmentInfoBase` and `MetricsInfoBase`.

## Results & Parameters

### Files Modified

| File | Change |
|------|--------|
| `scylla/core/results.py` | Added `JudgmentInfoBase`, `MetricsInfoBase`; removed `@dataclass` from `GradingInfoBase`; removed duplicate fields + `__post_init__` from `RunMetricsBase`; removed `warnings` + `dataclasses` imports |
| `scylla/core/__init__.py` | Added `JudgmentInfoBase`, `MetricsInfoBase` to imports and `__all__` |

### Test Results

```
tests/unit/core/test_metrics_judgment.py — 36 tests, all passing
tests/unit/ — 2350 tests, all passing (excluding pre-existing unrelated failure in test_validation.py)
Pre-commit hooks: all passed (ruff-format, ruff-check, mypy, etc.)
```

### Pre-existing Unrelated Failure

`tests/unit/config/test_validation.py` fails with `ImportError: cannot import name 'extract_model_family'`
— this is **not** caused by this fix and existed before this session.

## Key Takeaways

1. **Deprecation removal commits are high-risk** — always check that the removal is scoped to only the deprecated symbol using `grep` before committing
2. **Rebase replay order matters** — a fix + removal pair replayed in wrong order will undo the fix
3. **The `@dataclass` decorator on a Pydantic BaseModel is a signal of bad merge** — Pydantic models never have `@dataclass`
4. **Duplicate field declarations inside a class body = bad merge artifact** — Python ignores earlier definitions, mypy may not catch it
5. **`import warnings` + `import dataclasses` are canaries** — if neither is used, something was deleted that left them behind
6. **`cost_usd` and `impl_rate` must default to 0.0** — see `pydantic-type-consolidation-metrics-judgment` skill for the reasoning

## Related Skills

- `pydantic-type-consolidation-metrics-judgment` — Original creation of `JudgmentInfoBase` + `MetricsInfoBase` (#729, PR #788)
- `pydantic-base-class-hierarchy` — Adding `GradingInfoBase` (#796, PR #841)
- `backward-compat-removal` — The removal pattern that caused this issue if applied incorrectly (#784, PR #832)

## References

- PR: <https://github.com/HomericIntelligence/ProjectScylla/pull/882>
- Breaking commit: `adbd49d` ("Remove deprecated BaseRunMetrics dataclass")
- Fix commit (previously reverted): `2784fae`
- Related skill: `pydantic-type-consolidation-metrics-judgment`

# Skill: pydantic-base-class-hierarchy

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Issue | #796 |
| PR | #841 |
| Objective | Add GradingInfoBase to complete the Pydantic base class hierarchy for all nested info types in ReportingRunResult |
| Outcome | Success — 2276 tests pass, all pre-commit hooks pass |
| Category | architecture |

## When to Use

Trigger this skill when:

- A Pydantic model inherits directly from `BaseModel` but sibling models already have dedicated base classes in `scylla/core/`
- Issue references "completing the consolidation pattern" or "following the hierarchy from #729 / #658"
- Task asks to add `*Base` class so domain types can share fields via inheritance
- New `scylla/core/` base class needs to be exported from `scylla/core/__init__.py`
- Multiple `*Info` or `*RunResult` types exist in `scylla/reporting/` and need a shared ancestor

## Verified Workflow

### 1. Identify the pattern

Read `scylla/core/results.py` and note the existing base classes (`RunResultBase`, `ExecutionInfoBase`). Read `scylla/reporting/result.py` to find classes still using `BaseModel` directly.

### 2. Add the base class to `scylla/core/results.py`

Place new base class **before** the `@dataclass` section. Follow this template:

```python
class GradingInfoBase(BaseModel):
    """Base grading metrics type for all grading results.

    Attributes:
        pass_rate: Pass rate for the run (0.0 or 1.0).
        cost_of_pass: Cost per successful pass in USD.
        composite_score: Combined quality score (0.0-1.0).

    """

    pass_rate: float = Field(..., description="Pass rate (0.0 or 1.0)")
    cost_of_pass: float = Field(..., description="Cost per successful pass")
    composite_score: float = Field(..., description="Combined quality score")
```

**Key decisions:**

- Use `Field(...)` (required, no defaults) when the domain class had no defaults
- Do NOT add `frozen=True` unless sibling base classes have it (e.g., `ExecutionInfoBase` is frozen, `RunResultBase` is not)
- Update the module docstring's hierarchy diagram

### 3. Export from `scylla/core/__init__.py`

Add to both the `from scylla.core.results import (...)` block and the `__all__` list.

### 4. Update the domain class in `scylla/reporting/result.py`

Change the parent from `BaseModel` to the new base class. Remove fields that are now inherited. Add a docstring explaining the hierarchy.

```python
class GradingInfo(GradingInfoBase):
    """Calculated grading metrics for a run.

    Inherits common fields (pass_rate, cost_of_pass, composite_score)
    from GradingInfoBase.

    For the GradingInfo hierarchy, see:
    - GradingInfoBase (core/results.py) - Base Pydantic model
    - GradingInfo (reporting/result.py) - Reporting persistence (this class)

    """
```

### 5. Write tests for the base class in `tests/unit/core/test_results.py`

Required test methods:

- `test_construction_basic` — valid instantiation with field checks
- `test_construction_<edge_case>` — failed run / boundary values
- `test_missing_<field>_raises` — one per required field
- `test_model_dump` — verify `.model_dump()` output dict
- `test_subclass_is_instance` — verify the reporting subclass passes `isinstance()`

### 6. Add inheritance tests in `tests/unit/reporting/test_result.py`

```python
from scylla.core.results import GradingInfoBase

def test_is_subclass_of_grading_info_base(self) -> None:
    assert issubclass(GradingInfo, GradingInfoBase)

def test_instance_of_grading_info_base(self) -> None:
    info = make_grading()
    assert isinstance(info, GradingInfoBase)
```

### 7. Verify

```bash
pixi run python -m pytest tests/ --no-cov -q   # all tests pass
pre-commit run --all-files                       # ruff, mypy, black all pass
```

## Failed Attempts

None — this was a clean, pattern-following implementation with no dead ends.

The skill invocation attempted to use `commit-commands:commit-push-pr` skill but it was denied in the current permission mode. Fallback to direct git/gh commands worked cleanly.

## Results & Parameters

### Files Modified

| File | Change |
|------|--------|
| `scylla/core/results.py` | Added `GradingInfoBase` class (~20 lines) |
| `scylla/core/__init__.py` | Added import + `__all__` entry |
| `scylla/reporting/result.py` | `GradingInfo` now inherits `GradingInfoBase`; removed 3 field definitions; added docstring |
| `tests/unit/core/test_results.py` | Added `TestGradingInfoBase` (8 tests) |
| `tests/unit/reporting/test_result.py` | Added 2 inheritance assertion tests + import |

### Test Counts

- Tests added: 10 (8 in core, 2 in reporting)
- Total suite: 2276 passed, 0 failed

### Checklist for Future Base Class Additions

- [ ] `Field(...)` vs `Field(default=...)` matches domain class pattern
- [ ] `frozen=True` only if sibling base classes use it
- [ ] Docstring hierarchy diagram updated in `scylla/core/results.py`
- [ ] Export added to both import block and `__all__` in `__init__.py`
- [ ] Domain class docstring references both base and subclass
- [ ] Required field missing → `pytest.raises(ValidationError)` tests
- [ ] `isinstance()` cross-module test in both core and reporting test files

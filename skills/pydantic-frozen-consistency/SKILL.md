# Skill: pydantic-frozen-consistency

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Issue | #799 |
| PR | #846 |
| Objective | Add `frozen=True` to `RunResultBase` to match immutability pattern of sibling base types |
| Outcome | Success — 2272 tests pass, coverage 73.57% |
| Category | testing |

## When to Use

Trigger this skill when you see:

- A Pydantic `BaseModel` subclass with `ConfigDict()` or no `model_config` while sibling base classes use `ConfigDict(frozen=True)`
- Issue asking to "evaluate whether X should also be frozen, or document why it is intentionally mutable"
- Pydantic model immutability consistency audit
- `model_config = ConfigDict()` with no arguments on a result/info base class
- Subtypes that override `model_config` dropping inherited settings (e.g., `arbitrary_types_allowed=True` without `frozen=True`)

## Verified Workflow

### 1. Confirm no post-construction mutations exist

Before adding `frozen=True`, search for field assignments on instances of the target class and all its subtypes:

```bash
# Find all subclasses
grep -rn "class.*TargetBase\|TargetBase" scylla/ --include="*.py" | grep "class "

# Check for post-construction mutations on those types
grep -rn "\.(field_name)\s*=" scylla/ --include="*.py"
```

**Key insight**: Mutation sites may exist in the codebase on Pydantic models with similar field names (e.g., `cost_usd`, `duration_seconds`) but on *different* classes (dataclasses, other Pydantic models). Always verify the type of the mutated object before concluding that `frozen=True` is incompatible.

### 2. Update the base class

```python
# Before
model_config = ConfigDict()

# After
model_config = ConfigDict(frozen=True)
```

### 3. Update subtypes that override model_config

Pydantic subclasses that define their own `model_config` **do not inherit** the parent's config — they replace it. Find all subtypes that override `model_config`:

```bash
grep -n "model_config" scylla/path/to/subtype.py
```

For each subtype with its own `model_config`, explicitly include `frozen=True`:

```python
# Before (in subtype)
model_config = ConfigDict(arbitrary_types_allowed=True)

# After
model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
```

Subtypes that do **not** define `model_config` automatically inherit `frozen=True` from the base — no change needed.

### 4. Add immutability tests

Add a test class alongside existing tests for the base type:

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

### 5. Run tests

```bash
pixi run python -m pytest tests/ -v
```

## Failed Attempts

None — the pattern was straightforward once the mutation sites were verified to not affect `RunResultBase` subtypes.

The apparent mutation sites in the codebase (`scylla/executor/capture.py`, `scylla/cli/progress.py`, `scylla/e2e/command_logger.py`) mutate `ExecutionMetrics`, `RunProgress` (a dataclass), and `CommandLog` respectively — not any `RunResultBase` subtype. Always check the type before concluding mutations block `frozen=True`.

## Key Insight: Pydantic Config Inheritance

When a subclass defines its own `model_config`, it **replaces** (not merges with) the parent's config. This means:

- Subtypes with NO `model_config` → inherit `frozen=True` automatically ✓
- Subtypes WITH their own `model_config` → must explicitly repeat `frozen=True` ✗ if omitted

In this project, `E2ERunResult` was the only subtype that needed updating (it had `ConfigDict(arbitrary_types_allowed=True)`).

## Results

| File | Change |
|------|--------|
| `scylla/core/results.py:53` | `ConfigDict()` → `ConfigDict(frozen=True)` |
| `scylla/e2e/models.py:292` | `ConfigDict(arbitrary_types_allowed=True)` → `ConfigDict(frozen=True, arbitrary_types_allowed=True)` |
| `tests/unit/core/test_results.py` | Added `TestRunResultBase` with 6 tests |

Tests: 2272 passed, coverage 73.57%

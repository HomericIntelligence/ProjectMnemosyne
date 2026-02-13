# Skill: Migrate Dataclasses to Pydantic BaseModel

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-13 |
| **Objective** | Migrate all Python dataclasses in scylla/e2e/ to Pydantic BaseModel |
| **Outcome** | ✅ Successfully migrated 24 classes across 8 files, all tests passing |
| **Files Modified** | 10 files (8 source, 1 test, 1 checkpoint fix) |
| **Tests** | 2,044 tests pass |

## When to Use

Use this skill when you need to:

- Migrate Python `@dataclass` classes to Pydantic `BaseModel`
- Add runtime validation to existing dataclasses
- Standardize data models across a codebase
- Enable better JSON serialization with type coercion
- Resolve technical debt from mixed dataclass/Pydantic usage

**Trigger conditions:**
- Code review identifies dataclass usage in modules that use Pydantic
- Need for runtime validation on existing data models
- Type checking errors with dataclass serialization
- Following up on partial migrations (like commit 086e0b4)

## Verified Workflow

### 1. Identify Classes to Migrate

```bash
# Find all dataclasses in target directory
grep -r "@dataclass" scylla/e2e/ --include="*.py"
```

**Expected count:** 24 classes across 8 files

### 2. Migration Pattern (Per File)

#### Step A: Update Imports

```python
# Before
from dataclasses import dataclass, field

# After
from pydantic import BaseModel, ConfigDict, Field
```

#### Step B: Convert Class Declaration

```python
# Before
@dataclass
class TokenStats:
    input_tokens: int = 0
    output_tokens: int = 0
    items: list[str] = field(default_factory=list)

# After
class TokenStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    items: list[str] = Field(default_factory=list)
```

#### Step C: Add Model Configuration (if needed)

Add `ConfigDict(arbitrary_types_allowed=True)` for classes with:
- `Path` fields
- Enum fields (like `TierID`)
- Other non-standard types

```python
class ExperimentConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    experiment_id: str
    task_prompt_file: Path  # Requires arbitrary_types_allowed
    tiers_to_run: list[TierID] = Field(default_factory=list)
```

#### Step D: Convert Special Methods

**Pattern 1: `__post_init__` with validation**

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

**Pattern 2: `__post_init__` for default initialization**

```python
# Before
@dataclass
class RerunJudgeStats:
    per_slot_stats: dict[int, dict[str, int]] = None

    def __post_init__(self):
        if self.per_slot_stats is None:
            self.per_slot_stats = {}

# After - Just use Field(default_factory=dict)
class RerunJudgeStats(BaseModel):
    per_slot_stats: dict[int, dict[str, int]] = Field(default_factory=dict)
```

#### Step E: Handle Forward References

If you get `class-not-fully-defined` error:

```python
# In scylla/e2e/models.py
class SubTestResult(BaseModel):
    # Use string annotation for forward reference
    rate_limit_info: "RateLimitInfo | None" = None

# At end of file, import and rebuild
from scylla.e2e.rate_limit import RateLimitInfo  # noqa: E402
SubTestResult.model_rebuild()
```

### 3. Fix Common Issues

#### Issue A: Path Serialization in JSON

**Problem:** `model_dump()` returns `Path` objects as-is, not strings

```python
# ❌ This fails with TypeError: Object of type PosixPath is not JSON serializable
config_dict = config.model_dump()
json.dumps(config_dict, sort_keys=True)

# ✅ Use mode="json" to serialize Path → str
config_dict = config.model_dump(mode="json")
json.dumps(config_dict, sort_keys=True)
```

#### Issue B: Keep Custom `to_dict()` Methods

Pydantic's `model_dump()` doesn't handle custom serialization (Enum→value, Path→str). Keep existing `to_dict()` methods:

```python
class SubTestConfig(BaseModel):
    tier_id: TierID
    claude_md_path: Path | None

    # Keep this for custom serialization
    def to_dict(self) -> dict[str, Any]:
        return {
            "tier_id": self.tier_id.value,  # Enum → str
            "claude_md_path": str(self.claude_md_path) if self.claude_md_path else None,
        }
```

#### Issue C: Test Failures with Positional Arguments

**Problem:** Pydantic requires keyword arguments

```python
# ❌ This fails with Pydantic
vote = JudgeVote("01", 0.85, 0.9, "Good")

# ✅ Use keyword arguments
vote = JudgeVote(subtest_id="01", score=0.85, confidence=0.9, reasoning="Good")
```

### 4. Verification

```bash
# Run unit tests for migrated module
pixi run python -m pytest tests/unit/e2e/ -v

# Run full test suite
pixi run python -m pytest tests/ -v

# Test both serialization methods work
python -c "from scylla.e2e.models import ExperimentConfig; from pathlib import Path; c = ExperimentConfig(experiment_id='test', task_repo='r', task_commit='c', task_prompt_file=Path('p'), language='python'); print('model_dump:', c.model_dump()); print('to_dict:', c.to_dict())"

# Run linters
pre-commit run --all-files
```

## Failed Attempts

### ❌ Attempt 1: Import RateLimitInfo under TYPE_CHECKING

**What was tried:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scylla.e2e.rate_limit import RateLimitInfo

class SubTestResult(BaseModel):
    rate_limit_info: RateLimitInfo | None = None
```

**Why it failed:**
```
pydantic.errors.PydanticUserError: `SubTestResult` is not fully defined;
you should define `RateLimitInfo`, then call `SubTestResult.model_rebuild()`.
```

Pydantic needs the actual type at runtime for validation, not just for type checking.

**Solution:** Use string annotation + import at module end + `model_rebuild()`:
```python
class SubTestResult(BaseModel):
    rate_limit_info: "RateLimitInfo | None" = None

# At end of file
from scylla.e2e.rate_limit import RateLimitInfo  # noqa: E402
SubTestResult.model_rebuild()
```

### ❌ Attempt 2: Use model_dump() for JSON Serialization Without mode="json"

**What was tried:**
```python
config_dict = config.model_dump()
json.dumps(config_dict, sort_keys=True)
```

**Why it failed:**
```
TypeError: Object of type PosixPath is not JSON serializable
when serializing dict item 'task_prompt_file'
```

Pydantic's default `model_dump()` returns Python objects as-is. Path objects aren't JSON serializable.

**Solution:** Use `mode="json"` parameter:
```python
config_dict = config.model_dump(mode="json")  # Converts Path → str
json.dumps(config_dict, sort_keys=True)
```

### ❌ Attempt 3: Forgot to Remove @dataclass Decorator

**What was tried:**
```python
@dataclass
class _JudgeSlotResult(BaseModel):
    slot: JudgeSlotToRerun
    success: bool
```

**Why it failed:**
```
NameError: name 'dataclass' is not defined
```

After removing the import, the decorator was still present.

**Solution:** Remove all `@dataclass` decorators when converting to `BaseModel`.

## Results & Parameters

### Migration Statistics

| Metric | Value |
|--------|-------|
| **Classes migrated** | 24 |
| **Files modified** | 10 |
| **Lines changed** | +94, -80 |
| **Tests passing** | 2,044 (100%) |
| **E2E tests passing** | 430 (100%) |

### Files Modified

**Source files (8):**
- `scylla/e2e/models.py` (12 classes)
- `scylla/e2e/rate_limit.py` (1 class)
- `scylla/e2e/judge_selection.py` (2 classes)
- `scylla/e2e/llm_judge.py` (2 classes)
- `scylla/e2e/rerun.py` (2 classes)
- `scylla/e2e/rerun_judges.py` (3 classes)
- `scylla/e2e/regenerate.py` (1 class)
- `scylla/e2e/rerun_base.py` (1 class)

**Workaround reverted (1):**
- `scylla/e2e/checkpoint.py:294` - `to_dict()` → `model_dump(mode="json")`

**Test files (1):**
- `tests/unit/e2e/test_judge_selection.py` - positional → keyword arguments

### Migration Checklist

Use this checklist for each file:

- [ ] Update imports (`dataclass` → `BaseModel`, `field` → `Field`)
- [ ] Remove `@dataclass` decorators
- [ ] Convert class to inherit from `BaseModel`
- [ ] Convert `field(default_factory=...)` → `Field(default_factory=...)`
- [ ] Add `ConfigDict(arbitrary_types_allowed=True)` if needed (Path/Enum fields)
- [ ] Convert `__post_init__` to `@model_validator` or `Field(default_factory=...)`
- [ ] Handle forward references with string annotations + `model_rebuild()`
- [ ] Keep custom `to_dict()`, `from_dict()`, `@property` methods
- [ ] Run tests: `pixi run python -m pytest tests/unit/e2e/ -v`
- [ ] Run linters: `pre-commit run --all-files`

### Key Patterns Preserved

These patterns work seamlessly with Pydantic:

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

# ✅ Custom serialization methods work as-is
def to_dict(self) -> dict[str, Any]:
    return {
        "tier_id": self.tier_id.value,  # Custom Enum → str
        "path": str(self.path) if self.path else None,  # Custom Path → str
    }
```

## References

- **PR:** https://github.com/HomericIntelligence/ProjectScylla/pull/592
- **Commit:** a06e434 "refactor(e2e): Migrate all dataclasses to Pydantic BaseModel"
- **Previous migration:** 086e0b4 (migrated 19 dataclasses, left e2e/ untouched)
- **Pydantic docs:** https://docs.pydantic.dev/latest/
- **Forward references:** https://docs.pydantic.dev/latest/concepts/postponed_annotations/

## Success Criteria

- [x] All 24 dataclasses migrated to Pydantic BaseModel
- [x] All tests pass (2,044 tests)
- [x] Pre-commit hooks pass
- [x] Both `model_dump()` and `to_dict()` work correctly
- [x] Checkpoint workaround reverted
- [x] No breaking changes to public API
- [x] Forward references resolved correctly
- [x] Custom methods preserved (properties, dunder methods, class methods)

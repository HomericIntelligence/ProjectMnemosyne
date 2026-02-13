# Migration Notes: Dataclass to Pydantic BaseModel

## Session Context

**Date:** 2026-02-13
**Task:** Complete migration of all e2e dataclasses to Pydantic BaseModel
**Context:** Following up on commit 086e0b4 which migrated 19 dataclasses but left scylla/e2e/ untouched

## Detailed Timeline

### Discovery Phase

1. **Initial scan:** Found 24 dataclasses across 8 files in scylla/e2e/
2. **Pattern analysis:** Identified migration patterns from commit 086e0b4
3. **Complexity assessment:**
   - Simple classes: 14 (just field conversions)
   - Medium complexity: 8 (with `__post_init__` or custom methods)
   - High complexity: 2 (forward references, post-construction mutation)

### Migration Execution

**Order of migration:**
1. `scylla/e2e/models.py` - Largest file, all others depend on these types
2. `scylla/e2e/rate_limit.py` - Referenced by `SubTestResult`
3. Remaining files in parallel - `judge_selection.py`, `llm_judge.py`, `rerun*.py`
4. Checkpoint workaround revert - `checkpoint.py:294`
5. Test fixes - `test_judge_selection.py`

### Technical Challenges

#### Challenge 1: Forward Reference Resolution

**Problem:** `SubTestResult` in models.py references `RateLimitInfo` from rate_limit.py, but rate_limit.py doesn't import models.py (no circular import).

**Initial approach (failed):**
```python
if TYPE_CHECKING:
    from scylla.e2e.rate_limit import RateLimitInfo
```

**Error:**
```
pydantic.errors.PydanticUserError: `SubTestResult` is not fully defined;
you should define `RateLimitInfo`, then call `SubTestResult.model_rebuild()`.
```

**Solution:**
```python
# In class definition
rate_limit_info: "RateLimitInfo | None" = None

# At end of file
from scylla.e2e.rate_limit import RateLimitInfo  # noqa: E402
SubTestResult.model_rebuild()
```

**Why it works:** String annotations delay type resolution, and `model_rebuild()` revalidates after the import.

#### Challenge 2: JSON Serialization of Path Objects

**Problem:** Computing config hash for checkpointing requires JSON serialization, but `Path` objects aren't JSON serializable.

**Test failure:**
```
TypeError: Object of type PosixPath is not JSON serializable
when serializing dict item 'task_prompt_file'
```

**Solution:** Use `model_dump(mode="json")` which converts `Path → str`, `Enum → value`, etc.

```python
# Before (workaround with to_dict)
config_dict = config.to_dict()

# After (proper Pydantic usage)
config_dict = config.model_dump(mode="json")
```

#### Challenge 3: Test Compatibility

**Problem:** Test code using positional arguments fails with Pydantic.

**Error:**
```
TypeError: BaseModel.__init__() takes 1 positional argument but 5 were given
```

**Example:**
```python
# ❌ Fails
vote = JudgeVote("01", 0.85, 0.9, "Good")

# ✅ Works
vote = JudgeVote(subtest_id="01", score=0.85, confidence=0.9, reasoning="Good")
```

**Solution:** Convert all positional arguments to keyword arguments in tests.

### Migration Patterns Discovered

#### Pattern 1: Simple Dataclass

```python
# Before
@dataclass
class TokenStats:
    input_tokens: int = 0
    output_tokens: int = 0

# After
class TokenStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
```

**Effort:** Low (automated find-replace)

#### Pattern 2: Dataclass with default_factory

```python
# Before
@dataclass
class SubTestConfig:
    resources: dict[str, Any] = field(default_factory=dict)
    inherit_best_from: list[TierID] = field(default_factory=list)

# After
class SubTestConfig(BaseModel):
    resources: dict[str, Any] = Field(default_factory=dict)
    inherit_best_from: list[TierID] = Field(default_factory=list)
```

**Effort:** Low (find-replace `field` → `Field`)

#### Pattern 3: Dataclass with Path/Enum Fields

```python
# Before
@dataclass
class ExperimentConfig:
    task_prompt_file: Path
    tiers_to_run: list[TierID] = field(default_factory=lambda: list(TierID))

# After
class ExperimentConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_prompt_file: Path
    tiers_to_run: list[TierID] = Field(default_factory=lambda: list(TierID))
```

**Effort:** Medium (need to identify which classes need `arbitrary_types_allowed`)

#### Pattern 4: Dataclass with Validation __post_init__

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

**Effort:** Medium (requires understanding validation logic)

#### Pattern 5: Dataclass with Initialization __post_init__

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

**Effort:** Low (can replace with `Field(default_factory=...)`)

### Custom Methods Compatibility

All custom methods work seamlessly with Pydantic:

**✅ Properties:**
```python
@property
def total_tokens(self) -> int:
    return self.input_tokens + self.output_tokens
```

**✅ Dunder methods:**
```python
def __add__(self, other: TokenStats) -> TokenStats:
    return TokenStats(...)
```

**✅ Class methods:**
```python
@classmethod
def load(cls, path: Path) -> ExperimentConfig:
    with open(path) as f:
        data = json.load(f)
    return cls(**data)
```

**✅ Instance methods:**
```python
def save(self, path: Path) -> None:
    path.write_text(json.dumps(self.to_dict(), indent=2))
```

**✅ Custom serialization:**
```python
def to_dict(self) -> dict[str, Any]:
    return {
        "tier_id": self.tier_id.value,  # Enum → str
        "path": str(self.path) if self.path else None,  # Path → str
    }
```

### Test Results

**Before migration:**
- 2,044 tests pass

**After migration:**
- 2,044 tests pass (100% retention)
- 430 e2e tests pass specifically
- Pre-commit hooks pass (black, ruff, mypy)

### Performance Impact

No measurable performance impact observed:
- Test suite runtime: ~38s (same as before)
- E2E test suite runtime: ~10s (same as before)

### Code Quality Metrics

**Lines changed:** +94, -80 (net: +14 lines)
- Added: import statements, model_config declarations, model_validator decorators
- Removed: dataclass decorators, redundant __post_init__ methods

**Type safety:** Improved
- Pydantic provides runtime validation
- Better error messages for type mismatches
- Automatic type coercion where appropriate

## Lessons Learned

1. **Forward references require special handling** in Pydantic - use string annotations + `model_rebuild()`
2. **Always use `mode="json"` for JSON serialization** when Path/Enum fields are present
3. **Preserve `to_dict()` methods** for custom serialization logic (Enum→value, Path→str)
4. **Test compatibility** requires keyword arguments, not positional
5. **`arbitrary_types_allowed=True`** is required for Path and custom Enum fields
6. **`__post_init__` conversion:**
   - Validation logic → `@model_validator(mode='after')`
   - Initialization logic → `Field(default_factory=...)`

## Recommendations

### For Future Migrations

1. **Start with dependency analysis:** Migrate files in dependency order to avoid forward reference issues
2. **Use incremental verification:** Run tests after each file migration
3. **Check for positional arguments:** Search test files for class instantiation patterns
4. **Keep custom serialization:** Don't blindly replace `to_dict()` with `model_dump()`
5. **Add `arbitrary_types_allowed`** proactively for classes with Path/Enum fields

### For New Code

1. **Always use Pydantic BaseModel** for new data models
2. **Use `Field()` for all defaults** with factory functions
3. **Prefer `@model_validator`** over `__post_init__` for validation
4. **Document custom serialization** if `to_dict()` differs from `model_dump()`
5. **Use `mode="json"`** when serializing for JSON/YAML output

## Raw Command Log

```bash
# Discovery
grep -r "@dataclass" scylla/e2e/ --include="*.py"

# Testing during migration
pixi run python -m pytest tests/unit/e2e/test_models.py -v
pixi run python -m pytest tests/unit/e2e/ -v
pixi run python -m pytest tests/ -v

# Verification
python -c "from scylla.e2e.models import ExperimentConfig; from pathlib import Path; c = ExperimentConfig(experiment_id='test', task_repo='r', task_commit='c', task_prompt_file=Path('p'), language='python'); print('model_dump:', c.model_dump()); print('to_dict:', c.to_dict())"

# Linting
pre-commit run --files scylla/e2e/models.py scylla/e2e/rate_limit.py ...

# Git workflow
git add scylla/e2e/*.py tests/unit/e2e/test_judge_selection.py
git commit -m "refactor(e2e): Migrate all dataclasses to Pydantic BaseModel"
git checkout -b refactor/migrate-e2e-dataclasses-to-pydantic
git push -u origin refactor/migrate-e2e-dataclasses-to-pydantic
gh pr create --title "refactor(e2e): Migrate all dataclasses to Pydantic BaseModel" --label "refactoring"
gh pr merge --auto --rebase 592
```

## Follow-up Actions

- [ ] Consider adding Pydantic validation to existing models (e.g., email format, URL validation)
- [ ] Document Pydantic usage patterns in CONTRIBUTING.md
- [ ] Add pre-commit hook to prevent new dataclass usage in favor of Pydantic
- [ ] Consider migrating remaining dataclasses in other modules (scylla/core/, scylla/metrics/)

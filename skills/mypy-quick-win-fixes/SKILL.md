# Mypy Quick-Win Fixes Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Issue** | #767 - Fix quick-win mypy errors: override, no-redef, exit-return, return-value, call-overload |
| **Objective** | Resolve 5 single-violation mypy error codes and remove them from `disable_error_code` in `pyproject.toml` |
| **Outcome** | ✅ Success — all 5 error codes removed, suppressed count reduced from 63 to 58, 2396 tests pass |
| **PR** | #946 |

## When to Use

Use this skill when:

- MYPY_KNOWN_ISSUES.md shows single-violation error codes (count = 1)
- You want to remove error codes from `disable_error_code` in `pyproject.toml`
- You need to fix specific mypy error patterns: `override`, `no-redef`, `exit-return`, `return-value`, `call-overload`
- Following a "quick-win" batch fix session as part of the mypy roadmap (see #687)

**See also**: `mypy-living-baseline` skill for the tracking infrastructure.

## Verified Workflow

### 1. Identify Actual Violations Before Touching Code

Run mypy with only the target error codes enabled to confirm the exact file/line:

```bash
pixi run python -m mypy scylla/ \
  --enable-error-code override \
  --enable-error-code no-redef \
  --enable-error-code exit-return \
  --enable-error-code return-value \
  --enable-error-code call-overload \
  2>&1 | grep "error:"
```

**Critical**: The actual violations may differ from what MYPY_KNOWN_ISSUES.md documented. Always
re-run mypy to get the ground truth before making changes.

### 2. Fix Each Error Code

#### `exit-return` — `__exit__` return type

```python
# WRONG: bool return type triggers exit-return when method always returns False
def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
    ...
    return False  # mypy: "bool" is invalid as return type for "__exit__"

# CORRECT: Use None (never suppresses exceptions) or Literal[False]
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    ...
    # Return None (False-y) to not suppress exceptions
```

#### `override` — pydantic `model_validate` incompatible override

Do NOT try to match pydantic's exact `model_validate` signature — it uses complex keyword-only
params that are hard to replicate. Instead, **rename the method** to avoid the override entirely:

```python
# WRONG: Incompatible override of pydantic BaseModel.model_validate
class MyModel(BaseModel):
    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> MyModel:  # override error
        ...

# CORRECT: Rename to a custom method name
class MyModel(BaseModel):
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MyModel:
        ...
        return super().model_validate(data)  # still delegates to pydantic
```

Update all call sites (including tests) to use `from_dict()` instead of `model_validate()`.

#### `no-redef` — import shadowing a local variable

```python
# WRONG: 'config' is already a function parameter on line 237
def my_func(config: ExperimentConfig) -> None:
    ...
    from scylla.e2e.models import config  # no-redef: "config" already defined
    print(config.language)  # actually works but is wrong/confusing

# CORRECT: Remove the erroneous import; use the parameter
def my_func(config: ExperimentConfig) -> None:
    ...
    print(config.language)  # use the parameter directly
```

#### `return-value` — bare `dict` return annotation

```python
# WRONG: bare dict is not a valid generic type annotation
def my_validator(cls, v: Any) -> dict:  # return-value warning
    return v if v else {}

# CORRECT: Specify generic parameters
def my_validator(cls, v: Any) -> dict[str, Any]:
    return v if v else {}
```

#### `call-overload` in tests — mypy `ignore_errors = true` limitation

In mypy 1.19, `ignore_errors = true` in `[[tool.mypy.overrides]]` for `tests.*` does NOT suppress
`call-overload` errors that arise from `Any`-typed dict access. Use a targeted inline ignore:

```python
# When accessing nested dict values typed as Any:
assert set(my_dict["key"]["subkey"]) == expected  # call-overload: no overload matches "object"

# CORRECT: Add targeted ignore comment
assert set(my_dict["key"]["subkey"]) == expected  # type: ignore[call-overload]
```

**Note**: Wrapping in `list()` does NOT help — `list(Any)` has the same overload problem.

### 3. Remove Error Codes from pyproject.toml

```toml
# Before
disable_error_code = [
    ...
    "override",        # 1 violation - incompatible method override
    "no-redef",        # 1 violation - name redefinition
    "exit-return",     # 1 violation - context manager __exit__ return type
    ...
    "return-value",    # 1 violation - incompatible return value type
    "call-overload",   # 1 violation - no matching overload variant
]

# After (remove the 5 lines)
disable_error_code = [
    ...
    # only remaining codes
]
```

### 4. Verify Clean Mypy

```bash
pixi run python -m mypy scylla/
# Expected: Success: no issues found in N source files
```

### 5. Run Full Pre-commit

```bash
pre-commit run --all-files
```

**Watch out**: If `pixi.lock` is modified (by running `pixi run` commands), stage it before
committing. Pre-commit stashing unstaged changes + auto-formatting conflicts will cause repeated
failures. Solution: `git add pixi.lock` before committing.

## Failed Attempts

### Matching pydantic's `model_validate` signature with `**kwargs: Any`

**Attempt**: Change subclass signature to `def model_validate(cls, data: Any, **kwargs: Any) -> MyModel:`

**Failure**: Mypy 1.19 still reports `[override]` — pydantic's base method uses keyword-only
params (declared with `*`), not `**kwargs`. The two signatures are structurally incompatible
regardless of `**kwargs`.

**Fix**: Rename the method to `from_dict()` entirely.

### Using `bool | None` as `__exit__` return type

**Attempt**: Change from `-> bool` to `-> bool | None`

**Failure**: Mypy still reports `exit-return` because the method body has `return False` which
is typed as `bool`, and mypy says `"bool" is invalid as return type for "__exit__"` when the
method always returns `False`.

**Fix**: Change return type to `None` AND replace `return False` with a comment. The `None` return
type is semantically correct — returning `None` from `__exit__` is falsy and does not suppress
exceptions, same as `return False`.

### Wrapping `set()` call in `list()` to fix `call-overload`

**Attempt**: `set(list(merged["agents"]["names"]))` — hoping `list()` would be typed as `list[Any]`

**Failure**: `list(Any)` has the same overload problem: `No overload variant of "list" matches
argument type "object"`. The root cause is that nested dict access returns `object`, not `Any`.

**Fix**: Use `# type: ignore[call-overload]` directly on the `set()` call.

### Relying on `ignore_errors = true` for tests

**Assumption**: `ignore_errors = true` in `[[tool.mypy.overrides]]` for `tests.*` would suppress
all test errors including `call-overload`.

**Failure**: Mypy 1.19 still reports `call-overload` errors from test files even with
`ignore_errors = true`. The override does not work for this error code in this version.

**Fix**: Add `# type: ignore[call-overload]` directly on the offending test line.

## Results & Parameters

```
Error codes fixed: 5 (override, no-redef, exit-return, return-value, call-overload)
Suppressed error count: 63 → 58
Files modified: 6 source files + 3 test files
Tests: 2396 passed, 74.16% coverage (≥73% threshold)
Pre-commit: all hooks pass
Mypy 1.19 (compiled: yes)
```

### Files Modified

| File | Change |
|------|--------|
| `scylla/executor/capture.py` | `__exit__` return `bool` → `None`, remove `return False` |
| `scylla/e2e/checkpoint.py` | Rename `model_validate` → `from_dict`, update internal caller |
| `scylla/e2e/models.py` | `-> dict` → `-> dict[str, Any]` on field validator |
| `scylla/e2e/regenerate.py` | Remove erroneous `from scylla.e2e.models import config` import |
| `tests/unit/e2e/test_checkpoint.py` | Update 3 call sites to `from_dict()` |
| `tests/unit/e2e/test_resume.py` | Update 1 call site to `from_dict()` |
| `tests/unit/e2e/test_tier_manager.py` | Add `# type: ignore[call-overload]` |
| `pyproject.toml` | Remove 5 error codes from `disable_error_code` |

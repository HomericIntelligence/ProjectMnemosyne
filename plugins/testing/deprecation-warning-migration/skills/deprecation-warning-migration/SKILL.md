# Skill: deprecation-warning-migration

## Overview

| Field     | Value |
|-----------|-------|
| Date      | 2026-02-19 |
| Category  | testing |
| Issue     | #728 (follow-up from #658) |
| PR        | #779 |
| Outcome   | Success — all 2206 tests passing |
| Objective | Add a runtime `DeprecationWarning` to a legacy dataclass that was superseded by a Pydantic model, track usage in CI, and document the migration timeline |

---

## When to Use

Trigger this skill when you need to:

- Deprecate a Python dataclass in favour of a Pydantic `BaseModel`
- Emit runtime `DeprecationWarning` so consumers are notified at import/instantiation time
- Track surviving usages of the deprecated class in CI without blocking the build
- Document a v-major removal timeline in a CHANGELOG

---

## Verified Workflow

### 1. Add `__post_init__` warning to the dataclass

```python
# scylla/core/results.py
import warnings
from dataclasses import dataclass

@dataclass
class BaseExecutionInfo:
    """...(deprecated docstring)..."""

    exit_code: int
    duration_seconds: float
    timed_out: bool = False

    def __post_init__(self) -> None:
        """Emit a DeprecationWarning on instantiation."""
        warnings.warn(
            "BaseExecutionInfo is deprecated and will be removed in v2.0.0. "
            "Use ExecutionInfoBase instead.",
            DeprecationWarning,
            stacklevel=2,
        )
```

Key points:

- `stacklevel=2` surfaces the caller's file/line, not the `__post_init__` itself.
- Add a one-line docstring to satisfy `ruff D105` (missing docstring in magic method).

### 2. Update existing tests with `pytest.warns`

Wrap every `DeprecatedClass(...)` instantiation in tests:

```python
import pytest

def test_still_works(self) -> None:
    with pytest.warns(DeprecationWarning, match="BaseExecutionInfo is deprecated"):
        info = BaseExecutionInfo(exit_code=0, duration_seconds=1.0)
    assert info.exit_code == 0
```

Add an explicit test asserting the warning is emitted:

```python
def test_deprecation_warning_emitted(self) -> None:
    with pytest.warns(
        DeprecationWarning,
        match="BaseExecutionInfo is deprecated and will be removed in v2.0.0",
    ):
        BaseExecutionInfo(exit_code=0, duration_seconds=1.0)
```

### 3. Add a non-blocking CI grep step

In `.github/workflows/test.yml`, **before** the `Install pixi` step (so it runs without the env):

```yaml
- name: Track deprecated BaseExecutionInfo usage
  run: |
    count=$(grep -rn "BaseExecutionInfo" . \
      --include="*.py" \
      --exclude-dir=".pixi" \
      | grep -v "scylla/core/results.py" \
      | grep -v "# deprecated" \
      | grep -v "test_results.py" \
      | wc -l)
    echo "BaseExecutionInfo usage count (excluding definition and tests): $count"
    if [ "$count" -gt "0" ]; then
      echo "::warning::Found $count usages of deprecated BaseExecutionInfo"
      grep -rn "BaseExecutionInfo" . --include="*.py" --exclude-dir=".pixi" \
        | grep -v "scylla/core/results.py" \
        | grep -v "# deprecated" \
        | grep -v "test_results.py"
    fi
```

Uses `::warning::` (not `::error::`) so CI passes even if deprecated usages remain.

### 4. Add CHANGELOG.md deprecation section

```markdown
## [Unreleased]

### Deprecated

- `BaseExecutionInfo` dataclass deprecated as of v1.5.0; removed in v2.0.0.
  **Migration**: Use `ExecutionInfoBase` or its domain-specific subtypes.
  Runtime `DeprecationWarning` emitted on instantiation. Related: #728, #658.

## Migration Timeline

| Version | Action |
|---------|--------|
| v1.5.0  | `BaseExecutionInfo` deprecated; `DeprecationWarning` added at runtime |
| v2.0.0  | `BaseExecutionInfo` removed |
```

---

## Failed Attempts

### `ruff D105` — missing docstring in magic method

- **Symptom**: Pre-commit hook failed with `D105 Missing docstring in magic method` on `__post_init__`.
- **Fix**: Add a one-line docstring `"""Emit a DeprecationWarning on instantiation."""`.
- **Lesson**: `ruff` with `D105` requires docstrings on _all_ dunder methods, including `__post_init__`.

### Skill tool blocked in don't-ask mode

- `AskUserQuestion` was denied because the session ran in non-interactive mode.
- **Workaround**: Pick sensible defaults (category=`testing`, name=`deprecation-warning-migration`) and proceed.

---

## Results & Parameters

| Metric | Value |
|--------|-------|
| Files changed | 4 (`results.py`, `test_results.py`, `test.yml`, `CHANGELOG.md`) |
| Tests added | 1 explicit deprecation test + 8 updated with `pytest.warns` |
| Total tests | 2206 passed, 0 failed |
| Pre-commit hooks | All passed after adding `__post_init__` docstring |
| CI approach | Non-blocking `::warning::` grep annotation |

---

## Copy-Paste Configs

### pytest.ini / pyproject.toml (no changes needed)

Standard pytest handles `pytest.warns` natively.

### Ruff rule to watch

```toml
# pyproject.toml
[tool.ruff.lint]
# D105 is enforced — always add docstrings to dunder methods
```

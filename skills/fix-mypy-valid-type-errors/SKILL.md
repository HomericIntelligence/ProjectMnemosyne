# Skill: Fix Mypy valid-type Errors

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Fix `valid-type` mypy violations so the error code can be removed from `disable_error_code` |
| **Outcome** | ✅ 2 violations fixed, `valid-type` re-enabled, baseline updated (157 errors, 19 codes disabled) |
| **Issue** | ProjectScylla #888 — Phase 1 of roadmap #687 |

## When to Use

Use this skill when:

- Mypy has a suppressed error code in `disable_error_code` (e.g., `"valid-type"`) due to accumulated violations
- A roadmap issue tasks you with fixing a category of type errors to re-enable the check
- You see annotations like `callable`, `any`, `dict[str, any]` (lowercase built-ins used as types)
- Pre-commit mypy hook is failing with `valid-type` or similar "invalid type" errors
- You want to incrementally reduce the `disable_error_code` list in `pyproject.toml`

**Trigger phrases:**

- "Fix valid-type violations"
- "Re-enable mypy error code"
- "Replace lowercase `callable` with `Callable`"
- "Fix `any` used as type annotation"

## Root Cause

Python built-in names like `callable`, `any`, `type`, and `list` are valid at runtime but mypy
(with `valid-type` enabled) requires the proper `typing` or `collections.abc` equivalents:

| Wrong (runtime only) | Correct (mypy-compatible) |
|----------------------|--------------------------|
| `callable` | `Callable[[ArgType], ReturnType]` from `collections.abc` |
| `any` | `Any` from `typing` |
| `dict[str, any]` | `dict[str, Any]` |
| `type[Foo]` | Valid in Python 3.10+, mypy ≥0.930 — no change needed |

## Verified Workflow

### Step 1: Identify All Violations

```bash
# Find all valid-type violations across the codebase
pixi run python -m mypy scylla/ --enable-error-code valid-type 2>&1 | grep "valid-type"

# Also grep for common patterns
grep -rn ": callable" scylla/
grep -rn "dict\[str, any\]" scylla/
```

**Note:** The issue description count may differ from the actual grep count if the codebase
has changed since the issue was filed. Trust the mypy output, not the issue's stated count.

### Step 2: Apply Fixes

**Fix 1 — `callable` → `Callable[[ArgType], ReturnType]`:**

```python
# Before (invalid)
def _generate_table(column_header_fn: callable) -> list[str]: ...

# After (correct — use collections.abc, not typing)
from collections.abc import Callable

def _generate_table(column_header_fn: Callable[[Any], str]) -> list[str]: ...
```

Prefer `from collections.abc import Callable` over `from typing import Callable`
(the latter is deprecated since Python 3.9).

**Fix 2 — `any` → `Any`:**

```python
# Before (invalid — lowercase any is a built-in function, not a type)
def load_result(run_dir: Path) -> dict[str, any]: ...

# After (correct)
from typing import Any

def load_result(run_dir: Path) -> dict[str, Any]: ...
```

### Step 3: Verify Zero Violations

```bash
pixi run python -m mypy scylla/ --enable-error-code valid-type 2>&1 | grep "valid-type"
# Expected: no output (zero violations)
```

### Step 4: Remove from `disable_error_code` in `pyproject.toml`

```toml
# Before
disable_error_code = [
    ...
    "valid-type",  # 5 violations - invalid type annotations
    ...
]

# After — remove the line entirely
disable_error_code = [
    ...
    # valid-type line removed
    ...
]
```

Also update the baseline comment:

```toml
# See MYPY_KNOWN_ISSUES.md for current baseline (157 errors as of 2026-02-21)
```

### Step 5: Remove from `scripts/check_mypy_counts.py`

```python
# Before
DISABLED_ERROR_CODES = [
    ...
    "valid-type",
    ...
]

# After — remove the entry
```

This keeps the regression guard in sync with `pyproject.toml`.

### Step 6: Update `MYPY_KNOWN_ISSUES.md`

```bash
pixi run python scripts/check_mypy_counts.py --update
```

Verify:
- `valid-type` row is removed from the baseline table
- Total error count and disabled code count are decremented

### Step 7: Run Full Validation

```bash
# Verify mypy passes
pre-commit run mypy-check-python --all-files

# Verify all hooks pass
pre-commit run --all-files

# Run full test suite
pixi run python -m pytest tests/ -v
```

## Key Insight: Issue Count vs Actual Violations

The issue description stated "5 `valid-type` violations" but only **2 actual violations** existed
at implementation time. The discrepancy arose because:

1. The issue was filed against an older baseline
2. Some violations may have been fixed in unrelated PRs before this issue was implemented
3. `type[Exception]` (noted as a potential violation) is **valid** in mypy ≥0.930 with Python 3.10+

**Always run mypy to confirm the actual count before starting work.**

## Results & Parameters

| Metric | Value |
|--------|-------|
| Violations fixed | 2 |
| Files modified | 6 (2 source + pyproject.toml + check_mypy_counts.py + MYPY_KNOWN_ISSUES.md + pixi.lock) |
| Tests after fix | 2436 passed, 74.16% coverage |
| Baseline before | 159 errors, 20 codes disabled |
| Baseline after | 157 errors, 19 codes disabled |
| PR | HomericIntelligence/ProjectScylla#932 |

## Failed Attempts

None — the fix was straightforward once the actual violation count was verified against mypy output.
The only "gotcha" was the stated-vs-actual count discrepancy (5 in issue → 2 actual violations).

## Related Skills

- `fix-ruff-linting-errors` — systematic approach to fixing linting errors for CI
- `batch-pr-pre-commit-fixes` — batch-fixing pre-commit failures across multiple PRs
- `coverage-threshold-tuning` — managing test coverage gates alongside type checking

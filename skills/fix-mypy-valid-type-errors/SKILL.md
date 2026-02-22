---
name: fix-mypy-valid-type-errors
description: "TRIGGER CONDITIONS: When re-enabling mypy 'valid-type' error code; when type annotations use lowercase builtins as types (callable, any); when incrementally improving mypy strictness per a phased roadmap"
user-invocable: false
category: tooling
date: 2026-02-21
---

# fix-mypy-valid-type-errors

Fix mypy `valid-type` violations by replacing lowercase builtin names used as types with proper `typing`/`collections.abc` equivalents, then re-enable the error code.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-21 |
| Objective | Fix all `valid-type` mypy violations and remove `valid-type` from `disable_error_code` |
| Outcome | Success — 2 violations fixed, error code re-enabled, all 2436 tests passing |

## When to Use

- Fixing `valid-type` mypy errors (e.g., `callable`, `any` used as type annotations)
- Following a phased mypy strictness roadmap (like `#687`)
- Incrementally re-enabling disabled mypy error codes in a large codebase
- When `pyproject.toml` has `disable_error_code = ["valid-type", ...]` and violations are fixed

## Verified Workflow

1. **Find all violations** with the error code explicitly enabled:

   ```bash
   pixi run python -m mypy scylla/ --enable-error-code valid-type 2>&1 | grep "valid-type"
   ```

2. **Fix each violation** — common patterns:
   - `callable` → `Callable[[ArgType], ReturnType]` from `collections.abc`
   - `dict[str, any]` → `dict[str, Any]` (capitalize, already imported from `typing`)
   - `list[any]` → `list[Any]`

3. **Add missing imports** if `Callable` isn't already imported:

   ```python
   from collections.abc import Callable
   from typing import Any  # already present in most files
   ```

4. **Re-verify zero violations**:

   ```bash
   pixi run python -m mypy scylla/ --enable-error-code valid-type
   # Should produce no output (no violations)
   ```

5. **Remove from `pyproject.toml`** `disable_error_code` list:

   ```toml
   # Remove this line:
   "valid-type",      # 5 violations - invalid type annotations
   ```

6. **Remove from `scripts/check_mypy_counts.py`** `DISABLED_ERROR_CODES` list (if present).

7. **Update `MYPY_KNOWN_ISSUES.md`**:
   - Remove the `valid-type` row from the disabled codes table
   - Update the total error count and number of disabled codes in the status header
   - Run `python scripts/check_mypy_counts.py --update` to auto-update counts

8. **Update `pyproject.toml` comment** with new baseline count and date.

9. **Run full pre-commit suite** to verify no regressions:

   ```bash
   pre-commit run --all-files
   ```

10. **Run full test suite**:

    ```bash
    pixi run python -m pytest tests/ -v
    ```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Running `check_mypy_counts.py` validation after update | Script regex `[a-z][a-z0-9-]+` doesn't match backtick-quoted table rows like `` `assignment` `` — exits with code 2 | Pre-existing bug; script only works with unquoted error codes in the MD table. Use `--update` to auto-fix counts but ignore the validation path against the backtick format |
| Committing with unstaged `pixi.lock` | Pre-commit stash/unstash conflicts when there are unstaged files alongside staged ones | Stage all modified files including `pixi.lock` before committing |
| First ruff check run modified files | Ruff auto-fixed import ordering, causing the hook to report failure | Re-run ruff check after auto-fix; it will pass on the second run |

## Results & Parameters

The 2 violation patterns fixed in ProjectScylla (2026-02-21):

```python
# BEFORE (invalid):
def _generate_criteria_comparison_table(
    ...
    column_header_fn: callable,   # lowercase builtin - not valid as type
) -> list[str]:

# AFTER (correct):
from collections.abc import Callable
def _generate_criteria_comparison_table(
    ...
    column_header_fn: Callable[[Any], str],
) -> list[str]:
```

```python
# BEFORE (invalid):
def load_agent_result(run_dir: Path) -> dict[str, any]:  # lowercase 'any'

# AFTER (correct):
def load_agent_result(run_dir: Path) -> dict[str, Any]:  # capitalize
```

MYPY_KNOWN_ISSUES.md update pattern:

```markdown
# Before: valid-type row present
| `valid-type` | 5 | Invalid type annotations | Phase 1 |

# After: row removed, total counts updated
**Status**: 157 total type errors (was 159), 19 codes disabled (was 20)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #932, Issue #888 (Phase 1 of #687 roadmap) | [notes.md](references/notes.md) |

## References

- Related skills: `coverage-threshold-tuning`, `batch-pr-pre-commit-fixes`
- Roadmap pattern: phased mypy strictness improvement (`disable_error_code` → fix → re-enable)

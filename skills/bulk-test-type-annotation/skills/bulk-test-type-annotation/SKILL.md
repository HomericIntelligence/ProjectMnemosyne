---
name: bulk-test-type-annotation
description: "TRIGGER CONDITIONS: Annotating hundreds of unannotated test functions in tests/unit/ to satisfy mypy disallow_untyped_defs. Use when removing a [[tool.mypy.overrides]] suppress block for a test directory, adding -> None to test methods, and adding typing.Any to pytest fixture parameters in bulk."
user-invocable: false
category: testing
date: 2026-03-06
---

# bulk-test-type-annotation

How to annotate hundreds of test functions in a test suite to satisfy mypy's `disallow_untyped_defs`, remove a mypy override block, and avoid the cascade of secondary errors that follow the first pass.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-06 |
| Objective | Add type annotations to ~635 unannotated test functions in `tests/unit/`, remove `[[tool.mypy.overrides]]` suppress block |
| Outcome | Success — zero mypy errors across 200 source files, 4455 unit tests pass |
| Issue | HomericIntelligence/ProjectScylla#1379 |
| PR | HomericIntelligence/ProjectScylla#1453 |

## When to Use

- A `[[tool.mypy.overrides]]` block with `disable_error_code = ["no-untyped-def"]` exists for a test directory
- You need to add `-> None` to hundreds of test methods in bulk
- Pytest fixture parameters need `typing.Any` annotations
- Inner helper functions inside tests lack return type annotations
- You want mypy to enforce full type coverage on the test suite

## Verified Workflow

### Phase 1: Annotate test function return types

Use an AST-guided script that matches `def test_*`, `def setUp`, `def tearDown`, `def setup_method`, etc. and appends `-> None:` when no return annotation exists:

```python
import re
from pathlib import Path

# Single-line def: ends with ):
func_match = re.match(
    r'^( *)(def (?:test_\w+|setUp|tearDown|setup_method|teardown_method|setup_class|teardown_class|setUpClass|tearDownClass)\s*\(.*\))(\s*):$',
    stripped
)
if func_match and '->' not in func_match.group(2):
    new_line = f"{func_match.group(1)}{func_match.group(2)} -> None:\n"
```

Run on entire `<test-dir>/`:
```bash
python3 annotate_tests.py   # adds -> None to ~590 functions
```

### Phase 2: Check actual mypy errors (don't guess)

```bash
<package-manager> run mypy <test-dir>/
```

Remove the override from `pyproject.toml` **before** running mypy so you see the real error count. Expect 3 error categories:

1. `[no-untyped-def]` — arguments still unannotated (fixture params, inner helpers)
2. `[return-value]` — `-> None` added to functions that actually return values
3. `[no-any-return]` / `[func-returns-value]` — fixture functions returning dataframes annotated `-> None`

### Phase 3: Fix argument annotations with `Any`

Replace unannotated parameters with `Any` (not `object` — `object` causes cascade errors):

```python
# In parameter parser: replace untyped params with : Any
new_parts.append(f'{leading}{name}: Any{rest}')
```

**Critical**: Add `from typing import Any` to each file **after** the module docstring and **after** any `from __future__ import annotations` line. Getting this order wrong causes syntax errors or E402.

### Phase 4: Fix return-value cascade

Inner functions annotated `-> None` that actually return values need `-> Any`:

```python
# Search backwards from error line for ) -> None:
re.sub(r'\) -> None:(\s*)$', r') -> Any:\1', line)
```

### Phase 5: Fix generator fixtures

Generator fixtures (`yield`-based) need `Generator[Any, None, None]`:

```python
def my_fixture() -> Generator[Any, None, None]:
    yield value
```

### Phase 6: Run pre-commit and fix import ordering

Ruff will flag E402 if `from typing import Any` lands before other imports or inside docstrings. Auto-fix:

```bash
<package-manager> run ruff check <test-dir>/ --fix
```

### Phase 7: Remove the override and verify

```toml
# Remove from pyproject.toml:
# [[tool.mypy.overrides]]
# module = "tests.unit.*"
# disable_error_code = ["no-untyped-def"]
```

```bash
<package-manager> run mypy <test-dir>/
# Expected: Success: no issues found in N source files
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Used `object` as the annotation type for all fixture parameters | `object` is too restrictive — `"object" has no attribute "readouterr"`, `Unsupported left operand type for / ("object")` cascade errors throughout | Always use `Any` for pytest fixture parameters, not `object` |
| Single-pass script: add `-> None` to all functions at once | Functions that return values (inner helpers, mock callbacks) got `[return-value]` errors — `-> None` is wrong for them | Run mypy after phase 1 to identify which functions need `-> Any` vs `-> None` |
| Inserting `from typing import Any` at line 0 of file | Placed import before module docstring; caused E402 when `from __future__ import annotations` came later | Insert after docstring closes AND after any `from __future__` line |
| Regex to insert import `from __future__` on docstring-first files | Pattern matched inside docstring body, inserting `from typing import Any` into the middle of the docstring | Check that insertion point is after the closing `"""` |
| Multi-line def collection using paren counting | Some defs had `) -> None:` on the last line already; script added a second `) -> None:` producing unmatched `)` syntax errors | Before modifying the closing line, check it doesn't already contain `-> None` |
| Using `generator` fixture `-> None` annotation | mypy `[misc]`: generator return type must be `Generator` or subtype | Detect `yield` in function body, annotate as `Generator[Any, None, None]` |

## Results & Parameters

**Files changed**: 62 test files
**Annotations added**: ~590 `-> None` + ~725 `: Any` parameter annotations
**mypy errors resolved**: 489 cascade errors after initial pass
**Test count unchanged**: 4455 unit tests pass

Key pyproject.toml change:
```toml
# BEFORE (suppress override):
[[tool.mypy.overrides]]
module = "tests.unit.*"
disable_error_code = ["no-untyped-def"]

# AFTER (removed entirely — mypy now enforces full coverage):
# (block deleted)
```

Key annotation patterns:
```python
# Test method (no params beyond self/fixtures):
def test_something(self) -> None:

# Test with pytest fixtures — use Any:
def test_with_fixture(self, my_fixture: Any, tmp_path: Any) -> None:

# Inner mock/helper that returns a value:
def mock_reset_runs(checkpoint: Any, from_state: Any, **kwargs: Any) -> Any:
    return 1

# Generator fixture:
def my_fixture() -> Generator[Any, None, None]:
    yield create_thing()
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1453, issue #1379 — ~635 unannotated functions in tests/unit/ | [notes.md](../../references/notes.md) |

## References

- Related skills: `flaky-test-patch-isolation`, `script-test-coverage-pattern`
- mypy docs: `disallow_untyped_defs`, `[[tool.mypy.overrides]]`

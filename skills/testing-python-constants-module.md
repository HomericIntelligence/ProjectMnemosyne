---
name: testing-python-constants-module
description: "Test Python constants modules for type safety, immutability, and format string validity. Use when: (1) adding test coverage for a constants.py module, (2) verifying frozenset immutability and contents, (3) testing logging format strings."
category: testing
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - python
  - constants
  - frozenset
  - logging
  - unit-tests
  - pytest
---

# Testing Python Constants Modules

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add regression tests for a Python constants module containing frozenset and logging format string constants |
| **Outcome** | 17 tests pass, 100% coverage on constants module |
| **Verification** | verified-local — all tests pass locally, CI validation pending on PR |

## When to Use

- A constants module defines `frozenset` or other immutable collection constants that need type regression tests
- A constants module defines `logging.Formatter`-compatible format strings
- A quality audit or issue identifies a constants module with zero test coverage
- You need to verify that constants can't be accidentally changed from `frozenset` to `set`

## Verified Workflow

### Quick Reference

```bash
# Run constants tests
pixi run python -m pytest tests/unit/test_constants.py -v
```

### Detailed Steps

1. **Read the constants module** to understand all exported constants, their types, and their values.

2. **Test frozenset constants** with four assertion categories:
   - **Type check**: `isinstance(CONST, frozenset)` — catches `set` vs `frozenset` regressions
   - **Contents check**: Parametrize over all expected entries — catches accidental removals
   - **Entry type check**: Verify all entries are strings (or expected type)
   - **Immutability check**: Verify `.add()` and `.discard()` raise `AttributeError`

   ```python
   class TestDefaultExcludeDirs:
       def test_is_frozenset(self) -> None:
           assert isinstance(DEFAULT_EXCLUDE_DIRS, frozenset)

       @pytest.mark.parametrize("directory", [".git", "__pycache__", "node_modules"])
       def test_contains_expected_entry(self, directory: str) -> None:
           assert directory in DEFAULT_EXCLUDE_DIRS

       def test_all_entries_are_strings(self) -> None:
           for entry in DEFAULT_EXCLUDE_DIRS:
               assert isinstance(entry, str)

       def test_immutability(self) -> None:
           with pytest.raises(AttributeError):
               DEFAULT_EXCLUDE_DIRS.add("new_dir")  # type: ignore[attr-error]
           with pytest.raises(AttributeError):
               DEFAULT_EXCLUDE_DIRS.discard(".git")  # type: ignore[attr-error]
   ```

3. **Test logging format strings** with three assertions:
   - **Type check**: `isinstance(LOG_FORMAT, str)`
   - **Formatter validity**: Construct a `logging.Formatter` and format a `LogRecord` — confirms the string is valid
   - **Field presence**: Verify expected `%(field)s` placeholders are present

   ```python
   class TestLogFormat:
       def test_is_string(self) -> None:
           assert isinstance(LOG_FORMAT, str)

       def test_valid_logging_formatter(self) -> None:
           formatter = logging.Formatter(LOG_FORMAT)
           record = logging.LogRecord(
               name="test", level=logging.INFO, pathname="test.py",
               lineno=1, msg="hello", args=None, exc_info=None,
           )
           formatted = formatter.format(record)
           assert len(formatted) > 0

       def test_contains_standard_fields(self) -> None:
           assert "%(asctime)s" in LOG_FORMAT
           assert "%(name)s" in LOG_FORMAT
           assert "%(levelname)s" in LOG_FORMAT
           assert "%(message)s" in LOG_FORMAT
   ```

4. **Place test file** at the same level as the constants module in the test tree (e.g., `tests/unit/test_constants.py` for `hephaestus/constants.py`).

5. **Run and verify**: All tests should pass on first attempt — no mocking needed since constants are pure values.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked on first try | N/A | Constants testing requires no mocking — pure value assertions are straightforward |

## Results & Parameters

### Test Categories for Constants Modules

| Constant Type | Test Categories | Example Assertions |
|---------------|----------------|-------------------|
| `frozenset` | type, contents (parametrized), entry types, immutability | `isinstance()`, `in`, `pytest.raises(AttributeError)` |
| `str` (format) | type, formatter validity, field presence | `logging.Formatter()`, `LogRecord.format()`, `"%(field)s" in` |
| `int`/`float` | type, value range, relationships between constants | `isinstance()`, `>= 0`, `TIMEOUT > INTERVAL` |
| `dict` | type, required keys, value types, immutability (if frozen) | `isinstance()`, `key in`, `isinstance(v, expected)` |

### Coverage Impact

```
hephaestus/constants.py: 0% → 100% (2 statements covered)
New tests: 17 (11 parametrized entries + 3 frozenset checks + 3 format string checks)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #61, PR #122 — 17 tests for constants.py | Tests DEFAULT_EXCLUDE_DIRS and LOG_FORMAT |

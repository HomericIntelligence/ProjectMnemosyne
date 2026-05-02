---
name: hook-grep-chain-unit-tests
description: 'Write pure-Python pytest tests that replicate a pre-commit hook''s bash
  grep chain as a Python predicate. Use when: a pre-commit hook uses grep with exclusion
  patterns and has no unit tests, you need fast regression coverage without invoking
  pre-commit, or you want to document known hook limitations.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Skill** | hook-grep-chain-unit-tests |
| **Category** | testing |
| **Language** | Python / pytest |
| **Primary file** | `.pre-commit-config.yaml` |
| **Test target** | Hook grep chain logic (replicated as Python `re` predicate) |

A pre-commit hook that uses a bash grep pipe (`grep pattern | grep -v exclusion1 | grep -v exclusion2`)
can be regression-tested directly as a Python predicate — no subprocess, no pre-commit invocation,
no binary required. The predicate runs in milliseconds and makes positive/negative/edge cases explicit.

## When to Use

- A pre-commit hook bans a code pattern via `grep pattern | grep -v ...` and has no unit tests
- You need to add tests for: positive cases (caught), negative cases (excluded), and edge cases
- The issue asks you to follow the pattern of an existing similar test file
- You want to document known hook limitations (e.g. grep cannot distinguish string literals)

## Verified Workflow

### Quick Reference

| Step | Action |
| ------ | -------- |
| 1 | Read exact hook `entry:` from `.pre-commit-config.yaml` |
| 2 | Translate each grep step to a Python `re.search()` call |
| 3 | Compose into an `is_violation(line: str) -> bool` predicate |
| 4 | Write `TestPositiveCases`, `TestNegativeCases`, `TestEdgeCases` |
| 5 | Use `@pytest.mark.parametrize` for multiple similar inputs |
| 6 | Run and verify — no warnings, no failures |

### Step 1 — Extract the exact hook entry

```bash
grep -A5 "id: <hook-id>" .pre-commit-config.yaml
```

For a hook like:

```bash
grep -rn "\.__matmul__(" . --include="*.mojo" |
  grep -v "fn __matmul__(" |
  grep -v "# __matmul__" |
  grep -v "__matmul__.*deprecated"
```

### Step 2 — Map grep steps to Python re

| Bash grep step | Python equivalent |
| ---------------- | ------------------- |
| `grep 'PATTERN'` | `re.search(r'PATTERN', line)` |
| `grep -v 'EXCL'` | `not re.search(r'EXCL', line)` |

Translate ALL exclusion steps. A line is a violation when the positive match holds
AND all exclusions are absent.

### Step 3 — Write the predicate

```python
import re


def is_violation(line: str) -> bool:
    """Return True if *line* would be flagged by the <hook-name> hook.

    Replicates the bash grep chain::

        grep 'PATTERN'
        grep -v 'EXCL1'
        grep -v 'EXCL2'
    """
    if not re.search(r'PATTERN', line):
        return False
    if re.search(r'EXCL1', line):
        return False
    if re.search(r'EXCL2', line):
        return False
    return True
```

### Step 4 — Write test classes

```python
class TestPositiveCases:
    @pytest.mark.parametrize("line", [
        "    result = a.__matmul__(b)",
        "    c = self.__matmul__(other)",
    ])
    def test_call_site_is_violation(self, line: str) -> None:
        """Direct call sites must be flagged."""
        assert is_violation(line), f"Expected violation for: {line!r}"


class TestNegativeCases:
    def test_function_definition_excluded(self) -> None:
        """Method definition is not a call site."""
        assert not is_violation("fn __matmul__(self, rhs: Self) -> Self:")

    def test_comment_line_excluded(self) -> None:
        assert not is_violation("# __matmul__ is deprecated")


class TestEdgeCases:
    def test_string_literal_is_caught(self) -> None:
        """Grep has no AST awareness — string contents are flagged.
        This test documents the known limitation rather than ideal behaviour."""
        line = 'var msg = ".__matmul__( is a call site"'
        assert is_violation(line)  # false positive — documented limitation
```

### Step 5 — Run and verify

```bash
pixi run python -m pytest tests/test_<hook_name>.py -v
# 13 passed in 0.02s — no warnings
```

### Step 6 — Ensure docstrings use single quotes or raw strings for bash patterns

Python 3.12+ emits `SyntaxWarning` for unrecognised escape sequences in regular string literals
(e.g. `"\."` in a docstring). Use single quotes or raw strings in module/function docstrings
when quoting bash grep patterns to avoid these warnings:

```python
# ✅ Safe — no escape sequence warning
"""
    grep '.__matmul__('
"""

# ❌ Triggers SyntaxWarning in Python 3.12+
"""
    grep "\.__matmul__("
"""
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Backslash escape in docstring | Used `"\.__matmul__("` in module docstring to show the bash grep command | Python 3.12+ `SyntaxWarning: "\." is an invalid escape sequence` (docstrings are regular strings) | Use single quotes `'.\__matmul__('` or a `.. code-block:: bash` RST block in docstrings; backslashes in re patterns belong in raw strings `r"..."`, not docstrings |
| Treating string literal edge case as a negative | Initially expected `".__matmul__("` inside a string to NOT be a violation | Bash grep has no AST awareness — the pattern fires regardless of syntactic context | The test should assert `is_violation(...) == True` and add a comment documenting the known false-positive limitation |

## Results & Parameters

### Final test structure (13 tests, 0.02s)

```text
TestPositiveCases  (4 tests) — call sites caught via @pytest.mark.parametrize
TestNegativeCases  (5 tests) — fn definitions, comment lines, deprecated variants excluded
TestEdgeCases      (4 tests) — string literal false-positive, single-line fn+body, no-dot, no-call
```

### Key imports (minimal)

```python
import re
import pytest
```

No `subprocess`, no `yaml`, no `pathlib` — pure logic tests.

### Predicate template

```python
def is_violation(line: str) -> bool:
    """Return True if *line* would be flagged by the <hook-id> hook.

    Replicates the bash grep chain::

        grep 'POSITIVE_PATTERN'
        grep -v 'EXCL1'
        grep -v 'EXCL2'
        grep -v 'EXCL3'
    """
    if not re.search(r'POSITIVE_PATTERN', line):
        return False
    if re.search(r'EXCL1', line):
        return False
    if re.search(r'EXCL2', line):
        return False
    if re.search(r'EXCL3', line):
        return False
    return True
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #4783 — `no-matmul-call-sites` hook | [notes.md](../references/notes.md) |

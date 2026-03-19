---
name: pre-commit-pygrep-hook
description: 'Add a regex-based pre-commit hook using language: pygrep to detect forbidden
  code patterns. Use when: automating manual grep audits as commit-time checks, banning
  debug artifacts in specific directories, or preventing deprecated syntax from being
  re-introduced.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Category** | ci-cd |
| **Complexity** | Low |
| **Time** | < 5 min |
| **Dependencies** | pre-commit installed, `.pre-commit-config.yaml` exists |

Adds a `language: pygrep` hook to `.pre-commit-config.yaml` that runs a regex against
staged files with zero external dependencies. Also adds pytest tests that validate the
regex pattern directly, ensuring the hook behaviour is documented and regression-tested
without requiring the full pre-commit runtime.

## When to Use

- A periodic manual `grep` audit was done and should be automated
- Debug artifact patterns (`print("NOTE/TODO/FIXME")`) must be caught at commit time
- Deprecated or banned syntax patterns must be prevented from re-appearing
- Zero-dependency guardrail needed that works with `language: pygrep`

## Verified Workflow

### Quick Reference

```yaml
# Minimal hook stanza
- id: check-print-debug-artifacts
  name: Check for NOTE/TODO/FIXME in print statements
  description: >-
    Fail if examples/ contains print() calls with NOTE, TODO, or FIXME.
  entry: 'print.*(NOTE|TODO|FIXME)'
  language: pygrep
  files: ^examples/
```

### Step 1 — Identify the pattern

Convert the manual grep command to a regex:

```bash
# Original manual audit command (from issue #3194)
grep -rn 'print.*NOTE\|print.*TODO\|print.*FIXME' examples/
```

Translated to pygrep regex: `print.*(NOTE|TODO|FIXME)`

**Key difference**: pygrep uses Python `re` syntax (use `|` inside a group, not `\|`).

### Step 2 — Add the hook stanza

Insert into the appropriate `local` repo block in `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: check-print-debug-artifacts
      name: Check for NOTE/TODO/FIXME in print statements
      description: >-
        Fail if examples/ contains print() calls with NOTE, TODO, or FIXME
        left over from development/debugging.
      entry: 'print.*(NOTE|TODO|FIXME)'
      language: pygrep
      files: ^examples/
```

**Placement tip**: Add new hooks alongside similar hooks in the same `repo: local` block.
Avoid creating a new `- repo: local` block for every hook.

### Step 3 — Write pytest tests for the regex

```python
import re
PATTERN = re.compile(r"print.*(NOTE|TODO|FIXME)")

def matches(line: str) -> bool:
    return bool(PATTERN.search(line))
```

Parametrize positive cases (must match) and negative cases (must not match):

```python
POSITIVE_CASES = [
    ('print("NOTE: fix this")', "bare NOTE"),
    ('print("TODO: remove")', "bare TODO"),
    ('# print("NOTE: commented")', "commented-out print still flagged"),
]

NEGATIVE_CASES = [
    ('print("hello world")', "no keyword"),
    ('log("TODO: ignored")', "non-print call"),
    ('print("noted")', "partial word match — not flagged"),
]
```

**Important**: `language: pygrep` matches the raw line content including `#`-prefixed
comments. Commented-out prints that contain NOTE/TODO/FIXME **will** be flagged. This is
correct and expected — document it in the positive cases.

### Step 4 — Validate baseline

Run the hook against all files before committing to confirm the codebase is clean:

```bash
SKIP=mojo-format,mypy pixi run pre-commit run check-print-debug-artifacts --all-files
```

### Step 5 — Run tests

```bash
pixi run python -m pytest tests/test_check_print_debug_artifacts.py -v
```

### Step 6 — Commit and PR

```bash
git add .pre-commit-config.yaml tests/test_check_<hook-name>.py
git commit -m "feat(pre-commit): add hook to catch <pattern>"
git push -u origin <branch>
gh pr create --title "feat(pre-commit): ..." --body "Closes #<issue>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Test: commented-out print as negative case | Added `# print("NOTE: ...")` to NEGATIVE_CASES expecting it would not match | `pygrep` matches the raw line — `# print(...)` still contains `print.*NOTE` | Move commented-out prints to POSITIVE_CASES; pygrep does not understand comments |
| Using `\|` alternation in pygrep entry | Wrote `print.*NOTE\|print.*TODO\|print.*FIXME` (grep syntax) | pygrep uses Python `re` syntax; `\|` is a literal pipe | Use `(NOTE\|TODO\|FIXME)` or `(NOTE|TODO|FIXME)` group syntax |

## Results & Parameters

### Hook parameters

| Field | Value | Notes |
|-------|-------|-------|
| `language` | `pygrep` | Zero external deps; pattern matched via Python `re` |
| `entry` | `'print.*(NOTE\|TODO\|FIXME)'` | Quoted to prevent shell expansion |
| `files` | `^examples/` | Scope to one directory; adjust as needed |
| `types` | (omitted) | Defaults to all text files; add `[python]` to restrict |
| `pass_filenames` | (omitted) | pygrep handles file iteration automatically |

### Test file template

```python
#!/usr/bin/env python3
"""Unit tests for the <hook-id> pre-commit hook."""

import re
from typing import List, Tuple
import pytest

PATTERN = re.compile(r"<entry-regex>")

def matches(line: str) -> bool:
    """Return True if *line* would be flagged by the hook."""
    return bool(PATTERN.search(line))

POSITIVE_CASES: List[Tuple[str, str]] = [
    ("<flagged line>", "<description>"),
]

NEGATIVE_CASES: List[Tuple[str, str]] = [
    ("<clean line>", "<description>"),
]

@pytest.mark.parametrize("line,description", POSITIVE_CASES)
def test_positive_match(line: str, description: str) -> None:
    assert matches(line), f"Expected match for {description!r}: {line!r}"

@pytest.mark.parametrize("line,description", NEGATIVE_CASES)
def test_negative_no_match(line: str, description: str) -> None:
    assert not matches(line), f"Unexpected match for {description!r}: {line!r}"
```

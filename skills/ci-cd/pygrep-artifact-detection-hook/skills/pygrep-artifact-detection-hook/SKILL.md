---
name: pygrep-artifact-detection-hook
description: "Zero-dependency pattern for adding a pygrep pre-commit hook that blocks commits if banned phrases appear in source files. Covers regex design, ruff D301 fix, and test strategy."
category: ci-cd
date: 2026-03-03
user-invocable: false
---

# Pygrep Artifact Detection Pre-commit Hook

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Prevent regression of Mojo migration docstring artifacts in `scylla/` that survived two manual audits and one prior fix attempt |
| **Outcome** | ✅ Hook implemented, 12 unit tests added, full suite passes (4011+12), PR #1401 merged |
| **PR** | HomericIntelligence/ProjectScylla#1401 |
| **Fixes** | HomericIntelligence/ProjectScylla#1366 (follow-up from #1347) |

## Overview

When a banned phrase survives two consecutive quality audits (Feb and March 2026) despite a prior fix
(PR #1121), the right response is a **compile-time gate**: a pre-commit hook that fails the commit
if any file under the guarded directory contains those phrases.

The `pygrep` hook language in pre-commit requires zero Python scripts — it runs `grep -P` against the
staged files. This makes it the simplest possible solution for phrase-based guards.

## When to Use This Skill

Invoke when:

- A known-bad phrase keeps reappearing after manual fixes (regression pattern)
- The guard needs to be zero-dependency (no new script required)
- The guard targets a specific directory subtree and file type
- The banned pattern is a simple alternation of literal strings

## Verified Workflow

### Step 1 — Add the `pygrep` hook to `.pre-commit-config.yaml`

Place it in the Security checks block (first `local` repo section) alongside similar guards:

```yaml
- id: check-mojo-artifacts
  name: Check for Mojo Migration Artifacts
  description: >-
    Fail if scylla/ contains Mojo migration artifact phrases
    ('Mojo equivalents' or 'no Mojo') left over from a prior migration attempt.
  entry: '(Mojo equivalents|no Mojo)'
  language: pygrep
  files: ^scylla/.*\.py$
  types: [python]
```

Key fields:
- `language: pygrep` — no script needed; pre-commit runs the `entry` as a regex against file contents
- `files:` — a regex applied to staged file paths (anchored with `^`)
- `entry:` — the grep pattern; alternation with `|` works; wrap in single quotes in YAML
- `types: [python]` — additional filter; only `.py` files are checked

### Step 2 — Write unit tests for the regex pattern

Since the hook has no script to import, unit-test the **regex directly**:

```python
r"""Tests for the check-mojo-artifacts pre-commit hook regex pattern.

The hook uses pygrep with pattern ``(Mojo equivalents|no Mojo)`` against
files matching ``^scylla/.*\.py$``.  These tests unit-test that regex
directly, without invoking pre-commit itself.
"""

from __future__ import annotations
import re
import pytest

PATTERN = re.compile(r"(Mojo equivalents|no Mojo)")


@pytest.mark.parametrize("line", [
    "# Mojo equivalents",
    "generate Mojo equivalents for all public functions",
    "# no Mojo",
    "has no Mojo support",
])
def test_pattern_matches_artifact_phrases(line: str) -> None:
    """Pattern must match lines containing the banned artifact phrases."""
    assert PATTERN.search(line) is not None


@pytest.mark.parametrize("line", [
    "# Mojo stdlib limitation",
    "mojo-format",
    "# No mojo (lowercase)",      # case-sensitive — lowercase does NOT match
    "# mojo equivalents (all lowercase)",
])
def test_pattern_does_not_match_legitimate_lines(line: str) -> None:
    """Pattern must not match legitimate lines."""
    assert PATTERN.search(line) is None
```

**Critical**: The `pygrep` language uses case-sensitive matching by default. Design negative test
cases to cover near-misses (different capitalization, partial word matches).

### Step 3 — Fix ruff D301 on the test module docstring

If the docstring contains backslash sequences (e.g. `\\.py$`), ruff raises **D301: Use `r"""`**:

```
D301 Use `r"""` if any backslashes in a docstring
```

Fix: add `r` prefix and remove the double-backslash escaping:

```python
# WRONG — triggers D301
"""Files matching ``^scylla/.*\\.py$``."""

# CORRECT
r"""Files matching ``^scylla/.*\.py$``."""
```

### Step 4 — Confirm baseline is clean before committing

```bash
grep -rn 'Mojo equivalents\|no Mojo' scylla/
# Should return: (no output)
```

This ensures the hook doesn't immediately fail on the codebase it's being added to.

## Failed Attempts

None — the `pygrep` approach worked on the first try. The only issue was the ruff D301 lint error
on the test module docstring (caught by pre-commit during the first commit attempt, fixed immediately).

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Hook language | `pygrep` |
| Entry pattern | `(Mojo equivalents\|no Mojo)` |
| File filter | `^scylla/.*\.py$` |
| Type filter | `[python]` |
| Test count | 12 (6 positive + 6 negative) |
| Implementation time | ~10 min total (no script to write) |
| Pre-commit hook runs | Skipped when no `scylla/*.py` files are staged |

## Key Takeaway

For phrase-based regressions, `pygrep` hooks are the right tool:
- Zero-dependency (no script file to maintain)
- Case-sensitive by default (design tests accordingly)
- Scoped to specific directories via `files:` regex
- Unit-testable by compiling the `entry` pattern directly in pytest

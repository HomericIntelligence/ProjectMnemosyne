---
name: mojo-note-format-compliance
description: 'Enforce # NOTE (Mojo vX.Y.Z): format in Mojo files via pre-commit hook
  and Python audit script. Use when: adding a CI check for a comment format standard,
  implementing a pygrep hook with negative lookahead, or bulk-fixing non-compliant
  NOTE comments.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Goal** | Enforce `# NOTE (Mojo vX.Y.Z):` format in `.mojo` files via CI |
| **Scope** | Pre-commit hook + standalone Python audit script |
| **Pattern** | `re.compile(r"# NOTE(?!\s*\()")` — negative lookahead |
| **Hook type** | `language: pygrep` (same as `check-list-constructor`) |
| **Test count** | 28 pytest unit tests |
| **Files fixed** | ~37 violations across 20 source files |

## When to Use

- Adding a pre-commit hook to enforce a comment format standard in Mojo files
- Implementing a `pygrep` hook that requires negative lookahead regex
- Writing a Python script to audit and bulk-fix non-compliant `# NOTE` comments
- Any codebase-wide comment normalization task before enabling a new lint rule

## Verified Workflow

### 1. Write the audit script (`scripts/check_note_format.py`)

```python
import re
from pathlib import Path
from typing import List, Tuple

EXCLUDED_DIRS = {".worktrees", ".pixi", "build", ".git", "__pycache__", ".mypy_cache"}
SOURCE_DIRS = ["benchmarks", "examples", "papers", "scripts", "shared", "tests"]

# CRITICAL: Use negative lookahead, NOT [^(]
# '# NOTE[^(]' falsely matches '# NOTE (' because space != '('
NOTE_VIOLATION_PATTERN = re.compile(r"# NOTE(?!\s*\()")
```

Key design decisions:
- Excludes `.worktrees/`, `.pixi/`, `build/`, `.git/` to avoid false positives from dependencies
- Defaults to scanning repo source dirs only (not the entire filesystem)
- Accepts optional directory argument for targeted scans
- Exits 0 on clean, 1 on any violations
- Prints `file:line: content` to stdout, summary to stderr

### 2. Fix existing violations before enabling the hook

**Order matters**: Fix all violations first, then add the hook. Adding the hook first blocks all commits.

Categorize violations into two types:
- **Mojo-limitation notes** → annotate with `(Mojo v0.26.1)`: e.g., `# NOTE: Dict iteration not supported` → `# NOTE (Mojo v0.26.1): Dict iteration not supported`
- **General code comments** → remove `# NOTE:` prefix or replace with plain comment: e.g., `# NOTE: Check is inside else block to avoid...` → `# Check is inside else block to avoid...`

### 3. Add the pre-commit hook (`.pre-commit-config.yaml`)

```yaml
- id: check-note-format
  name: Check NOTE format compliance
  description: Enforce # NOTE (Mojo vX.Y.Z): format in Mojo files (issue #3285)
  entry: '# NOTE(?!\s*\()'
  language: pygrep
  files: ^(benchmarks|examples|papers|scripts|shared|tests)/.*\.(mojo|🔥)$
  types: [text]
```

Place it immediately after `check-list-constructor` in the same local repo block.

### 4. Verify clean state

```bash
python3 scripts/check_note_format.py  # exits 0
pixi run python -m pytest tests/scripts/test_check_note_format.py -v  # 28 passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `# NOTE[^(]` as regex | Used character class negation to exclude `(` | `# NOTE (Mojo v0.26.1):` has a space before `(`, so `# NOTE` matches because space ≠ `(` | Always use negative lookahead `(?!\s*\()` when the separator between keyword and delimiter may vary |
| `language: pygrep` with `[^(]` pattern | Same pattern in pre-commit hook | Same false-positive: compliant lines were flagged and hook blocked all commits | Negative lookaheads work fine in `language: pygrep` hooks — pre-commit uses Python's `re` module |
| Checking existing violations manually | Tried to enumerate violations from memory | Missed several files; grep output was the source of truth | Always run `grep -rn "# NOTE[^(]" --include="*.mojo" shared/ tests/ ...` first to get the definitive list |

## Results & Parameters

### Regex pattern (copy-paste)

```python
import re
NOTE_VIOLATION_PATTERN = re.compile(r"# NOTE(?!\s*\()")
```

### Pre-commit hook entry (copy-paste)

```yaml
entry: '# NOTE(?!\s*\()'
language: pygrep
```

### Violation categories and fixes

| Type | Example Before | Example After |
| ------ | ---------------- | --------------- |
| Mojo limitation | `# NOTE: Mojo doesn't support __all__` | `# NOTE (Mojo v0.26.1): Mojo doesn't support __all__` |
| Mojo limitation w/issue | `# NOTE: Batch iteration blocked by #3076` | `# NOTE (Mojo v0.26.1, #3076): Batch iteration blocked` |
| General comment | `# NOTE: Check is inside else block` | `# Check is inside else block` |
| Commented-out imports | `# NOTE: These imports are commented out` | `# These imports are commented out` |

### Test coverage pattern

```python
class TestNoteViolationPattern:
    def test_does_not_flag_compliant_format(self):
        assert not NOTE_VIOLATION_PATTERN.search("    # NOTE (Mojo v0.26.1): explanation")

    def test_does_not_flag_compliant_with_issue(self):
        assert not NOTE_VIOLATION_PATTERN.search("    # NOTE (Mojo v0.26.1, #3092): reason")

    def test_does_not_flag_note_with_open_paren(self):
        assert not NOTE_VIOLATION_PATTERN.search("    # NOTE(#3092): issue ref")

    def test_detects_note_colon(self):
        assert NOTE_VIOLATION_PATTERN.search("    # NOTE: some text")
```

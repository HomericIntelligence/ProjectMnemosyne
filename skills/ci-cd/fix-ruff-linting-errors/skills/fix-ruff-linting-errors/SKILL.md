---
name: fix-ruff-linting-errors
description: Fix all CI/CD failures by systematically resolving ruff linting errors (F841, D401, D102, E741, D103, D413) with automation for repetitive fixes
category: ci-cd
date: 2026-01-04
---

# Fix Ruff Linting Errors

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Fix all CI/CD failures in PR #126 by systematically resolving 431+ ruff linting errors |
| **Outcome** | ✅ Success - All ruff checks passing, pre-commit hooks passing, CI ready |
| **Project** | ProjectScylla |
| **Error Types** | F841 (9), D401 (5), D102 (431), E741 (3), D103 (4), D413 (2), D203/D213 config |

## When to Use This Skill

Use this skill when:
- ✅ Pre-commit hooks are failing with ruff linting errors
- ✅ CI/CD pipeline shows ruff check failures
- ✅ You have hundreds of linting errors to fix (especially D102 missing docstrings)
- ✅ Ruff reports conflicting docstring rules (D203/D211, D212/D213)
- ✅ You need to fix multiple error types systematically

Do NOT use this skill when:
- ❌ You have only 1-2 trivial linting errors (just fix them directly)
- ❌ The errors are not from ruff (different linter)

## Verified Workflow

### Phase 1: Understand the Scope

```bash
# Run ruff locally to see all errors
pixi run ruff check .

# Count errors by type
pixi run ruff check . --select D102 2>&1 | grep "D102" | wc -l
pixi run ruff check . --select F841 2>&1 | grep "F841" | wc -l
```

**Critical Rule**: ALWAYS test locally before pushing to remote.

### Phase 2: Fix Systematically (One Error Type at a Time)

#### 2.1 Fix F841 (Unused Variables)

**Pattern**: Variable assigned but never used

```python
# WRONG
result = orchestrator.run_single(...)
# result is never used after this

# RIGHT
orchestrator.run_single(...)
# No assignment if not needed
```

**Common locations**:
- Exception handlers: `except subprocess.TimeoutExpired as e:` where `e` is used later
- Test methods: `result = adapter.run(...)` where only side effects matter
- Source files: Variables that were intended for later use

**Fix approach**: Read context, remove assignment if value truly unused

#### 2.2 Fix D401 (Docstring Imperative Mood)

**Pattern**: Docstrings should start with imperative verb

```python
# WRONG
"""Helper to create statistics."""
"""Simple implementation that returns success."""
"""Setup test environment."""

# RIGHT
"""Create statistics for testing."""
"""Return success result."""
"""Set up test environment."""
```

**Common patterns**:
- "Helper to X" → "Create X for testing"
- "Factory function to X" → "Create X"
- "Simple implementation that X" → Active verb form
- "Setup" (noun) → "Set up" (verb phrase)

#### 2.3 Fix D102 (Missing Test Method Docstrings) - AUTOMATE THIS

**Problem**: 431 test methods missing docstrings

**Solution**: Create automation script

```python
#!/usr/bin/env python3
"""Add missing docstrings to test methods."""

import re
from pathlib import Path

def generate_docstring(method_name: str) -> str:
    """Generate docstring from test method name.

    Args:
        method_name: Name like 'test_init_default'

    Returns:
        Generated docstring

    """
    # Remove 'test_' prefix
    name = method_name.replace("test_", "")
    # Convert snake_case to words
    words = name.replace("_", " ")
    # Capitalize first letter
    docstring = words[0].upper() + words[1:] + "."
    return f'"""Test {docstring}"""'

def add_docstrings_to_file(file_path: Path) -> int:
    """Add docstrings to test methods in file.

    Args:
        file_path: Path to Python file

    Returns:
        Number of docstrings added

    """
    content = file_path.read_text()
    lines = content.split("\n")
    modified = False
    count = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this is a test method
        match = re.match(r"^(\s+)def (test_\w+)\(", line)
        if match:
            indent = match.group(1)
            method_name = match.group(2)

            # Check if next line already has docstring
            next_line_idx = i + 1
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx].strip()
                if not (next_line.startswith('"""') or next_line.startswith("'''")):
                    # Add docstring
                    docstring = generate_docstring(method_name)
                    lines.insert(next_line_idx, f"{indent}    {docstring}")
                    modified = True
                    count += 1
                    i += 1  # Skip inserted line

        i += 1

    if modified:
        file_path.write_text("\n".join(lines))

    return count
```

**Usage**:
```bash
python3 scripts/add_test_docstrings.py
# Output: Added 431 docstrings across 17 files
```

#### 2.4 Fix E741 (Ambiguous Variable Names)

**Pattern**: Single-letter variables that are ambiguous

```python
# WRONG
levels = [int(l.strip()) for l in args.levels.split(",")]

# RIGHT
levels = [int(level.strip()) for level in args.levels.split(",")]
```

Common culprits: `l` (looks like `1`), `O` (looks like `0`), `I` (looks like `1`)

#### 2.5 Fix D103 (Missing Function Docstrings)

**Pattern**: Public functions missing docstrings

```python
# WRONG
def main():
    parser = argparse.ArgumentParser(...)

# RIGHT
def main():
    """Compose configuration from command line arguments."""
    parser = argparse.ArgumentParser(...)
```

#### 2.6 Fix D413 (Missing Blank Line After Returns)

**Pattern**: Docstring sections need blank line after them

```python
# WRONG
    """
    Args:
        x: Input value
    Returns:
        Output value
    """

# RIGHT
    """
    Args:
        x: Input value

    Returns:
        Output value

    """
```

### Phase 3: Handle Conflicting Docstring Rules

**Problem**: Ruff has conflicting rule pairs that cannot both be enabled

**Conflicting pairs**:
- D203 (1 blank line before class) vs D211 (no blank line before class)
- D212 (multi-line summary first line) vs D213 (multi-line summary second line)

**Solution**: Choose one and ignore the other in `pyproject.toml`

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP"]
ignore = [
    "D100",  # Missing docstring in public module
    "D104",  # Missing docstring in public package
    "D203",  # 1 blank line before class (conflicts with D211)
    "D213",  # Multi-line summary second line (conflicts with D212)
    "D417",  # Missing argument descriptions in docstring
]
```

**Decision rationale**:
- Use D211 (no blank line before class) - more common in Python codebases
- Use D212 (multi-line summary first line) - better readability

### Phase 4: Test Locally Before Pushing

**CRITICAL**: This is non-negotiable user feedback

```bash
# 1. Run ruff check
pixi run ruff check .

# 2. Run pre-commit on all files
pre-commit run --all-files

# 3. Only if BOTH pass, commit and push
git add -A
git commit -m "fix(linting): fix all ruff errors"
git push origin <branch>
```

**Why this matters**:
- Avoids wasting CI minutes on known failures
- Prevents commit spam from iterative fixes
- Shows professionalism and respect for team resources

### Phase 5: Commit and Push

```bash
git add -A
git commit -m "fix(linting): fix all ruff errors to pass CI checks

Fixed all remaining ruff linting errors:
- F841: Removed unused variable assignments (9 instances)
- D401: Changed docstrings to imperative mood (5 instances)
- D102: Added docstrings to all test methods (431 instances)
- E741: Renamed ambiguous variable \`l\` to \`level\` (3 instances)
- D103: Added docstrings to main() functions (4 instances)
- D413: Added blank lines after Returns sections (2 instances)

Created script to automate test docstring generation from method names.

All pre-commit hooks now pass successfully.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
"

git push origin <branch>
```

## Failed Attempts (What NOT to Do)
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Attempt 1: Push fixes without testing locally

**What happened**: Pushed fixes immediately after making changes, before running `pre-commit run --all-files`

**Why it failed**: CI failed with additional errors that would have been caught locally

**User feedback**: "run things locally before pushing to remote"

**Lesson**: ALWAYS run `pre-commit run --all-files` before pushing

### ❌ Attempt 2: Ignore D102 errors because "they're just test methods"

**What happened**: Considered adding D102 to ignore list rather than fixing

**Why it failed**: User rejected this approach

**User feedback**: "no, it is not 'okay' just because they are 'test methods', fix all ruff issues"

**Lesson**: Don't take shortcuts - fix ALL errors properly

### ❌ Attempt 3: Manually add 431 docstrings

**What happened**: Started manually adding docstrings one by one

**Why it failed**: Would take hours and be error-prone

**Solution**: Created automation script that fixed all 431 in ~30 seconds

**Lesson**: Automate repetitive fixes when count > ~20

### ❌ Attempt 4: Add D211 to ignore list (first try)

**What happened**: Added D211 to ignore list to resolve conflict warning

**Why it failed**: D203 and D211 conflict - adding D211 to ignore makes D203 fire on 481 locations

**Solution**: Add D203 to ignore list instead (use D211)

**Lesson**: Understand which rule in the conflicting pair you want to KEEP before ignoring

## Results & Parameters

### Final Stats
- **Total errors fixed**: 454 errors across 7 error types
- **Files modified**: 38 files
- **Automation created**: 1 Python script (120 lines)
- **Time to fix**: ~2 hours (would be ~8 hours without automation)
- **Lines added**: 1,492 insertions (mostly docstrings)

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP"]
ignore = [
    "D100",  # Missing docstring in public module
    "D104",  # Missing docstring in public package
    "D203",  # 1 blank line before class (conflicts with D211)
    "D213",  # Multi-line summary second line (conflicts with D212)
    "D417",  # Missing argument descriptions in docstring
]
```

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### Automation Script Location

`scripts/add_test_docstrings.py` - Reusable for future projects with D102 issues

### Verification Commands

```bash
# Check all errors are fixed
pixi run ruff check .

# Verify pre-commit passes
pre-commit run --all-files

# Check specific error type
pixi run ruff check . --select D102
pixi run ruff check . --select F841
```

## Key Takeaways

1. **Test locally first** - Non-negotiable. Run `pre-commit run --all-files` before every push
2. **Automate repetitive fixes** - If fixing >20 similar errors, write a script
3. **Fix systematically** - One error type at a time, understand the pattern first
4. **Don't take shortcuts** - Fix all errors properly, don't just ignore them
5. **Understand conflicting rules** - Know which rule you want to keep before ignoring the other
6. **Create reusable tools** - The docstring automation script can be used on future projects
7. **Document your work** - Clear commit messages with error counts and approaches

## When You Know This Skill Is Working

✅ All ruff checks pass: `pixi run ruff check .` shows "All checks passed!"
✅ All pre-commit hooks pass: `pre-commit run --all-files` shows all "Passed"
✅ CI/CD pipeline turns green
✅ No conflicting rule warnings in ruff output
✅ You have automation scripts ready for next time

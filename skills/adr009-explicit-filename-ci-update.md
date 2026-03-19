---
name: adr009-explicit-filename-ci-update
description: 'Splitting a Mojo test file per ADR-009 when CI uses explicit filenames
  (not glob). Use when: the CI test group pattern lists files by name and splitting
  would make new part files invisible to CI without a workflow update.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Category | ci-cd |
| Complexity | Low |
| Risk | Low |
| Time | ~20 minutes |

Extends the `adr009-test-file-splitting` skill for CI groups that enumerate test files
**explicitly by name** rather than using a `test_*.mojo` wildcard glob. When splitting a test
file in this context, the CI workflow must also be updated or the new part files will be silently
skipped and never executed.

## When to Use

- A CI test group `pattern:` field lists individual filenames (e.g. `test_foo.mojo test_bar.mojo`)
- The file to split is one of those explicit names
- A `test_*.mojo` wildcard is NOT used for that test group
- You need to replace one filename with N part-file names in the workflow

## Verified Workflow

### 1. Identify the CI group pattern type

Before splitting, determine whether the CI group uses wildcards or explicit names:

```bash
# Check how the file is referenced in comprehensive-tests.yml
grep -n "test_integration.mojo" .github/workflows/comprehensive-tests.yml
```

If output is a `pattern:` line with space-separated names (not `test_*.mojo`), proceed with
this workflow. If it uses a wildcard, use the basic `adr009-test-file-splitting` skill instead.

### 2. Count tests and plan split

```bash
# Count test functions (use [a-z] to avoid matching comments)
grep -c "^fn test_[a-z]" tests/<path>/test_<name>.mojo
```

Target ≤8 per file (ADR-009 hard limit is 10; ≤8 provides a safety buffer).

### 3. Create split files with ADR-009 header

Each new file's docstring must include the tracking comment:

```mojo
"""Description of this part.

# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<name>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""
```

Name the files with a `_part1`, `_part2`, `_part3` suffix for clarity.

### 4. Update the CI workflow pattern (CRITICAL)

Replace the original filename with all new part filenames in the `pattern:` field:

```yaml
# Before:
pattern: "... test_integration.mojo ..."

# After:
pattern: "... test_integration_part1.mojo test_integration_part2.mojo test_integration_part3.mojo ..."
```

### 5. Delete the original file

```bash
git rm tests/<path>/test_<name>.mojo
```

Or just `rm` it — it will show as deleted in `git status`.

### 6. Verify counts and run validate_test_coverage.py

```bash
# Verify each split file is within limit
grep -c "^fn test_[a-z]" tests/<path>/test_<name>_part*.mojo

# Validate CI coverage (detects uncovered test files)
python scripts/validate_test_coverage.py
```

### 7. Stage, commit, and push

```bash
git add .github/workflows/comprehensive-tests.yml \
        tests/<path>/test_<name>.mojo \
        tests/<path>/test_<name>_part1.mojo \
        tests/<path>/test_<name>_part2.mojo \
        tests/<path>/test_<name>_part3.mojo

git commit -m "fix(ci): split test_<name>.mojo into N files per ADR-009"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Only creating new split files | Created 3 new `_part*.mojo` files without updating the CI workflow | `validate_test_coverage.py` pre-commit hook would catch uncovered files; more importantly, the CI job would never run the new files | Always check whether the CI pattern is a wildcard or explicit filename list before splitting |
| Using `grep "^fn test_"` to count | Counted comment lines matching the pattern | The ADR-009 header comment text itself can contain `fn test_` | Use `^fn test_[a-z]` (requires a lowercase letter after the underscore) to match only real functions |

## Results & Parameters

**ADR-009 limits:**

- Hard limit: ≤10 `fn test_` per file
- Target: ≤8 per file (safety buffer)

**Grep pattern for accurate count:**

```bash
grep -c "^fn test_[a-z]" <file>.mojo
```

**CI workflow pattern update example:**

```yaml
# Core Utilities group with explicit filenames
- name: "Core Utilities"
  path: "tests/shared/core"
  pattern: "test_utilities.mojo test_utility.mojo test_integration_part1.mojo test_integration_part2.mojo test_integration_part3.mojo test_inplace_simd.mojo"
```

**Pre-commit hooks that validate the split:**

- `validate_test_coverage.py` — detects uncovered `test_*.mojo` files (catches missing workflow update)
- `mojo format` — ensures new files are properly formatted
- `check-yaml` — validates workflow YAML syntax

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3452, PR #4263 | test_integration.mojo (19 tests) → 3 part files (7+7+5) in Core Utilities group |

**Related:** `adr009-test-file-splitting` (parent skill), `docs/adr/ADR-009-heap-corruption-workaround.md`

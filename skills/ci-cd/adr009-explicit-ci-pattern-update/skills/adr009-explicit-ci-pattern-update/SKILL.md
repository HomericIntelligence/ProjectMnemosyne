---
name: adr009-explicit-ci-pattern-update
description: "ADR-009 test file split when CI uses explicit filename patterns. Use when: splitting a Mojo test file whose CI group lists filenames explicitly (not glob), requiring workflow file updates alongside test file creation."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Category | ci-cd |
| Complexity | Low |
| Risk | Low |
| Time | ~20 minutes |

Extends the base ADR-009 test-file-splitting workflow with an explicit CI pattern update step.
Unlike glob-based CI groups where new `test_*.mojo` files are auto-discovered, some CI groups
in `comprehensive-tests.yml` use explicit space-separated filename lists. Splitting these files
requires updating the workflow in addition to creating the new part files.

## When to Use

- The CI group for the target file uses an explicit filename list (not `test_*.mojo` glob)
- The issue or ADR-009 audit identifies a file in a group like `Core Activations & Types`
- `grep "test_elementwise_edge_cases.mojo" .github/workflows/*.yml` returns a match
- You are splitting any file whose name appears literally in a CI workflow `pattern:` line

## Verified Workflow

### 1. Check CI pattern type before starting

```bash
# Determine if the file is in a glob or explicit list
grep -n "<filename>.mojo" .github/workflows/comprehensive-tests.yml
```

If the filename appears literally, the CI pattern is explicit and this skill applies.
If only a glob pattern like `test_*.mojo` is found, use the base `adr009-test-file-splitting` skill instead.

### 2. Count and plan the split

```bash
grep -c "^fn test_" tests/shared/core/<filename>.mojo
```

Target ≤8 tests per part file (ADR-009 hard limit is 10, target is 8 for safety buffer).
Calculate number of parts: `ceil(total / 8)`.

### 3. Create part files with ADR-009 header

Each new file must begin with the ADR-009 comment block (as a comment before the docstring):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Tests for ... - Part N: <focus area>."""
```

Group tests semantically (e.g., all sqrt tests in part1, all log tests in part2).

### 4. Verify counts in all new files

```bash
for f in tests/shared/core/<prefix>_part*.mojo; do
  count=$(grep -c "^fn test_" "$f")
  echo "$f: $count tests"
done
```

All counts must be ≤8.

### 5. Delete the original file

```bash
git rm tests/shared/core/<original_filename>.mojo
```

### 6. Update the CI workflow pattern

In `.github/workflows/comprehensive-tests.yml`, find the `pattern:` line containing the
original filename and replace it with the space-separated list of part filenames:

```yaml
# Before:
pattern: "... test_elementwise_edge_cases.mojo ..."

# After:
pattern: "... test_elementwise_edge_cases_part1.mojo test_elementwise_edge_cases_part2.mojo test_elementwise_edge_cases_part3.mojo test_elementwise_edge_cases_part4.mojo ..."
```

### 7. Verify the workflow change

```bash
grep -n "elementwise_edge_cases" .github/workflows/comprehensive-tests.yml
# Should show the 4 part files, not the original
```

### 8. Stage specific files and commit

```bash
git add .github/workflows/comprehensive-tests.yml \
        tests/shared/core/<original>.mojo \
        tests/shared/core/<prefix>_part1.mojo \
        tests/shared/core/<prefix>_part2.mojo \
        tests/shared/core/<prefix>_part3.mojo \
        tests/shared/core/<prefix>_part4.mojo
```

All pre-commit hooks must pass before committing (mojo format, test coverage validation, YAML check).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming glob discovery | Expected new `test_*_part*.mojo` files to be auto-discovered by CI | The `Core Activations & Types` CI group uses an explicit filename list, not a glob | Always check `grep "<filename>" .github/workflows/*.yml` first to determine pattern type |
| Using `grep "^fn test_"` to count | Tried counting with base pattern | Would match comment lines containing `fn test_` text | Use `grep -c "^fn test_"` (the line must start with `fn test_`) |

## Results & Parameters

**This session**: `test_elementwise_edge_cases.mojo` (28 tests) → 4 part files

| Part File | Tests | Focus |
|-----------|-------|-------|
| `_part1.mojo` | 8 | sqrt edge cases + float64 dtype + vector |
| `_part2.mojo` | 5 | log edge cases |
| `_part3.mojo` | 8 | exp edge cases + float64 dtype + vector + log/exp inverse |
| `_part4.mojo` | 7 | tanh saturation + trig (sin/cos) |

**CI group affected**: `Core Activations & Types` in `comprehensive-tests.yml`

**ADR-009 limits:**

- Hard limit: ≤10 `fn test_` per file
- Target: ≤8 per file (safety buffer)

**Key difference from base skill**: CI workflow update is required (step 6).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3419, PR #4175 | Splitting `test_elementwise_edge_cases.mojo` in Core Activations & Types CI group |

**Related:** `adr009-test-file-splitting` (base skill for glob-discovered CI groups), `docs/adr/ADR-009-heap-corruption-workaround.md`

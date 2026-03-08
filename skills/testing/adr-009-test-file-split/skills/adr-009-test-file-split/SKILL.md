---
name: adr-009-test-file-split
description: "Split Mojo test files to comply with ADR-009 heap corruption workaround (≤10 fn test_ per file). Use when: a Mojo test file exceeds 10 fn test_ functions, CI shows libKGENCompilerRTShared.so crashes, or a test group fails non-deterministically."
category: testing
date: 2026-03-08
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | adr-009-test-file-split |
| **Category** | testing |
| **Mojo Version** | v0.26.1 |
| **ADR** | ADR-009 (docs/adr/ADR-009-heap-corruption-workaround.md) |
| **Limit** | ≤10 `fn test_` functions per file (target: ≤8 for headroom) |

## When to Use

- A Mojo test file contains more than 10 `fn test_` functions
- CI shows intermittent `libKGENCompilerRTShared.so` JIT faults
- A test group is non-deterministically failing (e.g., 13/20 recent CI runs)
- A new test file is being created with many test cases (plan splits upfront)

## Verified Workflow

### 1. Identify the offending file

```bash
# Count fn test_ functions per file
grep -r "^fn test_" tests/ --include="*.mojo" -l | while read f; do
  count=$(grep -c "^fn test_" "$f")
  echo "$count $f"
done | sort -rn | head -20
```

### 2. Decide on split boundaries

- Target ≤8 tests per file (leaves headroom under the 10-function limit)
- Split along logical groupings: creation, correctness, performance, resource management
- Keep the original filename removed — replace with `_part1.mojo`, `_part2.mojo`, etc.

### 3. Create the split files

Each new file MUST include the ADR-009 header comment:

```mojo
"""Tests for <component> - Part N: <Group Name>.

ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
high test load. Split from <original_filename>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""
```

Each file must have its own `fn main() raises:` that calls only its subset of tests.

### 4. Delete the original file

```bash
rm tests/path/to/test_original.mojo
```

### 5. Check CI workflow coverage

The CI `comprehensive-tests.yml` uses wildcard patterns like `loaders/test_*.mojo`.
If the original was covered by a wildcard, the split files are automatically covered.
Only update the workflow if the original used explicit filename references.

```bash
# Verify wildcard covers new files
grep "test_*.mojo" .github/workflows/comprehensive-tests.yml
```

### 6. Run validate_test_coverage.py

```bash
# Runs automatically as a pre-commit hook, or manually:
python scripts/validate_test_coverage.py
```

If the original file was covered by a glob pattern, the split files are covered automatically.

### 7. Commit

```bash
git add tests/path/to/test_original.mojo \
        tests/path/to/test_original_part1.mojo \
        tests/path/to/test_original_part2.mojo
git commit -m "fix(tests): split test_original.mojo per ADR-009 (≤10 fn test_ limit)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Update CI workflow | Assumed explicit filename references in `comprehensive-tests.yml` | CI already used `loaders/test_*.mojo` wildcard — no update needed | Always check if CI uses wildcard patterns before editing the workflow |
| Create a "Data Loaders" explicit CI group | Considered adding a dedicated group entry for split files | Unnecessary — the existing `Data` group's wildcard already matched | Wildcard patterns like `loaders/test_*.mojo` automatically pick up new files without CI changes |

## Results & Parameters

### Verified Configuration (Issue #3625)

- **Original file**: `tests/shared/data/loaders/test_parallel_loader.mojo` (12 tests)
- **Split into**:
  - `test_parallel_loader_part1.mojo` — 6 tests (creation + correctness)
  - `test_parallel_loader_part2.mojo` — 6 tests (performance + resource management)
- **CI group**: `Data` — pattern `loaders/test_*.mojo` covered both files automatically
- **Pre-commit hooks**: All passed (mojo format, validate_test_coverage, trailing-whitespace)
- **Result**: Clean commit, no CI workflow changes required

### ADR-009 Header Template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Quick Count Command

```bash
# Check all test files for ADR-009 compliance
grep -r "^fn test_" tests/ --include="*.mojo" -l | while read f; do
  count=$(grep -c "^fn test_" "$f")
  if [ "$count" -gt 10 ]; then
    echo "VIOLATION ($count): $f"
  fi
done
```

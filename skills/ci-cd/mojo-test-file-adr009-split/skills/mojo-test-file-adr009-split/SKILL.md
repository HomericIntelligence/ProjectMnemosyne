---
name: mojo-test-file-adr009-split
description: "Split Mojo test files exceeding ADR-009 limit (10 fn test_ per file) to prevent heap corruption. Use when: CI fails non-deterministically with libKGENCompilerRTShared.so JIT fault, or a test file has >10 fn test_ functions."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Trigger** | Mojo test file with >10 `fn test_` functions causing non-deterministic CI failure |
| **Root Cause** | Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault) under high test load |
| **ADR Reference** | ADR-009: ≤10 `fn test_` functions per file |
| **CI Symptom** | Data group fails ~65% of runs; failure rotates across test groups |
| **Fix** | Split into multiple files of ≤8 tests each with ADR-009 header comment |

## When to Use

- A `.mojo` test file contains more than 10 `fn test_` functions
- CI fails non-deterministically with `libKGENCompilerRTShared.so` JIT fault
- A CI test group rotates failures across runs without deterministic root cause
- ADR-009 compliance check flags a file as over-limit

## Verified Workflow

1. **Count test functions** in the offending file:

   ```bash
   grep -c "^fn test_" tests/path/to/test_file.mojo
   ```

2. **Plan the split** — aim for ≤8 tests per file (buffer below the 10 limit):
   - Part 1: primary/core tests
   - Part 2: edge cases and remaining tests

3. **Create `_part1.mojo`** — copy first N tests, update `main()` to call only those:

   ```mojo
   """Module docstring (Part 1 of 2).

   ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
   Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
   high test load. Split from test_original.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
   """
   ```

4. **Create `_part2.mojo`** — remaining tests with same ADR-009 header.

5. **Delete the original file** — replaced entirely, not kept alongside.

6. **Check CI workflow patterns** — most CI groups use `test_*.mojo` glob patterns,
   so new `_part1.mojo` / `_part2.mojo` files are picked up automatically without
   changing the workflow YAML.

7. **Update any README/docs** that explicitly reference the old filename.

8. **Commit with ADR reference**:

   ```bash
   git add tests/path/to/test_original_part1.mojo \
           tests/path/to/test_original_part2.mojo \
           tests/path/to/test_original.mojo  # staged as deleted
   git commit -m "fix(ci): split test_original.mojo into 2 files to fix heap corruption (ADR-009)"
   ```

## ADR-009 Header Comment

Always include this comment block at the top of each split file (in the module docstring):

```mojo
ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
high test load. Split from test_<original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

## CI Workflow Impact

When CI uses directory-scoped wildcard patterns like:

```yaml
pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo"
```

The new `test_foo_part1.mojo` and `test_foo_part2.mojo` files match `test_*.mojo`
automatically. No workflow YAML changes are needed.

Only update workflows if the original file was listed by **explicit filename** (not glob).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep original + add new files | Rename test_foo.mojo → test_foo_part1.mojo, create test_foo_part2.mojo, keep test_foo.mojo | Keeps all 13 tests in original, negating the fix | Original must be deleted; split files fully replace it |
| Split to 3 files of ~4 tests each | Create part1/part2/part3 | More fragmentation than needed; harder to navigate | Target ≤8 per file (not minimum possible); 2 files usually sufficient |
| Update CI workflow YAML explicitly | Add `test_datasets_part1.mojo test_datasets_part2.mojo` to pattern field | Unnecessary when pattern already uses `test_*.mojo` glob | Check glob coverage before editing CI YAML |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Mojo version | v0.26.1 |
| Heap corruption trigger | >10 `fn test_` per file |
| ADR-009 hard limit | ≤10 `fn test_` per file |
| Recommended target | ≤8 `fn test_` per file (2-test buffer) |
| Split naming convention | `test_<name>_part1.mojo`, `test_<name>_part2.mojo` |
| CI failure rate before fix | ~65% (13/20 runs on main) |
| Files affected in this session | `tests/shared/data/test_datasets.mojo` (13 tests → 2 files) |

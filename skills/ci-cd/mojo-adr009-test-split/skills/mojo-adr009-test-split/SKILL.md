---
name: mojo-adr009-test-split
description: "Split Mojo test files exceeding ADR-009 limit of 10 fn test_ functions per file to prevent heap corruption. Use when: a test file has >10 fn test_ functions causing intermittent CI crashes."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| Category | ci-cd |
| Trigger | Test file has >10 fn test_ functions OR intermittent heap corruption CI crashes |
| ADR | ADR-009 (docs/adr/ADR-009-heap-corruption-workaround.md) |
| Mojo Version | v0.26.1 |

## When to Use

- A `.mojo` test file has more than 10 `fn test_` functions
- CI shows intermittent `libKGENCompilerRTShared.so` JIT fault crashes
- The issue is labeled ADR-009 or references heap corruption
- CI failure rate is non-deterministic (load-dependent)

## Verified Workflow

1. **Count test functions** in the file: `grep -c "^fn test_" <file>.mojo`
2. **Plan the split** into groups of ≤8 tests each (buffer below the 10 limit)
   - Split by logical category (e.g., argmax vs top_k vs argsort)
   - Target: 3 files × ≤8 tests = 20 tests max handled comfortably
3. **Create split files** `test_<name>_part1.mojo`, `test_<name>_part2.mojo`, etc.
   - Each must start with the ADR-009 header comment:

     ```mojo
     # ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
     # Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
     # high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
     ```

   - Preserve ALL original imports and test functions exactly
   - Update `main()` to call only the tests in that file
4. **Delete the original** test file
5. **Update CI workflow** (`.github/workflows/comprehensive-tests.yml`):
   - Replace `test_<name>.mojo` with `test_<name>_part1.mojo test_<name>_part2.mojo test_<name>_part3.mojo` in the pattern
6. **Verify** pre-commit hooks pass (validate_test_coverage.py confirms new files are covered)
7. **Commit** with message: `fix(ci): split <file> into N files per ADR-009 (≤10 tests each)`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusting the main() count | The original main() said "18 tests passed" | Actual count was 20 (manual grep confirmed) | Always grep count fn test_ directly, never trust comments |
| Splitting evenly by count | 20/3 = 6.67, tried equal 7/7/6 split | Breaks logical grouping of tests | Split by functional category (argmax/top_k/argsort) instead |

## Results & Parameters

```bash
# Count test functions (ground truth)
grep -c "^fn test_" tests/shared/core/test_utils.mojo

# Verify each split file is within limit
grep -c "^fn test_" tests/shared/core/test_utils_part1.mojo \
                    tests/shared/core/test_utils_part2.mojo \
                    tests/shared/core/test_utils_part3.mojo

# ADR-009 header comment to add at top of each file
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_utils.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md

# CI workflow pattern update (Core Utilities group)
# OLD: test_utils.mojo
# NEW: test_utils_part1.mojo test_utils_part2.mojo test_utils_part3.mojo
```

**Naming convention**: `test_<original>_part<N>.mojo`

**Test distribution**: Target ≤8 tests per file (not 10) to leave buffer for future additions.

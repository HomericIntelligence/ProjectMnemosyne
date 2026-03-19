---
name: adr009-test-file-split
description: "Split Mojo test files to comply with ADR-009 heap corruption workaround\
  \ (\u226410 fn test_ per file). Use when: a Mojo test file exceeds 10 fn test_ functions,\
  \ CI shows intermittent heap corruption from libKGENCompilerRTShared.so, or a CI\
  \ group fails non-deterministically."
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Trigger** | Mojo test file with >10 `fn test_` functions causing intermittent CI failures |
| **Root Cause** | Mojo v0.26.1 heap corruption bug (`libKGENCompilerRTShared.so`) under high test load |
| **Fix** | Split into multiple files of ≤8 tests each (ADR-009 mandates ≤10, target ≤8 for safety margin) |
| **CI Impact** | Glob patterns like `testing/test_*.mojo` auto-discover split files — no workflow changes needed |
| **Effort** | ~15 minutes for a 28-test file split into 4 parts |

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- CI shows intermittent failures with `libKGENCompilerRTShared.so` JIT fault in the error log
- A CI group (e.g., "Testing Fixtures", "Shared Infra & Testing") fails non-deterministically
- ADR-009 compliance check flags a file as exceeding the limit
- CI failure rate across recent runs is high (e.g., 13/20) with no single reproducible root cause

## Verified Workflow

### 1. Count test functions in the file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

If count > 10, proceed with split.

### 2. Plan the split

Divide tests into logical groups of ≤8 per file:

- Group by the function under test (e.g., `zeros_tensor`, `ones_tensor`, `full_tensor`)
- Keep integration/workflow tests together in the last file
- Target ≤8 (not just ≤10) for a safety margin

### 3. Create split files with ADR-009 header

Each new file MUST include this header comment:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Name files with `_part1`, `_part2`, etc. suffix:

```
test_tensor_factory.mojo → test_tensor_factory_part1.mojo
                           test_tensor_factory_part2.mojo
                           test_tensor_factory_part3.mojo
                           test_tensor_factory_part4.mojo
```

### 4. Each split file needs its own `main()` function

```mojo
fn main() raises:
    """Run all tests."""
    test_zeros_tensor_float32()
    test_zeros_tensor_int32()
    # ... all tests in this file
```

### 5. Delete the original file

```bash
rm tests/path/to/test_file.mojo
```

### 6. Verify test counts

```bash
grep -c "^fn test_" tests/path/to/test_file_part*.mojo
# Each file should show ≤8
```

### 7. Check CI workflow glob patterns

Check if CI uses glob patterns or explicit filenames:

```bash
grep -r "test_tensor_factory\|testing/test_" .github/workflows/
```

- **Glob pattern** (`testing/test_*.mojo`): No changes needed — new files auto-discovered
- **Explicit filenames**: Update workflow to reference new `_part1`, `_part2`, etc. filenames

### 8. Commit and push

```bash
git add tests/path/to/test_file.mojo tests/path/to/test_file_part*.mojo
git commit -m "fix(ci): split test_file.mojo into N files (ADR-009)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Updating CI workflow pattern | Checked `comprehensive-tests.yml` for explicit filename references | Not needed — workflow already used `testing/test_*.mojo` glob | Always check if CI uses globs before modifying workflow files |
| Using `_part_1` naming | Considered underscore-number naming | Would sort inconsistently | Use `_part1`, `_part2` (no underscore before number) |
| Keeping original file | Thought about keeping original with reduced tests | Would still trigger heap corruption for the remaining tests | Delete the original entirely and fully redistribute tests |

## Results & Parameters

### Split Distribution for 28-test File

| File | Tests | Content |
|------|-------|---------|
| `*_part1.mojo` | 8 | `zeros_tensor` + `ones_tensor` tests |
| `*_part2.mojo` | 8 | `full_tensor` + `random_tensor` tests |
| `*_part3.mojo` | 8 | `random_normal_tensor` + `set_tensor_value` (first half) |
| `*_part4.mojo` | 4 | `set_tensor_value` (second half) + integration tests |

### ADR-009 Compliance Formula

```
files_needed = ceil(total_tests / 8)  # target ≤8 per file
tests_per_file ≤ 8                    # safety margin below the 10-test limit
```

### Pre-commit Hook Behavior

Pre-commit hooks (Mojo format, validate_test_coverage) pass automatically for split files with no extra configuration.

### Key Imports per File

Only import what each file needs — don't copy all imports from the original:

```mojo
from shared.testing.tensor_factory import (
    zeros_tensor,   # only functions tested in this file
    ones_tensor,
)
```

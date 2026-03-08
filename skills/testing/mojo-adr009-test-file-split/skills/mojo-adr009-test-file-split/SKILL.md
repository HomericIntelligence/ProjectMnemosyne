---
name: mojo-adr009-test-file-split
description: "Split Mojo test files exceeding the ADR-009 limit of ≤10 fn test_ functions per file to prevent heap corruption crashes. Use when: test file has >10 fn test_ functions, CI fails intermittently with libKGENCompilerRTShared.so JIT fault, or implementing ADR-009."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 has a JIT heap corruption bug (`libKGENCompilerRTShared.so`) triggered under high test load |
| **Symptom** | CI groups fail non-deterministically (13/20 runs) with no code changes |
| **Root Cause** | Too many `fn test_` functions compiled in a single Mojo test file |
| **Fix** | ADR-009: ≤10 `fn test_` functions per file (target: ≤8 for safety margin) |
| **Pattern** | Split into N part files, each with ~7-8 tests |

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- CI fails intermittently with `libKGENCompilerRTShared.so` JIT fault errors
- A CI group has `continue-on-error: true` due to heap corruption workaround
- Implementing ADR-009 heap corruption workaround in this project

## Verified Workflow

### Step 1: Count tests in the file

```bash
grep -c '^fn test_' tests/path/to/test_file.mojo
```

If count > 10, proceed with split.

### Step 2: Plan the split

- Target ≤8 tests per file (safety margin below the 10 limit)
- Group related tests together (e.g., forward pass tests, backward pass tests, gradient checks)
- Name files `test_<base>_part1.mojo`, `test_<base>_part2.mojo`, etc.

### Step 3: Add ADR-009 header to each new file

Every split file MUST begin with:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Step 4: Split tests preserving all imports

Each part file needs its own complete import block. Copy the full import section
from the original file and trim to only the imports actually used in that part.

### Step 5: Each part file needs its own `run_all_tests()` and `main()`

```mojo
fn run_all_tests() raises:
    """Run all loss function tests (Part N)."""
    print("=" * 60)
    print("Test Suite - Part N (Description)")
    print("=" * 60)

    test_function_1()
    test_function_2()
    # ...

    print("=" * 60)
    print("All Part N tests passed! ✓")
    print("=" * 60)


fn main() raises:
    """Entry point for tests (Part N)."""
    run_all_tests()
```

### Step 6: Delete the original file

```bash
git rm tests/path/to/test_file.mojo
```

### Step 7: Update CI workflow

In `.github/workflows/comprehensive-tests.yml`, update the test group pattern:

```yaml
# Before (with workaround)
- name: "Core Loss"
  path: "tests/shared/core"
  pattern: "test_losses.mojo test_loss_funcs.mojo test_loss_utils.mojo"
  continue-on-error: true

# After (fixed)
- name: "Core Loss"
  path: "tests/shared/core"
  pattern: "test_losses_part1.mojo test_losses_part2.mojo test_losses_part3.mojo test_losses_part4.mojo test_loss_funcs.mojo test_loss_utils.mojo"
```

Note: Remove `continue-on-error: true` — it was only needed due to heap corruption.

### Step 8: Verify the split

```bash
for f in tests/path/test_*_part*.mojo; do
    echo "$f: $(grep -c '^fn test_' "$f") tests"
done
```

All files should show ≤8 tests.

### Step 9: Commit

Pre-commit hooks will run `mojo format` automatically. All hooks should pass.

```bash
git add tests/path/test_*_part*.mojo .github/workflows/comprehensive-tests.yml
git rm tests/path/test_original.mojo
git commit -m "fix(ci): split test_X.mojo into N files per ADR-009"
```

## Results & Parameters

**Session results** (test_losses.mojo split, 2026-03-07):

- Original: 28 `fn test_` functions in one file
- Split into: 4 part files × 7 tests = 28 tests total (all preserved)
- ADR-009 limit: ≤10 per file; actual: 7 per file (30% safety margin)
- Pre-commit hooks: all passed (mojo format, YAML, validate test coverage)
- `continue-on-error: true` removed from CI workflow

**Grouping strategy used**:

| Part | Tests | Description |
|------|-------|-------------|
| part1 | 7 | BCE forward + MSE forward + numerical stability |
| part2 | 7 | BCE/MSE backward gradients + Smooth L1 forward/backward |
| part3 | 7 | Smooth L1 gradient check + Hinge loss + Focal perfect |
| part4 | 7 | Focal loss + KL Divergence forward/backward |

**Key config**:

- Target per file: ≤8 tests (not ≤10, for safety margin)
- Header comment: required in every split file
- Imports: each file has complete, trimmed import block
- `run_all_tests()` + `main()`: required in every split file

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `continue-on-error: true` | Marked Core Loss CI group as non-fatal | Masked real failures, did not fix root cause | Workarounds hide problems; fix the root cause |
| Keeping 10 tests per file (at limit) | Setting exactly at the ADR-009 limit | Risky — edge cases could still trigger corruption | Use ≤8 (70-80% of limit) for a safety margin |
| Splitting imports per-test | Trying to import only what each test needs | Added complexity; Mojo imports are file-scoped | Copy full import block, trim unused — simpler |

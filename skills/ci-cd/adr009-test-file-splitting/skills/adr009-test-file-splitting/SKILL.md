---
name: adr009-test-file-splitting
description: "Split Mojo test files exceeding ADR-009 limit (≤10 fn test_ functions) to prevent heap corruption in Mojo v0.26.1. Use when: CI shows non-deterministic libKGENCompilerRTShared.so crashes, a test file exceeds the fn test_ limit, or Models CI group fails intermittently."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| **Problem** | Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault) under high test load |
| **Root Cause** | Too many `fn test_` functions in a single `.mojo` file triggers memory corruption |
| **ADR-009 Limit** | ≤10 `fn test_` functions per file (target: ≤8 for safety margin) |
| **Fix** | Split oversized test files into numbered part files |
| **CI Impact** | Eliminates non-deterministic Models CI group failures |

## When to Use

- A `.mojo` test file has more than 10 `fn test_` functions
- CI shows intermittent `libKGENCompilerRTShared.so` segfaults on Mojo test runs
- The `Models` CI group (or other Mojo test groups) fail non-deterministically
- `grep -c "^fn test_" tests/models/test_<model>_layers.mojo` returns > 10
- Adding new tests would push a file over the 10-function limit

## Verified Workflow

### Step 1: Identify Oversized Files

```bash
# Find all test files exceeding the limit
for f in tests/**/*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  if [ "$count" -gt 10 ]; then
    echo "$count $f"
  fi
done
```

### Step 2: Plan the Split

- Target ≤8 tests per file (leaves buffer below the 10-function limit)
- Group tests logically: initialization → forward → backward, or by feature area
- All shared structs and helper functions must be duplicated in each part file

### Step 3: Create Part Files

Each part file MUST include:

1. **ADR-009 header comment** at the very top:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

2. **All imports** from the original file
3. **All shared structs and helper functions** (must be duplicated — no cross-file imports between test files)
4. **A subset of tests** (≤8 `fn test_` functions)
5. **A `main()` function** that runs only the tests in this part

### Step 4: Delete the Original File

```bash
rm tests/models/test_<model>_layers.mojo
```

### Step 5: Update CI Workflow

The `comprehensive-tests.yml` `Models` group uses `test_*_layers.mojo` pattern. Part files like
`test_googlenet_layers_part1.mojo` do NOT match this glob. Update the pattern explicitly:

```yaml
- name: "Models"
  path: "tests/models"
  pattern: "test_*_layers.mojo test_<model>_layers_part1.mojo test_<model>_layers_part2.mojo test_<model>_layers_part3.mojo"
```

### Step 6: Verify and Commit

```bash
# Verify test counts
grep -c "^fn test_" tests/models/test_<model>_layers_part*.mojo

# Verify total test count matches original
grep "^fn test_" tests/models/test_<model>_layers_part*.mojo | wc -l

# Run pre-commit (validate_test_coverage.py runs automatically)
just pre-commit

# Commit with ADR reference
git commit -m "fix(ci): split test_<model>_layers.mojo into N parts (ADR-009)"
```

## Key Architectural Detail: Helper Function Duplication

Because Mojo test files cannot import from each other, any shared structs or helper functions
(e.g., `InceptionModule`, `concatenate_depthwise`) must be **duplicated** into every part file
that uses them. This is intentional and expected — do not try to factor them out.

## CI Pattern Mismatch Gotcha

The `Models` group pattern `test_*_layers.mojo` matches `test_googlenet_layers.mojo` but NOT
`test_googlenet_layers_part1.mojo`. After splitting, the CI pattern must be updated to explicitly
list the part files, or the `validate_test_coverage.py` script will flag them as uncovered.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Relying on glob pattern | Assumed `test_*_layers.mojo` would match `test_googlenet_layers_part1.mojo` | Pattern requires `_layers.mojo` suffix; `_part1.mojo` doesn't match | Must explicitly list part files in CI pattern |
| Cross-file imports | Considered importing `InceptionModule` from part1 in part2 | Mojo test files cannot import from each other (no test module system) | Duplicate shared structs/helpers in each part file |
| Keeping original file | Considered keeping original alongside parts | Would double-count tests and re-introduce heap corruption | Delete original; replace completely with parts |

## Results & Parameters

### Splitting Strategy for 18-Test File

```
Part 1 (8 tests): inception module init/forward, branch forward passes, concat shape
Part 2 (6 tests): concatenation values, initial conv block, global avgpool, FC layer
Part 3 (4 tests): backward passes for all conv branches + concatenation gradient
```

### Validate Test Coverage Script

The project's `scripts/validate_test_coverage.py` automatically validates that all `.mojo` test
files are referenced in `comprehensive-tests.yml`. Run it to verify the split is correct:

```bash
python scripts/validate_test_coverage.py
```

### ADR-009 Header Template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

---
name: mojo-test-file-splitting
description: 'Split oversized Mojo test files to comply with ADR-009 heap corruption
  workaround. Use when: a test file has >10 fn test_ functions, CI shows intermittent
  libKGENCompilerRTShared.so crashes, or a Mojo test file must be divided while preserving
  all tests and updating CI workflow references.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | Mojo v0.26.1 has a heap corruption bug triggered by high test load (>10 `fn test_` functions per file), causing non-deterministic CI failures (`libKGENCompilerRTShared.so` JIT fault) |
| **Workaround** | ADR-009 mandates ≤10 `fn test_` functions per file |
| **Solution** | Split large test files into multiple parts, update CI workflow patterns |
| **Trigger** | Any Mojo test file exceeding 10 `fn test_` functions |

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- CI is showing intermittent, non-deterministic failures in a specific test group
- The failure pattern is load-dependent (more tests = more crashes)
- You need to comply with ADR-009 (`docs/adr/ADR-009-heap-corruption-workaround.md`)
- Target: ≤8 tests per file (leave headroom below the 10-function limit)

## Verified Workflow

### 1. Count tests in the target file

```bash
grep -c "^fn test_" tests/shared/core/test_target.mojo
```

### 2. Plan the split

Divide tests into groups of ≤8. For 22 tests, create 3 files:

- Part 1: 8 tests
- Part 2: 8 tests
- Part 3: 6 tests

### 3. Create split files with ADR-009 header

Each new file MUST start with this comment block:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### 4. Duplicate helper functions in each part file

Each part file is standalone — shared helper functions (e.g. `identity_op`, `add_op`) must be
redefined in every part file. There is no shared import mechanism for test helpers in Mojo.

### 5. Each part file needs its own `fn main()` runner

```mojo
fn main() raises:
    """Run dtype_dispatch part1 tests."""
    print("Running <name>_part1 tests...")
    test_foo()
    print("✓ test_foo")
    # ...
    print("\nAll N <name>_part1 tests passed!")
```

### 6. Delete the original file

```bash
rm tests/shared/core/test_target.mojo
```

### 7. Update CI workflow

In `.github/workflows/comprehensive-tests.yml`, replace the original filename with the
three new filenames in the relevant test group's `pattern:` field:

```yaml
# Before:
pattern: "... test_target.mojo ..."

# After:
pattern: "... test_target_part1.mojo test_target_part2.mojo test_target_part3.mojo ..."
```

### 8. Check validate_test_coverage.py

```bash
grep "test_target" scripts/validate_test_coverage.py
```

If the script references the old filename by name, update it. Often it uses glob patterns
and requires no changes.

### 9. Commit and push

```bash
git add tests/shared/core/test_target_part*.mojo \
        tests/shared/core/test_target.mojo \
        .github/workflows/comprehensive-tests.yml
git commit -m "fix(ci): split test_target.mojo into 3 files (ADR-009)"
git push -u origin <branch>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Import shared helpers | Tried to import helper functions from a shared conftest | Mojo test helpers can't be imported across test files the same way Python conftest works | Redefine helpers in each part file |
| Single-file solution | Considered grouping tests into structs or namespaces | ADR-009 specifically counts `fn test_` functions regardless of grouping | Must use separate files |
| Keep original + add new | Thought the original could be kept alongside split files | Would double-run the 22 tests and exceed limits again | Delete the original file |

## Results & Parameters

### Split Ratios (22 tests → 3 files)

```text
Part 1: 8 tests  (unary + binary float dispatch)
Part 2: 8 tests  (binary int/mismatch, scalar, float-unary)
Part 3: 6 tests  (float-binary, float-scalar, 2D tensors)
Total:  22 tests preserved, 0 deleted
```

### ADR-009 Header Template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### CI Workflow Pattern Update

```yaml
# In .github/workflows/comprehensive-tests.yml
# Replace single filename with part filenames in the pattern field:
pattern: "... test_foo_part1.mojo test_foo_part2.mojo test_foo_part3.mojo ..."
```

### Pre-commit hooks that run on Mojo files

- `mojo format` — auto-formats code (runs automatically)
- `Check for deprecated List[Type](args) syntax` — catches anti-patterns
- `Validate Test Coverage` — verifies test count badges and coverage scripts

---
name: mojo-logical-xor-test-coverage
description: 'Add logical_xor test coverage for Mojo elementwise operations. Use when:
  (1) a logical op is imported but untested, (2) the file is at the per-file test limit
  and a new file is needed, (3) binary logical truth-table coverage is missing.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-logical-xor-test-coverage |
| **Category** | testing |
| **Origin** | Issue #4145 – logical_xor imported but untested |
| **Language** | Mojo v0.26.1 |

## When to Use

- A Mojo elementwise function is imported in a test file but has no corresponding `fn test_*` functions
- The existing test file is at the per-file test limit (≤10 `fn test_` functions) and cannot receive more tests
- You need to add binary logical operation (AND/OR/XOR/NAND) truth-table coverage
- Following a file split that revealed pre-existing coverage gaps

## Verified Workflow

### Quick Reference

```bash
# 1. Identify the gap
grep -n "logical_xor" tests/shared/core/test_elementwise_part5.mojo
# Found in imports, zero fn test_logical_xor_* functions

# 2. Count existing tests in the file
grep -c "^fn test_" tests/shared/core/test_elementwise_part5.mojo
# Returns 10 → at limit, must create new file

# 3. Create new test file
# tests/shared/core/test_elementwise_logical_xor.mojo
```

### Step 1 – Identify the Gap

Grep for the function name in existing test imports vs. test function definitions:

```bash
grep -n "logical_xor" tests/shared/core/test_elementwise_part5.mojo
# Appears only in the import block — no fn test_logical_xor_*
```

### Step 2 – Check Per-File Test Limit

```bash
grep -c "^fn test_" tests/shared/core/test_elementwise_part5.mojo
# 10 → at limit; new file required
```

Keep each Mojo test file to ≤10 `fn test_` functions to avoid
`libKGENCompilerRTShared.so` heap corruption in Mojo v0.26.1.

### Step 3 – Read the Implementation Signature

```bash
grep -n "fn logical_xor" shared/core/elementwise.mojo
# fn logical_xor(a: ExTensor, b: ExTensor) raises -> ExTensor:
```

### Step 4 – Create the Test File

Follow the header comment and import pattern from `test_elementwise_part5.mojo` exactly:

```mojo
"""Tests for elementwise logical_xor operation.
...
"""

from tests.shared.conftest import (
    assert_almost_equal,
    assert_equal,
    assert_true,
)
from shared.core.extensor import ExTensor, zeros
from shared.core.elementwise import logical_xor
```

### Step 5 – Write the 5 Core Tests

| Test | What It Verifies |
| ------ | ----------------- |
| `test_logical_xor_values` | Full truth table: (F,F)→F, (F,T)→T, (T,F)→T, (T,T)→F |
| `test_logical_xor_shape_preserved` | Output shape matches input |
| `test_logical_xor_all_false` | zeros XOR zeros → all zeros |
| `test_logical_xor_all_true` | ones XOR ones → all zeros (T XOR T = F) |
| `test_logical_xor_identity` | A XOR 0 = bool(A) |

Truth-table test pattern (mirror of `test_logical_and_values`):

```mojo
fn test_logical_xor_values() raises:
    """Truth table: (F,F)→F, (F,T)→T, (T,F)→T, (T,T)→F."""
    var shape = List[Int]()
    shape.append(4)
    var a = zeros(shape, DType.float32)
    var b = zeros(shape, DType.float32)

    # a = [0, 0, 1, 1], b = [0, 1, 0, 1]
    a._data.bitcast[Float32]()[0] = 0.0
    a._data.bitcast[Float32]()[1] = 0.0
    a._data.bitcast[Float32]()[2] = 1.0
    a._data.bitcast[Float32]()[3] = 1.0
    b._data.bitcast[Float32]()[0] = 0.0
    b._data.bitcast[Float32]()[1] = 1.0
    b._data.bitcast[Float32]()[2] = 0.0
    b._data.bitcast[Float32]()[3] = 1.0

    var result = logical_xor(a, b)

    # XOR truth table: [0, 1, 1, 0]
    assert_almost_equal(result._data.bitcast[Float32]()[0], Float32(0.0), tolerance=1e-5)
    assert_almost_equal(result._data.bitcast[Float32]()[1], Float32(1.0), tolerance=1e-5)
    assert_almost_equal(result._data.bitcast[Float32]()[2], Float32(1.0), tolerance=1e-5)
    assert_almost_equal(result._data.bitcast[Float32]()[3], Float32(0.0), tolerance=1e-5)
```

### Step 6 – Add main() Runner

```mojo
fn main() raises:
    """Run logical_xor elementwise operation tests."""
    print("Running logical_xor elementwise operation tests...")

    test_logical_xor_values()
    print("✓ test_logical_xor_values")

    test_logical_xor_shape_preserved()
    print("✓ test_logical_xor_shape_preserved")

    test_logical_xor_all_false()
    print("✓ test_logical_xor_all_false")

    test_logical_xor_all_true()
    print("✓ test_logical_xor_all_true")

    test_logical_xor_identity()
    print("✓ test_logical_xor_identity")

    print("\nAll logical_xor tests passed!")
```

### Step 7 – Commit and PR

```bash
git add tests/shared/core/test_elementwise_logical_xor.mojo
git commit -m "test(elementwise): add logical_xor coverage

Closes #4145"
git push -u origin 4145-auto-impl

gh pr create \
  --title "test(elementwise): add logical_xor coverage" \
  --body "Closes #4145" \
  --label "testing"

gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Add tests to part5 | Append `fn test_logical_xor_*` to existing `test_elementwise_part5.mojo` | File already at the 10-test per-file limit | Always count existing tests before editing; create new file if at limit |
| Use `logical_xor` import from part5 without checking signature | Assumed same 2-tensor signature as logical_and | N/A (worked) — but skipping the grep would risk wrong args | Always verify function signature from source before writing tests |

## Results & Parameters

```text
File created: tests/shared/core/test_elementwise_logical_xor.mojo
Tests added:  5  (well under the 10-test per-file limit)
PR:           #4874
Issue closed: #4145
Branch:       4145-auto-impl
```

Key config values:

```text
Max fn test_ per file: 10
Reason:                libKGENCompilerRTShared.so heap corruption in Mojo v0.26.1
Workaround:            Split into multiple files, each ≤10 tests
```

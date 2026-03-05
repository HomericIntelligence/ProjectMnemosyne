---
name: mojo-dtype-partial-support-guard
description: "Diagnose and guard against partially-supported Mojo DTypes where the type exists but runtime value operations silently fail. Use when: CI shows 'Element 0 = 0.0, expected N.N' after enabling a previously-skipped dtype test, or DType.bfloat16 tensors return zeros despite explicit value assignment."
category: debugging
date: 2026-03-05
user-invocable: false
---

# Skill: Mojo DType Partial Support Guard

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Category** | debugging |
| **Objective** | Detect when a Mojo DType is in the type system but not fully supported at runtime |
| **Outcome** | Reverted premature test enablement; documented partial BF16 support limitation |
| **Context** | Issue #3088 - [Cleanup] Document BF16 type alias limitation |

## When to Use

Use this skill when:

- A previously-skipped dtype test (e.g. `DType.bfloat16`) is re-enabled and CI fails with value mismatch
- CI output shows: `Element 0 = 0.0, expected 1.0 (exact match required for special values)`
- A dtype type-checks at compile time but produces zero/garbage values at runtime
- You are removing a "TODO: enable when Mojo supports X" comment and need to verify runtime completeness
- `assert_dtype` passes but `verify_special_value_invariants` fails for the same tensor

Do NOT use when:

- The test fails due to a genuine logic bug unrelated to dtype support
- The dtype is known-broken at the compiler level (compile error, not runtime zero)
- Tests fail due to Apple Silicon hardware limitation (separate from runtime API coverage)

## The Partial Support Pattern

Mojo's `DType.bfloat16` (and potentially other recently-added dtypes) can be **partially supported**:

```
Compile-time type system:   ✅  DType.bfloat16 exists, compiles fine
assert_dtype check:         ✅  tensor.dtype() == DType.bfloat16 passes
_set_float64(i, value):     ❌  silently writes 0.0 instead of value
_get_float64(i):            ❌  reads back 0.0 instead of stored value
```

The key symptom: `create_special_value_tensor([2,2], DType.bfloat16, 1.0)` creates a tensor
that reports `DType.bfloat16` but all elements read as `0.0`.

## Verified Workflow

### 1. Identify the Failure Pattern in CI Logs

```bash
gh run view <run-id> --log-failed 2>/dev/null | grep -E "(✓|✅|❌|error|Element)"
```

Look for this specific signature:
```
✓ test_dtypes_float16
Unhandled exception caught during execution: Element 0 = 0.0, expected 1.0
/path/to/mojo: error: execution exited with a non-zero result: 1
❌ FAILED: tests/.../test_special_values.mojo
```

The dtype test immediately before the failure is the culprit.

### 2. Distinguish Full vs Partial Support

| Check | Full Support | Partial Support |
|-------|-------------|-----------------|
| `DType.bfloat16` compiles | ✅ | ✅ |
| `tensor.dtype() == DType.bfloat16` | ✅ | ✅ |
| `tensor._set_float64(i, 1.0)` | ✅ stores 1.0 | ❌ stores 0.0 |
| `tensor._get_float64(i)` returns 1.0 | ✅ | ❌ returns 0.0 |

### 3. Revert to Properly-Documented Skip

Replace the enabled test body with a `pass` and a clear TODO:

```mojo
fn test_dtypes_bfloat16() raises:
    """Test special values work with bfloat16.

    DType.bfloat16 is available in Mojo, but ExTensor's _set_float64/_get_float64
    path does not correctly round-trip values through bfloat16 storage, so this
    test is skipped until the ExTensor float64 read/write path supports bfloat16.

    Note:
        DType.bfloat16 is also not supported on Apple Silicon hardware.

    TODO: Enable when ExTensor._set_float64/_get_float64 correctly handle bfloat16.
        var tensor = create_special_value_tensor([2, 2], DType.bfloat16, 1.0)
        assert_dtype(tensor, DType.bfloat16, "Should be bfloat16")
        verify_special_value_invariants(tensor, 1.0)
    """
    pass
```

Key differences from the original (wrong) skip:
- **DO** name the specific functions that don't work (`_set_float64/_get_float64`)
- **DO** include the test code as a comment so future fixers know exactly what to uncomment
- **DON'T** say "DType.bfloat16 not supported" — the type IS supported, just not the I/O path

### 4. Update the Print Message

```mojo
    test_dtypes_bfloat16()
    print("✓ test_dtypes_bfloat16 (skipped - bfloat16 float64 read/write not yet supported)")
```

### 5. Check If CI Failures Are Pre-Existing

Before concluding your change caused CI failures, compare against recent main CI:

```bash
# Get recent main branch run IDs
gh run list --branch main --workflow "Comprehensive Tests" --limit 3 --json databaseId,conclusion

# Check which jobs failed on a specific run
gh run view <run-id> --json jobs 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for j in data.get('jobs', []):
    if j.get('conclusion') not in ('success', 'skipped'):
        print(j['name'], j.get('conclusion', 'N/A'))
"
```

If `Testing Fixtures`, `Data Datasets`, and `Fuzz Tests` all pass on main but fail on your PR,
the failures are introduced by your change.

### 6. Commit the Fix

```bash
git add tests/shared/testing/test_special_values.mojo
git commit -m "fix(tests): skip bfloat16 special values test until float64 path fixed

DType.bfloat16 is natively available in Mojo, but ExTensor's
_set_float64/_get_float64 path does not correctly round-trip values
through bfloat16 storage (reads back 0.0 instead of expected 1.0).

Skip the test body with a clear TODO documenting what needs to be fixed
before the test can be re-enabled, rather than having it fail in CI."
```

## Remote Branch Divergence Recovery

When the remote branch has been force-updated while you have local commits:

```bash
# Fetch remote state
git fetch origin <branch>

# Rebase local commits on top of remote (preserves your fix)
git rebase origin/<branch>

# Push (now fast-forward)
git push origin <branch>
```

Do NOT use `git pull --rebase` when the remote was force-pushed — use `git rebase origin/<branch>` directly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Enable test with real assertions | Uncomment BF16 test body assuming native DType support = full runtime support | `_set_float64`/`_get_float64` don't handle bfloat16 storage, silently write zeros | Type existing in DType enum ≠ full runtime I/O support across all paths |
| Assuming CI failures were pre-existing | Didn't check main branch CI first | Main branch had all tests passing; failures were introduced by the PR | Always compare failing CI jobs against recent main before concluding pre-existing |
| Force-push to recover from remote divergence | Not attempted (correctly avoided) | Would overwrite remote history | Use `git rebase origin/<branch>` then regular push |

## Results & Parameters

### BF16 Support Status (2026-03-05)

```
DType.bfloat16:              ✅ Available in type system
Tensor dtype assertion:      ✅ Works (assert_dtype passes)
_set_float64 / _get_float64: ❌ Silent failure - writes/reads zeros
Apple Silicon:               ❌ Not supported at all
```

### Files Affected

```text
tests/shared/testing/test_special_values.mojo
  - test_dtypes_bfloat16(): reverted to pass + detailed TODO
  - main(): updated print message
```

### How to Re-Enable When Fixed

When `ExTensor._set_float64` and `_get_float64` properly handle bfloat16:

1. Uncomment the 3 test lines inside `test_dtypes_bfloat16()`
2. Remove the `pass` statement
3. Update the print message to remove "(skipped - ...)"
4. Verify in CI that `Testing Fixtures` passes

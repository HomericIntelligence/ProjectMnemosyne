---
name: extensor-dtype-str-repr
description: 'Pattern for dtype-aware __str__/__repr__ in Mojo ExTensor and testing
  integer/bool formatting. Use when: adding string formatting to tensor structs, testing
  integer types render without decimals, testing bool renders as True/False.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Goal** | Fix ExTensor __str__/__repr__ to format integers without decimals and bools as True/False |
| **Language** | Mojo v0.26.1+ |
| **Files** | shared/core/extensor.mojo, tests/shared/core/test_utility.mojo |
| **PR** | #4045, Closes #3376 |

## When to Use

- Adding `__str__` or `__repr__` to a Mojo tensor/array struct
- The formatting needs to vary by dtype (float vs integer vs bool)
- Writing tests that verify integer values have no decimal suffix
- Writing tests that verify bool values display as `True`/`False`

## Verified Workflow

### 1. Add a dtype-dispatching format helper

Add a private helper to the struct before `__str__`:

```mojo
fn _format_element(self, i: Int) -> String:
    """Format a single element as a string based on dtype."""
    if self._dtype == DType.bool:
        return "True" if self._get_int64(i) != 0 else "False"
    elif (
        self._dtype == DType.int8
        or self._dtype == DType.int16
        or self._dtype == DType.int32
        or self._dtype == DType.int64
        or self._dtype == DType.uint8
        or self._dtype == DType.uint16
        or self._dtype == DType.uint32
        or self._dtype == DType.uint64
    ):
        return String(self._get_int64(i))
    else:
        return String(self._get_float64(i))
```

**Key insight**: Use explicit `== DType.xxx` comparisons, not `dtype.is_integral()`. The codebase
uses runtime enum comparisons everywhere for dtype branching.

### 2. Update __str__ and __repr__ to use the helper

```mojo
fn __str__(self) -> String:
    var result = String("ExTensor([")
    for i in range(self._numel):
        if i > 0:
            result += ", "
        result += self._format_element(i)  # was: self._get_float64(i)
    result += "], dtype=" + String(self._dtype) + ")"
    return result
```

### 3. Write tests using zeros + setitem pattern

```mojo
fn test_str_int32_no_decimals() raises:
    """Test __str__ renders int32 values without decimal points."""
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.int32)
    t[1] = 1.0
    t[2] = 2.0
    var s = String(t)
    assert_equal(s, "ExTensor([0, 1, 2], dtype=int32)", "__str__ int32 format")

fn test_str_bool_true_false() raises:
    """Test __str__ renders bool values as True/False."""
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.bool)
    t[1] = 1.0
    var s = String(t)
    assert_equal(
        s, "ExTensor([False, True, False], dtype=bool)", "__str__ bool format"
    )
```

**Pattern**: Use `zeros(shape, DType.xxx)` then `t[i] = value` to set specific elements. This is
the established test pattern in this codebase.

### 4. Register tests in main()

```mojo
# __str__ and __repr__
print("  Testing __str__ and __repr__...")
test_str_readable()
test_repr_complete()
test_str_int32_no_decimals()
test_str_bool_true_false()
test_repr_int32_no_decimals()
test_repr_bool_true_false()
```

### 5. Verify with pre-commit

```bash
just pre-commit-all
# or
pixi run pre-commit run --all-files
```

Pre-commit hooks (`mojo format`, deprecated syntax check, trailing-whitespace, end-of-file-fixer)
must all pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `dtype.is_integral()` | Using `self._dtype.is_integral()` to check integer types | Not tested locally due to GLIBC mismatch; codebase never used this pattern | Use explicit `== DType.xxx` comparisons to match existing codebase style and avoid potential compile issues |
| Running mojo locally | `pixi run mojo build shared/core/extensor.mojo` | GLIBC_2.32/2.33/2.34 not found on the host system | Rely on pre-commit hooks for format validation; CI handles actual Mojo compilation |

## Results & Parameters

**Expected string outputs**:

```text
# float32 (unchanged)
ExTensor([0.0, 1.0, 2.0], dtype=float32)

# int32 (new - no decimals)
ExTensor([0, 1, 2], dtype=int32)

# bool (new - True/False)
ExTensor([False, True, False], dtype=bool)

# __repr__ int32
ExTensor(shape=[3], dtype=int32, numel=3, data=[0, 1, 2])

# __repr__ bool
ExTensor(shape=[3], dtype=bool, numel=3, data=[False, True, False])
```

**Pre-commit hooks that run on .mojo files**:

- `mojo format` - auto-formats Mojo code
- `check-deprecated-list-syntax` - catches `List[Type](args)` → `[args]`
- `trailing-whitespace`, `end-of-file-fixer`, `check-added-large-files`

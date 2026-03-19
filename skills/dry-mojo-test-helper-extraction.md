---
name: dry-mojo-test-helper-extraction
description: 'Extract duplicated Mojo test tensor setup into a private helper returning
  a tuple. Use when: two or more test functions share identical tensor construction
  blocks, or when planning to add test variants that would repeat the same setup.'
category: architecture
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-15 |
| **Objective** | Reduce duplication in Mojo test files by extracting repeated tensor setup into a private helper function |
| **Outcome** | -10 net lines, identical behavior, no new `fn test_` functions added (ADR-009 limit respected) |
| **Project** | ProjectOdyssey |
| **Issue** | #3870 (follow-up from #3281) |

## When to Use

- Two or more `fn test_*` functions in a Mojo file open with identical tensor shape lists, `zeros()`/`ones()` calls, and initialization loops
- A new test variant (e.g., padding or stride) would copy-paste the same setup block
- Applying DRY principle to a numerical gradient test suite
- The file has an ADR-009 cap on the number of `fn test_` functions — you cannot add a new test, but you can add a private helper

## Verified Workflow

### Quick Reference

```mojo
# Before: duplicated in each test function
var input_shape = List[Int]()
input_shape.append(1)
...
var x = zeros(input_shape, DType.float32)
for i in range(16):
    x._data.bitcast[Float32]()[i] = Float32(i) * 0.1
# ... kernel + bias setup repeated verbatim

# After: single helper
fn _make_test_conv2d_tensors() raises -> (ExTensor, ExTensor, ExTensor):
    """Create standard (1,1,4,4) input, (1,1,3,3) kernel, and (1,) bias tensors."""
    ...
    return (x, kernel, bias)

# In each test:
var tensors = _make_test_conv2d_tensors()
var x = tensors[0]
var kernel = tensors[1]
var bias = tensors[2]
```

### Step 1 — Identify the duplicated block

Read the test file and confirm both functions have byte-for-byte identical setup (shape lists, zero initialization, element-wise loops).

### Step 2 — Name the helper

Use the convention `_make_test_<operation>_tensors()` (leading underscore = private, not a test entry point). Return a tuple matching the tensor order used by callers.

### Step 3 — Write the helper above the first consumer

Place the helper immediately before the first test function that uses it. This keeps the code readable in file order.

The helper signature:

```mojo
fn _make_test_conv2d_tensors() raises -> (ExTensor, ExTensor, ExTensor):
    """Create standard (1,1,4,4) input, (1,1,3,3) kernel, and (1,) bias tensors.

    Returns:
        Tuple of (input, kernel, bias) tensors with non-uniform values for
        meaningful gradient checking.
    """
```

### Step 4 — Replace the duplicated block in each consumer

```mojo
var tensors = _make_test_conv2d_tensors()
var x = tensors[0]
var kernel = tensors[1]
var bias = tensors[2]
```

### Step 5 — Verify ADR-009 compliance

Count `fn test_` functions. The helper is `fn _make_...` so it does NOT count toward the limit. The file's test count is unchanged.

### Step 6 — Commit with DRY rationale

```bash
git commit -m "refactor(tests): extract _make_test_conv2d_tensors() helper to reduce duplication

Both numerical gradient test functions shared identical tensor construction.
Extracted into _make_test_conv2d_tensors() following DRY principle.

Closes #<issue-number>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Tuple destructuring with `var (x, kernel, bias) = ...` | Tried Python-style tuple unpacking syntax | Mojo v0.26.1 does not support destructuring assignment for tuples in `var` declarations | Use indexed access: `tensors[0]`, `tensors[1]`, `tensors[2]` |
| Placing helper after consumers | Considered inserting helper at end of file | Mojo requires forward declarations or definition-before-use; helper must appear before its callers | Always insert private helpers immediately before their first caller |

## Results & Parameters

**Net change**: 56 lines changed (+23 / -33), extracting 25 duplicate lines into 30-line helper with docstring.

**Tensor setup pattern** (copy-paste template):

```mojo
fn _make_test_<op>_tensors() raises -> (ExTensor, ExTensor, ExTensor):
    """Create standard <dims> input, <dims> kernel, and <dims> bias tensors.

    Returns:
        Tuple of (input, kernel, bias) tensors with non-uniform values for
        meaningful gradient checking.
    """
    var input_shape = List[Int]()
    input_shape.append(<batch>)
    input_shape.append(<in_channels>)
    input_shape.append(<h>)
    input_shape.append(<w>)
    var x = zeros(input_shape, DType.float32)
    for i in range(<total_elements>):
        x._data.bitcast[Float32]()[i] = Float32(i) * <scale>

    var kernel_shape = List[Int]()
    kernel_shape.append(<out_channels>)
    kernel_shape.append(<in_channels>)
    kernel_shape.append(<kh>)
    kernel_shape.append(<kw>)
    var kernel = zeros(kernel_shape, DType.float32)
    for i in range(<kernel_elements>):
        kernel._data.bitcast[Float32]()[i] = Float32(i) * <k_scale> + <k_offset>

    var bias_shape = List[Int]()
    bias_shape.append(<out_channels>)
    var bias = zeros(bias_shape, DType.float32)

    return (x, kernel, bias)
```

**Consumer pattern**:

```mojo
var tensors = _make_test_<op>_tensors()
var x = tensors[0]
var kernel = tensors[1]
var bias = tensors[2]
```

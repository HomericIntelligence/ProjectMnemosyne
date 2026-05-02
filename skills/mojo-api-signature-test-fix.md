---
name: mojo-api-signature-test-fix
description: 'Fix Mojo test files when API signatures change (missing required positional
  args, positional/keyword conflicts). Use when: tests fail with ''missing required
  positional arguments'' or ''argument passed both as positional and keyword operand''.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-api-signature-test-fix |
| **Category** | testing |
| **Trigger** | Mojo test compile errors about missing args or positional/keyword conflicts |
| **Scope** | Test files in `tests/` — never modifies the implementation |
| **Result** | Compile errors resolved, PR created |

## When to Use

- Test fails with: `error: invalid call to 'fn_name': missing N required positional arguments: 'arg1', 'arg2'`
- Test fails with: `error: invalid call to 'fn_name': argument passed both as positional and keyword operand: 'arg_name'`
- API function signatures were updated but test call sites were not updated to match
- Fixing test files discovered during `--Werror` audit passes (e.g. in batch CI fix PRs)

## Verified Workflow

### Quick Reference

```bash
# 1. Read the actual function signature
grep -n "fn function_name" shared/core/module.mojo

# 2. Read the failing test call site
# (use offset/limit to go to the reported line number)

# 3. Fix: add missing positional args before keyword args
# Fix: wrap separate tensor args in List[ExTensor](a, b) for list-taking functions

# 4. Search for ALL calls in the file (not just the first one)
grep -n "function_name" tests/path/to/test_file.mojo

# 5. Commit and push
git add <files> && git commit -m "fix(tests): ..."
gh pr create ...
```

### Step-by-Step

1. **Read the error message carefully** — it tells you the function name and which
   arguments are missing or conflicting.

2. **Read the actual function signature** from the implementation file:

   ```bash
   grep -n "fn batch_norm2d" shared/core/normalization.mojo
   # Then read the full signature with Read tool at that offset
   ```

3. **Identify the fix type**:

   **Type A — Missing required positional args**: The API added new required
   parameters. Create the necessary tensors (typically `zeros`/`ones` with the
   appropriate shape) and insert them at the correct positional position before
   any keyword arguments.

   ```mojo
   # Before (broken):
   var result = batch_norm2d(x, gamma, beta, epsilon=1e-5, training=True)

   # After (fixed): running_mean and running_var are now required
   var running_mean = zeros(param_shape, DType.float32)
   var running_var = ones(param_shape, DType.float32)
   var result = batch_norm2d(
       x, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5
   )
   ```

   **Type B — Positional/keyword conflict**: A function takes a `List[T]` as its
   first arg but the call site passes individual values positionally. Mojo
   interprets the second positional as the next parameter (e.g., `axis`), then
   the keyword `axis=N` conflicts.

   ```mojo
   # Before (broken): b is treated as positional axis, axis=1 is also keyword
   var result = concatenate(a, b, axis=1)

   # After (fixed): wrap in List
   var result = concatenate(List[ExTensor](a, b), 1)
   ```

4. **Search for ALL call sites** in the file — there are often multiple test
   functions calling the same API. Always grep for all occurrences before
   declaring done.

5. **Verify the fix compiles** by checking the argument order matches the
   signature exactly (positional args first, keyword args after, in signature order).

6. **Commit with a descriptive message** referencing the issue number.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Only fixing the first reported call site | Patched line 288 of test_normalization_part3.mojo | A second call at line 338 had the same missing-args issue | Always grep for all calls to the changed function, not just the first reported error |
| Passing `axis` as keyword with two positional tensors | `concatenate(a, b, axis=1)` | Mojo sees `b` as the positional `axis` arg (Int) and `axis=1` as a conflicting keyword | When a function takes `List[T]` as first arg, wrap separate values in `List[T](a, b)` |

## Results & Parameters

### Working call pattern for batch_norm2d (with running stats)

```mojo
var param_shape = List[Int]()
param_shape.append(C)  # number of channels
var running_mean = zeros(param_shape, DType.float32)
var running_var = ones(param_shape, DType.float32)  # ones, not zeros (variance)

var result = batch_norm2d(
    x, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5
)
```

### Working call pattern for concatenate with axis

```mojo
# Function signature: fn concatenate(tensors: List[ExTensor], axis: Int = 0)
var result = concatenate(List[ExTensor](a, b), 1)  # axis=1
```

### PR format used

```
fix(tests): pass running_mean/running_var to batch_norm2d; fix concatenate axis arg

- test_normalization_part3.mojo: Add running_mean/running_var tensors and pass
  them to batch_norm2d() and batch_norm2d_backward() calls (required positional args)
- test_shape_part4.mojo: Fix concatenate() call to pass tensors as List[ExTensor]
  instead of positional args with conflicting keyword axis argument

Closes #<issue-number>
```

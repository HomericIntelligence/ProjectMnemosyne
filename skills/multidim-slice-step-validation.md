---
name: multidim-slice-step-validation
description: 'Fix silent incorrect results when a variadic-slice __getitem__ ignores
  the step field. Use when: multi-dim tensor slicing silently returns wrong data for
  step != 1, or you need a fail-fast guard for unimplemented strided access.'
category: debugging
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| Language | Mojo |
| Component | `ExTensor.__getitem__(*slices: Slice)` |
| Issue | Silent wrong results when `step != 1` in multi-dim slice |
| Fix Strategy | Fail fast — raise `Error` for any `step != 1` |
| Scope | `shared/core/extensor.mojo` |

## When to Use

- A variadic-arg `__getitem__(*slices)` overload computes `start`/`end` from each slice but never reads `step`, so `tensor[::2, :]` silently returns every element.
- You need to choose between "raise on unsupported step" (option 1, minimal) vs "implement strided multi-dim copy" (option 2, complex).
- You want to add targeted tests proving that step != 1 is now rejected and step == 1 (explicit or default) still works.

## Verified Workflow

### Quick Reference

```mojo
# Old (buggy): step silently ignored
var start = s.start.or_else(0)
var end   = s.end.or_else(size)
# step never read — wrong results for tensor[::2, :]

# Fixed (fail fast): validate step before any other logic
for dim in range(num_dims):
    var step = slices[dim].step.or_else(1)
    if step != 1:
        raise Error(
            "Multi-dimensional slicing does not support step != 1 "
            + "(got step=" + String(step)
            + " on dimension " + String(dim)
            + "). Use 1D slicing for strided access."
        )
```

### Step 1 — Locate the overload

Search for the variadic-slice `__getitem__` signature:

```bash
grep -n "__getitem__(self, \*slices" shared/core/extensor.mojo
```

Confirm that the loop over dimensions reads `start`/`end` but not `step`.

### Step 2 — Insert step-validation loop

Add the validation **before** the existing loop that computes `starts` and `result_shape`.
Order matters: reject bad inputs early, before allocating the result tensor.

```mojo
# Reject non-unit steps: multi-dim strided slicing is not implemented.
# Silently ignoring step would produce wrong results (issue #4463).
for dim in range(num_dims):
    var step = slices[dim].step.or_else(1)
    if step != 1:
        raise Error(
            "Multi-dimensional slicing does not support step != 1 "
            + "(got step="
            + String(step)
            + " on dimension "
            + String(dim)
            + "). Use 1D slicing for strided access."
        )
```

### Step 3 — Update the docstring

Add a `Raises` entry for the new error condition:

```mojo
Raises:
    Error: If number of slices doesn't match tensor dimensions,
           or if any slice has step != 1 (not implemented).
```

### Step 4 — Write targeted tests

Create a new test file with ≤10 `fn test_` functions:

```mojo
fn test_multidim_step2_first_dim_raises() raises:
    var raised = False
    try:
        var _ = t2d[::2, :]
    except:
        raised = True
    assert_true(raised, "Expected Error for step=2 on first dim")

fn test_multidim_step1_does_not_raise() raises:
    # Explicit step=1 must succeed
    var sliced = t2d[::1, ::1]
    assert_equal(sliced.shape()[0], 5)

fn test_multidim_no_step_does_not_raise() raises:
    # Omitted step defaults to 1 — must succeed
    var sliced = t2d[1:4, 1:3]
    assert_equal(sliced.shape()[0], 3)
```

Cover: step=2 first dim, step=2 second dim, step=-1, step=3 in 3D, step=1 explicit, no step.

### Step 5 — Run tests

```bash
just test-group "tests/shared/core" "test_extensor_multidim_step.mojo"
just test-group "tests/shared/core" "test_extensor_slicing_2d.mojo"
```

Both must pass before committing.

### Step 6 — Commit and PR

```bash
git add shared/core/extensor.mojo tests/shared/core/test_extensor_multidim_step.mojo
git commit -m "fix(extensor): raise Error when multi-dim slice step != 1

Closes #4463"
git push -u origin <branch>
gh pr create --title "fix(extensor): raise Error when multi-dim slice step != 1" \
  --body "Closes #4463" --label "implementation"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Implement full strided copy | Option 2: build a strided multi-dim copy loop analogous to the 1D `__getitem__(Slice)` path | Much more complex; increases surface area with no immediate test coverage; out of scope for a bug-fix issue | When the issue explicitly offers option 1 (fail fast) and option 2 (implement), prefer option 1 unless the caller needs strided access today |
| Add step check inside existing loop | Put step validation inside the `for dim in range(num_dims)` loop that also computes `starts` | Still correct but slightly harder to read because it mixes validation with computation | Separate validation from computation: a dedicated pre-loop over dimensions is clearer and follows fail-fast idiom |

## Results & Parameters

**File changed**: `shared/core/extensor.mojo`
**Lines inserted**: ~14 (validation loop + comment)
**Test file**: `tests/shared/core/test_extensor_multidim_step.mojo`
**Test functions**: 6
**File limit**: ≤10 `fn test_` per file (respected)

**Key `or_else` pattern** — Mojo `Optional[Int]` step default:

```mojo
var step = slices[dim].step.or_else(1)  # default 1 if not set
```

**Test harness command**:

```bash
just test-group "tests/shared/core" "test_extensor_multidim_step.mojo"
```

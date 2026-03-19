---
name: mojo-test-split-compile-hang
description: "Fix Mojo test compilation hangs by splitting large test files. Use when:\
  \ a test file takes >120s to compile, has backward-pass tests alongside forward-pass\
  \ tests, or exceeds the ADR-009 \u226410 test function limit."
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 compilation hangs (>120s) when a test file instantiates too many large parametric types (e.g. FC layer backward passes with 9216→4096 weights) |
| **Solution** | Move heavyweight test functions to a sibling part file that is already under the ≤10 limit |
| **ADR** | ADR-009: test files limited to ≤10 `fn test_` functions to avoid heap corruption and compile hangs |
| **Verified on** | ProjectOdyssey — `test_alexnet_layers_part4.mojo` and `test_extensor_slicing_part3.mojo` |

## When to Use

- A Mojo test file takes >120s to compile (possible infinite template instantiation loop)
- A test file has backward-pass tests alongside forward-pass tests for large layers (FC layers with thousands of features)
- A test file is approaching or exceeding 10 `fn test_` functions
- CI times out on a specific test compilation step

## Verified Workflow

### Quick Reference

```bash
# Count test functions in a file
grep -c "^fn test_" tests/models/test_foo_part4.mojo

# Find the sibling part file with room (≤10 limit)
for f in tests/models/test_foo_part*.mojo; do
  echo "$f: $(grep -c '^fn test_' $f)"
done
```

### Step 1 — Identify the overloaded file

```bash
# Count test functions per part file
grep -n "fn test_" tests/models/test_alexnet_layers_part4.mojo
```

If a file has backward-pass tests that reference large weight matrices (FC 9216→4096, FC 4096→4096),
these are the compile-time bottleneck — each backward test instantiates heavyweight gradient checking code.

### Step 2 — Find a sibling part file with capacity

```bash
# Check all sibling part files
for f in tests/models/test_alexnet_layers_part*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  echo "$f: $count tests"
done
```

Pick a sibling with fewer than 8 tests (leaving headroom for the 2 you'll move).

### Step 3 — Move the heavyweight tests

For each test function to move:

1. **Copy the function body** from part4 to part5 (include the full `fn test_..() raises:` block)
2. **Add section comment** above the function in part5 (e.g. `# FC1 Backward - moved from part4`)
3. **Add to part5 `main()`** — insert the print + call before existing tests
4. **Delete the function body** from part4
5. **Remove the call** from part4's `main()`

### Step 4 — Update docstrings

- Update part5's module docstring to list the newly added layers
- Update part5's `main()` print statement to reflect new content
- Update part5's final success print message

### Step 5 — Verify counts

```bash
grep -c "^fn test_" tests/models/test_alexnet_layers_part4.mojo  # Should decrease
grep -c "^fn test_" tests/models/test_alexnet_layers_part5.mojo  # Should increase, ≤10
```

### Step 6 — Commit (use SKIP=mojo-format if GLIBC mismatch)

```bash
SKIP=mojo-format git commit -m "fix(tests): move backward tests from part4 to part5 to resolve compile hang"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Delete backward tests entirely | Removing `test_fc1_backward_float32` and `test_fc2_backward_float32` | Loses test coverage for backward passes | Move to sibling part, never delete |
| Split into a new part6 | Create a brand new `test_alexnet_layers_part6.mojo` | Overkill — part5 had capacity (only 6 tests out of 10) | Check existing sibling capacity first |
| Add `# TODO: split this file` comment | Document the problem without fixing it | CI still hangs | Always fix the root cause in the same PR |

## Results & Parameters

### Part4 before/after

```
Before: 8 fn test_ functions (2 backward tests causing hang)
After:  6 fn test_ functions (forward-pass only — compiles fast)
```

### Part5 before/after

```
Before: 6 fn test_ functions
After:  8 fn test_ functions (still ≤10, ADR-009 compliant)
```

### Commit message template

```
fix(tests): move <LayerName> backward tests from part<N> to part<M> to resolve compile hang

- <filename>_part<N>: remove test_<layer>_backward_float32 (N→M tests)
- <filename>_part<M>: add test_<layer>_backward_float32 (M→P tests, ≤10)

Closes #<issue>
```

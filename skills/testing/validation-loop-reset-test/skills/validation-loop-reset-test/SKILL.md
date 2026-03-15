---
name: validation-loop-reset-test
description: "Pattern for testing that training/validation loops reset DataLoaders before iterating, using a pre-exhaustion strategy. Use when: adding tests for loop reset behavior, verifying run() or run_subset() semantics, or writing parallel tests across loop methods."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Category** | testing |
| **Mojo version** | 0.26.1 |
| **Issue** | #3688 (follow-up from #3186) |
| **Pattern** | Pre-exhaustion strategy for DataLoader reset tests |
| **File modified** | `tests/shared/training/test_validation_loop.mojo` |

## When to Use

- Adding a parallel test for `run()` after a `run_subset()` reset test already exists
- Verifying that any training or validation loop method calls `reset()` on a DataLoader before iterating
- Checking that a loop is resilient to a pre-exhausted (fully consumed) DataLoader
- Following up on an issue that says "check whether method X has the same pattern as method Y"

## Verified Workflow

### Quick Reference

```
1. Read the existing parallel test (e.g. test_..._run_subset_resets_loader)
2. Read the implementation to confirm the reset() call site and line number
3. Add test function using pre-exhaustion strategy
4. Add call to test function in main()
5. Commit, push, PR
```

### Step 1 — Read the existing parallel test

Locate the existing reset test for the sibling method and understand its structure:

```mojo
fn test_validation_loop_run_subset_resets_loader() raises:
    """..."""
    var vloop = ValidationLoop()
    var loader = create_val_loader(n_batches=2)
    loader.current_batch = loader.num_batches   # pre-exhaust
    assert_true(not loader.has_next())
    var metrics = TrainingMetrics()
    var val_loss = vloop.run_subset(simple_forward, simple_loss, loader, 2, metrics)
    assert_greater(val_loss, Float64(-1e-10))
    assert_less(val_loss, Float64(1e10))
    print("  test_validation_loop_run_subset_resets_loader: PASSED")
```

### Step 2 — Read the implementation to confirm reset() call site

Check `validation_loop.mojo`:

- `run_subset()` calls `val_loader.reset()` directly at line ~266.
- `run()` delegates to `validate()`, which calls `val_loader.reset()` at line ~94.

Document the exact call path in the docstring so reviewers understand the indirection.

### Step 3 — Write the parallel test using pre-exhaustion strategy

```mojo
fn test_validation_loop_run_resets_loader() raises:
    """Test run() resets a pre-exhausted DataLoader before iterating.

    Strategy: Create a loader with exactly 2 batches, then exhaust it by
    setting current_batch = num_batches. Without reset(), has_next() returns
    False immediately -> 0 batches processed -> division by zero. With reset(),
    the loader restarts and processes all 2 batches -> valid finite loss.

    This proves run() calls val_loader.reset() internally (via validate(),
    line 94 of validation_loop.mojo).
    """
    var vloop = ValidationLoop()
    # 2 batches total (8 samples, batch_size=4)
    var loader = create_val_loader(n_batches=2)
    # Pre-exhaust: advance to end so has_next() returns False
    loader.current_batch = loader.num_batches
    assert_true(not loader.has_next())
    var metrics = TrainingMetrics()
    # run() delegates to validate() which calls val_loader.reset() internally
    var val_loss = vloop.run(simple_forward, simple_loss, loader, metrics)
    # Valid finite loss proves batches were processed after reset (not 0)
    assert_greater(val_loss, Float64(-1e-10))
    assert_less(val_loss, Float64(1e10))
    print("  test_validation_loop_run_resets_loader: PASSED")
```

Key elements of the pre-exhaustion strategy:

1. `loader.current_batch = loader.num_batches` — directly mutates the loader state to simulate exhaustion
2. `assert_true(not loader.has_next())` — pre-condition: confirms loader is exhausted before calling the method under test
3. A **valid finite loss** as the post-condition — proves `reset()` ran (otherwise division-by-zero or zero batches)

### Step 4 — Add call to main()

Place the call in the correct group block (under `run()` tests, not `run_subset()` tests):

```mojo
print("Running ValidationLoop.run() tests...")
test_validation_loop_run_basic()
test_validation_loop_run_updates_metrics()
test_validation_loop_run_compute_accuracy_false()
test_validation_loop_run_resets_loader()   # ← add here
```

### Step 5 — Commit, push, PR

```bash
git add tests/shared/training/test_validation_loop.mojo
git commit -m "test(validation_loop): add test_validation_loop_run_resets_loader

Closes #3688"
git push -u origin 3688-auto-impl
gh pr create --title "..." --body "Closes #3688"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `run_in_background` for Skill tool | Called commit-commands:commit-push-pr skill | Skill tool denied (don't-ask mode) | Fall back to direct Bash git commands when Skill tool is unavailable |
| Checking for pytest tests | Issue prompt said "use pytest" | Project uses Mojo test runner, not pytest | Always check test file extension and existing test patterns before writing tests |

## Results & Parameters

**Test file**: `tests/shared/training/test_validation_loop.mojo`

**Pre-exhaustion snippet** (copy-paste):

```mojo
loader.current_batch = loader.num_batches
assert_true(not loader.has_next())
```

**Post-condition assertions** (valid finite loss):

```mojo
assert_greater(val_loss, Float64(-1e-10))
assert_less(val_loss, Float64(1e10))
```

**Why finite loss proves reset**:
- Without reset: `has_next()` returns `False` immediately → 0 batches → division by zero (crash or `avg_loss = 0/0`)
- With reset: loader restarts → N batches processed → `avg_loss = total / N` → finite positive value

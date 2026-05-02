---
name: mojo-run-epoch-with-batches
description: 'Test run_epoch_with_batches() in Mojo training scripts using a real
  DataLoader and a named step_fn. Use when: a training utility that accepts a DataLoader
  and step_fn has no tests, need to verify avg_loss > 0 and loader.reset() semantics,
  or step_fn must match the fn pointer signature fn(ExTensor, ExTensor) raises ->
  ExTensor.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# mojo-run-epoch-with-batches

## Overview

| Item | Details |
| ------ | --------- |
| Name | mojo-run-epoch-with-batches |
| Category | testing |
| Description | Pattern for testing Mojo epoch-runner functions that accept DataLoader + step_fn |
| Language | Mojo v0.26.1 |
| Pattern | Named top-level fn as step_fn, constant-returning helper, assert avg_loss > 0 |

## When to Use

- A Mojo training utility (`run_epoch_with_batches` or similar) accepts a `DataLoader` and
  a `step_fn: fn(ExTensor, ExTensor) raises -> ExTensor` but has no tests
- You need to verify that `loader.reset()` is called internally (reset-semantics test)
- You need to assert `avg_loss > 0` after one full epoch
- The function is in `shared/training/script_runner.mojo` or a similar module that exports
  epoch-level training helpers

## Verified Workflow

### Quick Reference

```mojo
# 1. Import at top of test file
from shared.training import TrainingCallbacks, run_epoch_with_batches
from shared.training.trainer_interface import DataLoader

# 2. Define a named top-level fn (NOT a closure)
fn _constant_step_fn(data: ExTensor, labels: ExTensor) raises -> ExTensor:
    return ExTensor(Float64(0.5))

# 3. Basic test: assert avg_loss > 0
fn test_run_epoch_with_batches_basic() raises:
    var data = ones([4, 10], DType.float32)
    var labels = zeros([4, 1], DType.float32)
    var loader = DataLoader(data^, labels^, 2)
    var callbacks = TrainingCallbacks(verbose=False, print_frequency=1)
    var avg_loss = run_epoch_with_batches(loader, callbacks, _constant_step_fn)
    assert_greater(Float64(avg_loss), Float64(0.0))
    assert_almost_equal(Float64(avg_loss), Float64(0.5), Float64(1e-5))

# 4. Reset-semantics test: partially consume loader first
fn test_run_epoch_with_batches_reset_semantics() raises:
    var data = ones([4, 10], DType.float32)
    var labels = zeros([4, 1], DType.float32)
    var loader = DataLoader(data^, labels^, 2)
    _ = loader.next()  # Partially consume
    var callbacks = TrainingCallbacks(verbose=False, print_frequency=1)
    var avg_loss = run_epoch_with_batches(loader, callbacks, _constant_step_fn)
    assert_greater(Float64(avg_loss), Float64(0.0))
    assert_equal(loader.num_batches, 2)  # All batches processed
```

1. **Read the function signature** of `run_epoch_with_batches` in `script_runner.mojo` to
   confirm the exact `step_fn` type: `fn (ExTensor, ExTensor) raises -> ExTensor`.

2. **Use a named top-level `fn`** for `step_fn` — Mojo function pointer types do not accept
   closures or lambdas; the function must be a top-level `fn` (not `def`, not a struct method).

3. **Return a scalar ExTensor from `step_fn`** using `ExTensor(Float64(value))` — this uses
   the implicit `Float64` conversion to create a 0D scalar tensor that `_get_float32(0)` can
   read.

4. **DataLoader positional args** — `DataLoader(data^, labels^, batch_size)` uses positional
   args; Mojo does not support keyword arguments for struct constructors.

5. **Basic test**: create a `DataLoader` with known batch count, call `run_epoch_with_batches`,
   assert `avg_loss > 0` and `avg_loss ≈ expected` (e.g., 0.5 when step_fn always returns 0.5).

6. **Reset-semantics test**: partially consume the loader (call `loader.next()` once), then
   call `run_epoch_with_batches`. Assert `avg_loss > 0` AND `loader.num_batches == N` to
   confirm all N batches were processed (proving `loader.reset()` was called internally).

7. **Add both tests to `main()`** with `print("Running run_epoch_with_batches tests...")`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3880, PR #4820 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Lambda / closure as step_fn | Tried `var step_fn = fn(d: ExTensor, l: ExTensor) raises -> ExTensor: return ExTensor(0.5)` | Mojo function pointer type `fn(ExTensor, ExTensor) raises -> ExTensor` does not accept closures | Always use a named top-level `fn`, never a closure or lambda |
| `ExTensor(Float32(0.5))` for scalar | Used Float32 conversion to create scalar loss | `ExTensor` has no implicit `Float32` constructor; only `Float64` and `Int` are implicitly converted | Use `ExTensor(Float64(value))` for scalar loss tensors |
| Keyword args in DataLoader constructor | Used `DataLoader(data^, labels^, batch_size=2)` | Mojo struct constructors don't support keyword arguments | Use positional args: `DataLoader(data^, labels^, 2)` |
| Testing callbacks_fired count | Tried to count callback invocations by subclassing `TrainingCallbacks` | `TrainingCallbacks` is a concrete struct (not a trait), cannot be subclassed | Assert `avg_loss > 0` and use `loader.num_batches` to verify batch count instead |

## Results & Parameters

```mojo
# Confirmed working pattern (ProjectOdyssey, Mojo 0.26.1)

fn _constant_step_fn(data: ExTensor, labels: ExTensor) raises -> ExTensor:
    """Step function returning a constant loss of 0.5 for testing."""
    return ExTensor(Float64(0.5))

fn test_run_epoch_with_batches_basic() raises:
    var data = ones([4, 10], DType.float32)
    var labels = zeros([4, 1], DType.float32)
    var loader = DataLoader(data^, labels^, 2)  # 4 samples / 2 = 2 batches
    var callbacks = TrainingCallbacks(verbose=False, print_frequency=1)
    var avg_loss = run_epoch_with_batches(loader, callbacks, _constant_step_fn)
    assert_greater(Float64(avg_loss), Float64(0.0))
    assert_almost_equal(Float64(avg_loss), Float64(0.5), Float64(1e-5))

fn test_run_epoch_with_batches_reset_semantics() raises:
    var data = ones([4, 10], DType.float32)
    var labels = zeros([4, 1], DType.float32)
    var loader = DataLoader(data^, labels^, 2)
    _ = loader.next()  # Partially consume (1 of 2 batches)
    var callbacks = TrainingCallbacks(verbose=False, print_frequency=1)
    var avg_loss = run_epoch_with_batches(loader, callbacks, _constant_step_fn)
    assert_greater(Float64(avg_loss), Float64(0.0))
    assert_almost_equal(Float64(avg_loss), Float64(0.5), Float64(1e-5))
    assert_equal(loader.num_batches, 2)  # Confirms reset() was called
```

**Import pattern** (both must come from `shared.training`):

```mojo
from shared.training import TrainingCallbacks, run_epoch_with_batches
from shared.training.trainer_interface import DataLoader
```

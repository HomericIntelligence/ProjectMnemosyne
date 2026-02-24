# Fix randn Seed Bug - Session Notes

## Context

Date: 2025-12-30
Project: ProjectOdyssey
Session Goal: Fix CI failures for PR #2980 (Enable Training Loop Tests)

## Problem Discovery

PR #2980 added training loop tests that used `randn(shape, dtype, seed=42)` for reproducible random inputs. Tests failed with assertion errors:

```text
test_training_loop_forward_pass: PASSED
Unhandled exception caught during execution: 0.19019678235054016 !≈ 0.10000000149011612 (diff: 0.09019678086042404)
❌ FAILED: tests/shared/training/test_training_loop.mojo
```

The test `test_training_loop_forward_batches_independently` was comparing two forward passes with supposedly identical inputs (same seed=42), but getting different outputs.

## Root Cause Analysis

1. Test creates two inputs with same seed:
   ```mojo
   var input1 = randn([10], DType.float32, seed=42)
   var input2 = randn([10], DType.float32, seed=42)
   ```

2. Expected: `input1 == input2` (same seed = same values)
   Actual: `input1 != input2` (different random values each call)

3. Traced to `shared/core/extensor.mojo` line 3259:
   ```mojo
   fn randn(shape: List[Int], dtype: DType, seed: Int = 0) raises -> ExTensor:
       # ... seed parameter DECLARED but NEVER USED
       var u1 = random_float64()  # Uses global unseeded PRNG
       var u2 = random_float64()
   ```

4. The `seed` parameter was in the function signature and docstring, but no code ever called `random_seed(seed)` to actually seed the PRNG.

## Initial Misdiagnosis

First assumption was that the model's `forward()` method was mutating state, causing different outputs. Investigation showed:
- SimpleMLP uses constant initialization (`init_value=0.1`)
- forward() doesn't mutate any internal state
- The model WAS deterministic - the inputs were not

The value `0.10000000149011612` (≈0.1) matched the model's init_value, suggesting one of the outputs was nearly zero input producing bias-dominated output.

## Solution Applied

### shared/core/extensor.mojo

**Line 38 (import):**
```mojo
# Before
from random import random_float64

# After
from random import random_float64, seed as random_seed
```

**Lines 3298-3300 (seed usage):**
```mojo
# Before (after dtype check, before tensor creation)
var tensor = ExTensor(shape, dtype)

# After
# Set random seed if provided (0 uses system randomness)
if seed > 0:
    random_seed(seed)

var tensor = ExTensor(shape, dtype)
```

## Additional Fixes in Same PR

1. **Pre-commit formatting**: `test_training_loop.mojo` had a long print line that `mojo format` reformatted:
   ```mojo
   # Before (line too long)
   print("  test_training_loop_property_loss_decreases_on_simple_problem: PASSED")

   # After (reformatted)
   print(
       "  test_training_loop_property_loss_decreases_on_simple_problem: PASSED"
   )
   ```

## PR Details

- PR #2980: Enable Training Loop Tests
- Branch: 2728-training-tests
- Commits:
  1. `feat(training): enable training loop tests with SimpleMLP and randn`
  2. `fix(tests): format long print line in training loop test`
  3. `fix(core): use seed parameter in randn function`
- Status: CI running with fixes

## Commands Used

```bash
# Check CI status
gh pr checks 2980

# Get failed run logs
gh run view 20560652519 --log-failed 2>&1 | grep -A 50 "error\|FAILED"

# Find seed usage in codebase
grep -n "seed" shared/core/extensor.mojo
grep -rn "random_seed\|seed as" shared/

# Build to verify fix compiles
pixi run mojo build shared/core/__init__.mojo -I .

# Commit and push
git add shared/core/extensor.mojo
git commit -m "fix(core): use seed parameter in randn function"
git push
```

## Lessons Learned

1. **Check function implementations, not just signatures** - The seed parameter existed but was dead code
2. **Trace the actual values** - The error message `0.19... !≈ 0.10...` gave clues about what was happening
3. **Look for patterns in codebase** - `shared/core/initializers.mojo` had the correct seeding pattern to copy
4. **Pre-existing bugs surface when code is tested** - The randn function was broken since it was written, but only exposed when tests actually used the seed parameter

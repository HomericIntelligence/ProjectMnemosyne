---
name: fix-randn-seed-bug
description: Fix unused seed parameter in random number generation functions causing non-reproducible tests
category: debugging
created: 2025-12-30
tags: [random, seed, reproducibility, testing, mojo, prng]
---

# Fix Unused Seed Parameter in randn()

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | | Field | Value | |-------|-------| | Date | 2025-12-30 | | Objective | Fix test failures caused by randn() ignoring its seed parameter | |
| Outcome | Operational |


| Field | Value |
|-------|-------|
| Date | 2025-12-30 |
| Objective | Fix test failures caused by randn() ignoring its seed parameter |
| Outcome | Tests now reproducible - same seed produces identical random tensors |

## When to Use

Use this skill when:

- Tests using `randn(shape, dtype, seed=42)` produce different values each run
- `assert_almost_equal` fails comparing outputs that should be identical
- Error shows two very different values (e.g., `0.19... !≈ 0.10...`)
- Function declares `seed` parameter but calls `random_float64()` without seeding
- Reproducibility tests fail despite using fixed seeds

## Verified Workflow

### 1. Identify the Symptom

Test failure pattern:

```text
Unhandled exception caught during execution: 0.19019678235054016 !≈ 0.10000000149011612 (diff: 0.09019678086042404)
```

This indicates two calls with the same seed produced different values.

### 2. Trace the Root Cause

```bash
# Find where seed parameter is used
grep -n "seed" shared/core/extensor.mojo | head -20
```

Look for pattern where seed is declared but never used:

```mojo
# BUG: seed parameter declared but not used
fn randn(shape: List[Int], dtype: DType, seed: Int = 0) raises -> ExTensor:
    # ...
    var u1 = random_float64()  # NOT seeded!
    var u2 = random_float64()
```

### 3. Check How Other Functions Seed

```bash
# Find seeding patterns in codebase
grep -rn "random_seed\|seed as" shared/
```

Expected pattern from working code:

```mojo
from random import random_float64, seed as random_seed

fn some_function(seed_val: Int = -1):
    if seed_val >= 0:
        random_seed(seed_val)
    var val = random_float64()  # Now seeded
```

### 4. Apply the Fix

Add the import and seeding call:

```mojo
# Before (broken)
from random import random_float64

fn randn(shape: List[Int], dtype: DType, seed: Int = 0) raises -> ExTensor:
    var tensor = ExTensor(shape, dtype)
    # ... uses random_float64() without seeding

# After (fixed)
from random import random_float64, seed as random_seed

fn randn(shape: List[Int], dtype: DType, seed: Int = 0) raises -> ExTensor:
    # Set random seed if provided (0 uses system randomness)
    if seed > 0:
        random_seed(seed)

    var tensor = ExTensor(shape, dtype)
    # ... now random_float64() is seeded
```

### 5. Verify the Fix

```bash
# Build to check for compile errors
pixi run mojo build shared/core/__init__.mojo -I .

# Run the failing test
pixi run mojo test tests/shared/training/test_training_loop.mojo -I .
```

## Failed Attempts

| Attempt | What Happened | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| Assumed model was non-deterministic | Thought SimpleMLP weights were random | Model actually uses constant init (`init_value=0.1`) | Check model initialization before blaming the model |
| Thought test logic was wrong | Assumed comparing wrong values | Test was correct - same input should give same output | Trust the test assertions, trace the actual values |
| Looked at model forward pass | Checked for state mutation in forward() | forward() doesn't mutate state, just creates output | The inputs themselves were different, not the model |

## Results & Parameters

### Files Modified

| File | Line | Change |
|------|------|--------|
| `shared/core/extensor.mojo` | 38 | Added `seed as random_seed` to import |
| `shared/core/extensor.mojo` | 3298-3300 | Added seed call before tensor creation |

### The Fix (Copy-Paste Ready)

```mojo
# Add to imports
from random import random_float64, seed as random_seed

# Add before using random_float64()
# Set random seed if provided (0 uses system randomness)
if seed > 0:
    random_seed(seed)
```

### Seed Convention

| Seed Value | Behavior |
|------------|----------|
| `seed = 0` | Use system randomness (non-reproducible) |
| `seed > 0` | Set PRNG seed for reproducibility |
| `seed = -1` | Alternative convention: random (used elsewhere) |

### Commands Reference

```bash
# Find seed parameter declarations
grep -rn "seed: Int" shared/

# Find actual seeding calls
grep -rn "random_seed(" shared/

# Find random_float64 usage without seeding
grep -B5 "random_float64()" shared/ | grep -v "random_seed"
```

## Related

- PR #2980 in ProjectOdyssey - Training loop tests that exposed this bug
- Issue #2728 - Enable Training Loop Tests (original feature work)
- `shared/core/initializers.mojo` - Example of correct seeding pattern

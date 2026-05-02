---
name: mojo-init-export-uncomment
description: 'Activate commented-out exports in Mojo __init__.mojo by verifying leaf-module
  implementations and using absolute import paths + comptime aliases to work around
  the v0.26.1 re-export chain limitation. Use when: (1) __init__.mojo has pending
  commented-out imports, (2) layer structs are confirmed implemented, (3) API name
  mismatches need bridging.'
category: tooling
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-init-export-uncomment |
| **Category** | tooling |
| **Context** | Mojo v0.26.1 packages, `__init__.mojo` export management |
| **Trigger** | Issue requesting activation of commented-out `__init__.mojo` imports after underlying modules are ready |
| **Output** | Updated `__init__.mojo` with active imports, `comptime` aliases, updated API table, and new packaging test |

## When to Use

Use this skill when:

1. A Mojo package `__init__.mojo` has blocks of commented-out imports with notes like "pending full implementation"
2. Some or all of the underlying modules have since been implemented
3. You need to expose symbols at the package top-level (e.g. `from shared import Linear`)
4. There are API name mismatches between documented names and actual struct names (e.g. `Conv2D` vs `Conv2dLayer`)

## Verified Workflow

### Quick Reference

```bash
# 1. Verify which struct/fn names actually exist
grep -rn "^struct\|^fn\|^trait" shared/core/layers/ | grep -v "__"

# 2. Check if re-export chains would work (they don't in v0.26.1)
# Use absolute leaf-module paths instead of re-exported names

# 3. Import directly from leaf modules
from shared.core.layers.linear import Linear

# 4. Add comptime aliases for API name mismatches
comptime Conv2D = Conv2dLayer
```

### Step 1 — Inventory the commented-out imports

Read the `__init__.mojo` file and list every commented-out import. For each one, note:

- The documented symbol name (e.g. `Conv2D`, `SGD`, `train_epoch`)
- The claimed source module (e.g. `.core.layers`, `.training.optimizers`)

### Step 2 — Verify leaf-module implementations

For each symbol, check if the actual struct/fn/trait exists:

```bash
# Check layers
grep -rn "^struct\|^fn\|^trait" shared/core/layers/ | grep -v "__"

# Check specific module
grep -rn "^struct SGD\|^struct Adam" shared/training/optimizers/
```

Categorize each import as:
- **Ready**: Implementation exists, can activate
- **Name mismatch**: Exists under a different name — use `comptime` alias
- **Not yet implemented**: Struct doesn't exist — leave commented out with note

### Step 3 — Determine if re-export chains work

In Mojo v0.26.1, re-export chains **do not work**. If `shared/core/__init__.mojo`
re-exports `Linear` from `shared/core/layers/linear.mojo`, you **cannot** then do:

```mojo
# shared/__init__.mojo — THIS FAILS in v0.26.1
from shared.core import Linear  # chain re-export — broken
```

You MUST use the absolute leaf-module path:

```mojo
# shared/__init__.mojo — THIS WORKS
from shared.core.layers.linear import Linear  # absolute path — works
```

### Step 4 — Write the activated imports

Replace the commented block with activated imports using absolute leaf-module paths:

```mojo
# Core layers — activated; absolute paths required due to #3754 re-export limitation
from shared.core.layers.linear import Linear
from shared.core.layers.conv2d import Conv2dLayer
from shared.core.layers.relu import ReLULayer

# comptime aliases bridge documented API names to actual struct names
comptime Conv2D = Conv2dLayer
comptime ReLU = ReLULayer

# MaxPool2D, Flatten — NOT YET IMPLEMENTED in shared/core/layers/
```

Keep comments for items that are NOT yet implemented so future contributors know
they're still pending.

### Step 5 — Update the Public API Table in the docstring

Update the ASCII table in the module docstring to reflect active vs pending exports:

```text
# ┌──────────────────────┬────────────────────────────────┐
# │ Symbol               │ Source                         │
# ├──────────────────────┼────────────────────────────────┤
# │ Linear               │ shared.core.layers.linear      │
# │ Conv2dLayer, Conv2D  │ shared.core.layers.conv2d      │
# └──────────────────────┴────────────────────────────────┘
# Not yet activated: Sequential, SGD/Adam/AdamW, TensorDataset
```

### Step 6 — Add a packaging test

Add a test function that smoke-tests all newly activated symbols:

```mojo
fn test_layer_root_level_imports() raises:
    """Test newly activated symbols are importable from shared."""
    from shared import Linear, Conv2dLayer, Conv2D, ReLU

    # Smoke-test: instantiate and use a layer
    var layer = Linear(4, 2)
    var x = zeros([1, 4], DType.float32)
    var out = layer.forward(x)
    assert_true(out.shape()[1] == 2, "Linear output features should be 2")

    # Alias resolves to the same type
    var conv = Conv2D(1, 4, 3)
    assert_true(True, "Conv2D alias should resolve to Conv2dLayer")

    print("✓ Layer root-level imports test passed")
```

Register it in `main()`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Import via intermediate `__init__.mojo` | `from shared.core import Linear` in `shared/__init__.mojo` | Mojo v0.26.1 re-export chain limitation: chained re-exports do not propagate | Always use absolute leaf-module paths in top-level `__init__.mojo` |
| Activating `SGD`/`Adam` | Searched for `struct SGD` in `shared/training/optimizers/` | Only functional step-functions exist (`sgd_step`, `adam_step`), no struct classes | Verify struct names precisely — functions and structs have different activation requirements |
| Activating `Sequential` | Expected single `Sequential` struct | Only parametric variants exist: `Sequential2`, `Sequential3`, `Sequential4`, `Sequential5` | Check for exact struct name match, not just module presence |
| Activating `TensorDataset` | Searched `shared/data/` for `TensorDataset` | Only `ExTensorDataset` exists | Documented API names may not match implemented struct names — always grep |
| Activating `train_epoch`/`validate_epoch` | Searched `shared/training/loops/` | Functions are named `train_one_epoch` and `validate`, not the documented names | API names documented in `__init__.mojo` may be aspirational, not actual |

## Results & Parameters

### What was activated (session result)

```mojo
# Core layers
from shared.core.layers.linear import Linear
from shared.core.layers.conv2d import Conv2dLayer
from shared.core.layers.relu import ReLULayer
from shared.core.layers.dropout import DropoutLayer
from shared.core.layers.batchnorm import BatchNorm2dLayer
comptime Conv2D = Conv2dLayer
comptime ReLU = ReLULayer
comptime Dropout = DropoutLayer
comptime BatchNorm2d = BatchNorm2dLayer

# Core activations
from shared.core.activation import relu, sigmoid, tanh, softmax

# Core module trait
from shared.core.module import Module

# Core tensors
from shared.core.extensor import ExTensor, zeros, ones, randn
comptime Tensor = ExTensor

# Training schedulers
from shared.training.schedulers.lr_schedulers import StepLR, CosineAnnealingLR

# Training callbacks
from shared.training.callbacks import EarlyStopping, ModelCheckpoint

# Utils
from shared.utils.logging import Logger
from shared.utils.visualization import plot_training_curves
```

### grep patterns for verification

```bash
# Find all structs/traits in a directory
grep -rn "^struct\|^fn\|^trait" <dir>/ | grep -v "__" | head -30

# Check if a specific struct exists
grep -rn "^struct Conv2D\b" shared/

# Check what functions a module exports
grep -rn "^fn " shared/training/loops/ | head -20
```

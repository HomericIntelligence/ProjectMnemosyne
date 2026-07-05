---
name: epoch-metrics-mutable-output-parameters
description: Record epoch-level metrics by adding mutable output parameters to training functions without refactoring the entire function signature
category: training
date: 2026-07-04
version: 1.0.0
user-invocable: false
verification: verified-local
tags:
  - mojo
  - mutable-parameters
  - training-functions
  - refactoring
  - metrics
  - minimal-change
---

# Skill: Epoch Metrics with Mutable Output Parameters

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Add epoch-level metric capture (loss history, gradient norms, etc.) to training functions without refactoring callers |
| **Outcome** | ✅ Added `mut loss_history: List[Float32]` parameter to train_epoch; existing smoke-test callers unaffected; metrics captured for convergence assertions |
| **Verification** | **verified-local** — training example smoke run passes; no breaking changes to train_epoch callers; metrics capture verified in test_backward.mojo |
| **Context** | Issue #5516: Needed to capture per-batch loss for convergence validation without changing train_epoch's core logic |

## Overview

This skill documents the pattern for adding **mutable output parameters** to existing training functions to capture metrics (loss history, gradient statistics, checkpoint info) without requiring:

- Major refactoring of function signatures
- Changes to existing callers
- Creating new wrapper functions
- Creating separate logging infrastructure

The approach is minimal, backward-compatible, and follows Mojo v1.0 conventions.

## When to Use

Use this skill when:

- Adding metric capture to existing training functions
- Need per-batch loss, gradient norms, or validation metrics without modifying core training logic
- Want to avoid creating wrapper functions or separate monitoring infrastructure
- Caller already owns the container they want to fill (e.g., `List[Float32]` created by caller)
- Need backward compatibility (existing callers should not be affected)

## Verified Workflow

### 1. Identify the Output Parameter Type

**Problem**: Need to capture metrics but don't want to change train_epoch's return type or add wrapper functions.

**Solution**: Add a mutable output parameter matching a type the caller already controls.

```mojo
# Option A: List for sequential metrics (loss per batch, norm per layer)
mut loss_history: List[Float32]

# Option B: Dict for named metrics (works for Float32-valued metrics)
mut metrics: Dict[String, List[Float32]]

# Option C: Custom struct for complex metrics
struct EpochMetrics:
    loss_history: List[Float32]
    gradient_norms: List[Float32]
    learning_rates: List[Float32]
```

**Key Details:**

- Caller creates the container and passes it mutably
- Function appends/modifies the container
- Function does not own or create the container
- No memory leaks or ownership transfer issues

### 2. Update Function Signature (Minimal Change)

**Problem**: How to add a mutable parameter without breaking existing callers?

**Solution**: Add the parameter at the end of the signature; use default-like behavior (empty list is safe).

```mojo
# BEFORE (original signature)
def train_epoch(
    model: ResNet18,
    images: AnyTensor,
    labels: AnyTensor,
    batch_size: Int,
    learning_rate: Float32,
    momentum: Float32,
    mut velocities: ResNet18Velocities,
    epoch: Int,
    total_epochs: Int,
) -> ResNet18:

# AFTER (added loss_history parameter)
def train_epoch(
    model: ResNet18,
    images: AnyTensor,
    labels: AnyTensor,
    batch_size: Int,
    learning_rate: Float32,
    momentum: Float32,
    mut velocities: ResNet18Velocities,
    mut loss_history: List[Float32],  # <- NEW: mutable output param
    epoch: Int,
    total_epochs: Int,
) -> ResNet18:
```

**Key Details:**

- Add `mut loss_history` parameter after `velocities` (preserve parameter order)
- No return type change (still returns ResNet18)
- Signature is now stricter (callers must pass the parameter explicitly)
- Check existing callers to see if they need updates

### 3. Append Metrics Inside the Training Loop

**Problem**: Need to record per-batch metrics without creating new data structures or introducing side effects.

**Solution**: Append to the mutable parameter inside the batch loop.

```mojo
def train_epoch(
    model: ResNet18,
    images: AnyTensor,
    labels: AnyTensor,
    batch_size: Int,
    learning_rate: Float32,
    momentum: Float32,
    mut velocities: ResNet18Velocities,
    mut loss_history: List[Float32],
    epoch: Int,
    total_epochs: Int,
) -> ResNet18:
    var model = model
    var total_loss = Float32(0.0)

    var num_batches = (images.shape()[0] + batch_size - 1) // batch_size
    for batch_idx in range(num_batches):
        # ... compute batch_loss ...

        # CAPTURE: Append batch loss to history
        loss_history.append(batch_loss)

        total_loss = total_loss + batch_loss

        # Log progress every 100 batches
        if (batch_idx + 1) % 100 == 0:
            var avg_loss = total_loss / Float32(batch_idx + 1)
            print("  Batch ", batch_idx + 1, ": Average Loss: ", avg_loss)

    return model
```

**Key Details:**

- Append after each batch: `loss_history.append(batch_loss)`
- No guard conditions needed (append is safe on empty list)
- Can be called multiple times (e.g., multiple epochs) without issue
- List grows as expected (10 batches → 10 entries)

### 4. Verify No Cross-File Callers Exist

**Problem**: Changing function signature could break callers in other files.

**Solution**: Grep for all callers and verify they can accommodate the new parameter.

```bash
# Search for all calls to train_epoch
grep -r "train_epoch" examples/ src/ tests/ --include="*.mojo"

# Expected output: only calls in files you control
# If external callers exist, they must be updated
```

**Verification Steps:**

1. Search for `train_epoch` calls
2. Check each call location:
   - Test files: Create empty `List[Float32]()` and pass it
   - Training scripts: Create list, pass it, inspect after call
   - Other modules: Update if applicable
3. Confirm no production code depends on old signature

**Real-world example from issue #5516:**

```bash
$ grep -r "train_epoch" . --include="*.mojo"

examples/resnet18_cifar10/test_backward.mojo:    _ = train_epoch(
examples/resnet18_cifar10/train.mojo:def train_epoch(
```

**Only two occurrences**: function definition + one test call. Update the test call:

```mojo
# OLD: 7 arguments
_ = train_epoch(model, images, labels, batch_size, lr, momentum, velocities, epoch, total_epochs)

# NEW: 8 arguments (added loss_history)
var loss_history: List[Float32] = []
_ = train_epoch(
    model, images, labels, batch_size,
    Float32(0.01), Float32(0.9),
    velocities, loss_history,
    1, 1
)
```

### 5. Test the Change with Smoke Run

**Problem**: Need to verify the change doesn't break existing callers or introduce new bugs.

**Solution**: Run the training example (smoke test) without the new feature to verify backward compatibility.

```bash
# Compile the training example (tests function signature is still valid)
mojo build examples/resnet18_cifar10/train.mojo

# Run the test file (verifies both old behavior and new metric capture)
mojo test examples/resnet18_cifar10/test_backward.mojo
```

**Expected Results:**

- Compilation succeeds (no signature errors)
- All existing tests pass (backward compatibility maintained)
- New metric-capture tests pass (new feature works)

## Mojo v1.0 Conventions

### `mut` Parameter Semantics

In Mojo v1.0, `mut param: Type` means:

- Caller passes a mutable reference to an object they own
- Function can read and modify the object
- Object lifetime is controlled by the caller
- Function cannot transfer ownership (no `^` operator needed)

```mojo
# Pattern 1: Append to caller-owned list
def process_items(mut items: List[Int]) raises:
    items.append(42)  # Modifies caller's list

# Pattern 2: Modify caller-owned struct
def update_state(mut state: MyState) raises:
    state.counter = state.counter + 1

# Pattern 3: Multiple mutable parameters
def train_step(
    mut model: ResNet18,
    mut velocities: ResNet18Velocities,
    mut loss_history: List[Float32],
) raises:
    # Modify all three
```

### Avoid Common Mistakes

```mojo
# ❌ WRONG: Using ^param transfers ownership; caller loses access
def bad_example(^items: List[Int]) raises:
    # items is now owned by this function; caller cannot use it afterward

# ✅ CORRECT: Using mut param allows caller to use after call
def good_example(mut items: List[Int]) raises:
    items.append(42)
    # Caller still owns items; can inspect after call returns
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Return List from train_epoch | `(model, loss_history) = train_epoch(...)` | Mojo 1.0 doesn't support Python-style tuple unpacking; awkward return types | Use mutable parameters for output |
| Create EpochMetrics struct | Add as new parameter with all metric types | Too much scope creep; complicates function signature | Start with single metric (loss), add more later via YAGNI |
| Log to file inside train_epoch | Print to stderr with batch loss | Mixing training logic with I/O; hard to test; log pollution | Capture metrics, let caller decide what to do (print, save, assert, etc.) |
| Make loss_history optional (default []) | `mut loss_history: List[Float32] = []` | Mojo doesn't support default mutable parameters | Require explicit parameter; caller always passes a list |

## Results & Parameters

### Parameter Addition Checklist

When adding a mutable output parameter:

- [ ] Identify metric type (List[Float32], List[Int], custom struct, etc.)
- [ ] Add parameter to function signature (end of parameter list, after other mut params)
- [ ] Use `mut metric_name: Type` syntax
- [ ] Append/modify inside the loop: `metric_name.append(value)`
- [ ] Grep for all callers and update them
- [ ] Create empty container in caller: `var loss_history: List[Float32] = []`
- [ ] Pass mutably: `train_epoch(..., loss_history, ...)`
- [ ] Verify signature with compilation: `mojo build file.mojo`
- [ ] Run smoke test: `mojo run test_file.mojo`

### Caller-Side Usage Pattern

```mojo
# 1. Create container
var loss_history: List[Float32] = []

# 2. Pass to function (function will append to it)
var model = train_epoch(
    model,
    images,
    labels,
    batch_size,
    learning_rate,
    momentum,
    velocities,
    loss_history,  # <- Pass mutable reference
    epoch,
    total_epochs,
)

# 3. Inspect metrics after call
print("Captured ", len(loss_history), " batch losses")
for i in range(len(loss_history)):
    print("Batch ", i, ": ", loss_history[i])
```

### Backward Compatibility Note

**Breaking change**: Callers must now pass the loss_history parameter explicitly. This is a signature change but:

- No logic change to existing training
- No change to return type
- Easy to update existing callers (add one parameter)
- Enables new convergence validation tests

To minimize impact, consider:

- Adding the parameter at the **end** of the signature
- Documenting the change in release notes
- Providing examples for common use cases

## Related Patterns

- **Mutable output parameters**: Use `mut` for metrics capture
- **Caller-owned containers**: Let caller create the List, function appends to it
- **Minimal function changes**: Add new parameters without refactoring core logic
- **DRY metric collection**: Avoid duplicating metric-capture code across train_epoch variants
- **Testability**: Metrics capture enables new assertion patterns (e.g., loss convergence checks)

## Implementation Checklist

- [ ] Identify which metrics to capture (start with loss)
- [ ] Choose container type (List[Float32] for scalars)
- [ ] Add mutable parameter to function signature
- [ ] Append to parameter inside training loop
- [ ] Update all callers (use grep to find them)
- [ ] Create empty list in each caller
- [ ] Pass list mutably to function
- [ ] Run compilation check: `mojo build`
- [ ] Run smoke tests: `mojo run` or `mojo test`
- [ ] Verify metrics contain expected values

## Tags

`mojo-v1.0` `mutable-parameters` `training-functions` `metrics-capture` `refactoring` `backward-compatibility` `minimal-change` `loss-tracking`

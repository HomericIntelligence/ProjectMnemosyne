---
name: mojo-trait-conformance-for-sequential-integration
description: "Add Module trait conformance to Mojo layers for Sequential container use, and fix missing trait declarations causing compile-time 'does not conform to trait' errors. Use when: (1) existing layers lack train()/inference() methods, (2) forward() uses self instead of mut self, (3) layers need to be composed inside Sequential2/Sequential3, (4) a struct implements trait methods (e.g. __hash__) but is missing the trait in its declaration list."
category: testing
date: 2026-03-15
version: 1.1.0
user-invocable: false
absorbed:
  - mojo-trait-conformance-fix
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-trait-conformance-for-sequential-integration |
| **Category** | testing |
| **Issue** | #3742 — Integrate Sequential into SimpleMLP in shared/testing |
| **Result** | SimpleMLP2 using Sequential3[Linear, ReLULayer, Linear] as integration test fixture |

## When to Use

Use this skill when:

1. You need to use existing Mojo layer structs inside `Sequential2`/`Sequential3` containers
2. A layer struct is declared `(Copyable, Movable)` but not `Module` — causing type mismatch
3. `forward()` has signature `fn forward(self, ...)` but `Module` requires `fn forward(mut self, ...)`
4. You want to add a test fixture that demonstrates real Sequential container usage
5. Adding a `SimpleMLP2` (or similar) variant that uses Sequential internally

## Verified Workflow

### Quick Reference

```bash
# 1. Check Module trait requirements
grep -n "trait Module" shared/core/module.mojo

# 2. Add Module conformance to layer
# In linear.mojo / relu.mojo:
#   - Add "Module" to struct declaration
#   - Change forward(self) to forward(mut self)
#   - Add train(mut self) and inference(mut self) no-ops

# 3. Add SimpleMLP2 to shared/testing/models.mojo
# 4. Export from shared/testing/__init__.mojo
# 5. Write tests in tests/shared/testing/
just test-group "tests/shared/testing" "test_test_models_simple_mlp2.mojo"
```

### Step 1: Discover Module trait requirements

Read `shared/core/module.mojo` to find the exact method signatures required by `Module`:

```bash
cat shared/core/module.mojo
```

Key requirements typically include:

- `fn forward(mut self, input: ExTensor) raises -> ExTensor`
- `fn parameters(self) raises -> List[ExTensor]`
- `fn train(mut self)`
- `fn inference(mut self)` (or the mode-switching equivalent)

### Step 2: Check existing layer conformance

```bash
grep -n "fn forward\|fn train\|fn inference\|fn parameters" shared/core/layers/linear.mojo
grep -n "struct Linear" shared/core/layers/linear.mojo
```

Look for gaps:

- Is `Module` in the struct trait list?
- Does `forward()` use `self` (immutable) vs `mut self` (mutable)?
- Are `train()` and `inference()` present?

### Step 3: Add Module conformance to layers

For each layer (`linear.mojo`, `relu.mojo`, etc.):

1. Add import: `from shared.core.module import Module`
2. Add `Module` to struct declaration traits
3. Change `fn forward(self, ...)` to `fn forward(mut self, ...)`
4. Add no-op methods:

```mojo
fn train(mut self):
    pass

fn inference(mut self):
    pass
```

**Key insight:** Even if `forward()` doesn't logically need mutation, `Module` requires `mut self`
to allow stateful layers (e.g., BatchNorm) to switch between train/inference modes.

### Step 4: Implement the fixture struct

```mojo
struct SimpleMLP2(Model, Movable):
    var input_dim: Int
    var hidden_dim: Int
    var output_dim: Int
    var net: Sequential3[Linear, ReLULayer, Linear]

    fn __init__(out self, input_dim: Int, hidden_dim: Int, output_dim: Int) raises:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.net = Sequential3[Linear, ReLULayer, Linear](
            Linear(input_dim, hidden_dim),
            ReLULayer(),
            Linear(hidden_dim, output_dim),
        )

    fn forward(mut self, input: ExTensor) raises -> ExTensor:
        return self.net.forward(input)

    fn parameters(self) raises -> List[ExTensor]:
        return self.net.parameters()

    fn train(mut self):
        self.net.train()

    fn inference(mut self):
        self.net.inference()
```

**Why `Sequential3` for 1-hidden-layer?** Layer count: `Linear(input->hidden)` + `ReLU` +
`Linear(hidden->output)` = 3 layers -> `Sequential3`.

**Why `Movable` only, not `Copyable`?** `Sequential3` is `Movable` only (contains
non-copyable layers with heap-allocated weights).

### Step 5: Export from `__init__.mojo`

```mojo
# In shared/testing/__init__.mojo
from shared.testing.models import SimpleMLP2
```

### Step 6: Write tests

Test file `tests/shared/testing/test_test_models_simple_mlp2.mojo`:

```mojo
fn test_simple_mlp2_initialization() raises:
    var model = SimpleMLP2(10, 20, 5)
    assert_equal(model.input_dim, 10)
    assert_equal(model.hidden_dim, 20)
    assert_equal(model.output_dim, 5)

fn test_simple_mlp2_forward_shape() raises:
    var model = SimpleMLP2(10, 20, 5)
    var input = zeros([10])
    var output = model.forward(input)
    assert_equal(output.shape()[0], 5)

fn test_simple_mlp2_parameters_count() raises:
    var model = SimpleMLP2(10, 20, 5)
    var params = model.parameters()
    # W1: 10*20=200, b1: 20, W2: 20*5=100, b2: 5 -> 4 tensors, 325 elements
    assert_equal(len(params), 4)
```

**Use FP-representable values** per project testing strategy: `0.0`, `0.5`, `1.0`, `1.5`, `-1.0`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Use Sequential3 without Module conformance | Passed `Linear`/`ReLULayer` directly into `Sequential3[Linear, ReLULayer, Linear]` | Compile error: `Linear` not in scope of `Module` trait; `T: Module & Movable` constraint unsatisfied | Must add `Module` to all layer structs before they can be used in Sequential containers |
| Keep `forward(self, ...)` immutable | Left `forward()` as `fn forward(self, input: ExTensor)` | Mojo compiler error: signature mismatch with `Module` trait's `fn forward(mut self, ...)` | The `Module` trait requires `mut self` on `forward()` to allow stateful layers; all conforming layers must use `mut self` |
| Add `Copyable` to `SimpleMLP2` | Tried `struct SimpleMLP2(Copyable, Model, Movable)` | `Sequential3` is `Movable` only; compiler rejects copying a type containing a non-Copyable field | Don't declare `Copyable` on model fixtures wrapping Sequential containers |
| Path B (wrapper structs) | Create `LinearModule`/`ReLUModule` wrappers in `shared/testing/` | Works but adds unnecessary indirection and diverges from production code | Path A (add `Module` to production layers) is simpler and correct; layers that have `forward()`/`parameters()` should conform to `Module` |

## Results & Parameters

### Verified configuration

```toml
# Mojo version: 0.26.1 (pinned in pixi.toml)
# Test runtime: just test-group "tests/shared/testing" "test_test_models_simple_mlp2.mojo"
```

### Parameter count formula

For `SimpleMLP2(input_dim=I, hidden_dim=H, output_dim=O)`:

- Tensors: 4 (`W1`, `b1`, `W2`, `b2`)
- Total elements: `I*H + H + H*O + O`
- Example `(10, 20, 5)`: `200 + 20 + 100 + 5 = 325`

### Module trait conformance checklist

```text
[ ] Module import added to layer file
[ ] "Module" added to struct trait list
[ ] forward(self) changed to forward(mut self)
[ ] train(mut self) method added (no-op for stateless layers)
[ ] inference(mut self) method added (no-op for stateless layers)
[ ] Struct compiles with: pixi run mojo build <layer-file>
[ ] Existing layer tests still pass
```

### Pre-existing test failures to ignore

The following test files fail on this branch due to unrelated missing symbols:

- `tests/shared/test_imports.mojo` — `SGD` missing from `shared.training.optimizers`
- `tests/shared/test_imports_part2.mojo` — same root cause
- `tests/shared/test_imports_part3.mojo` — `TrainingState` missing from `shared.training.loops`

These failures exist on `main` and are NOT introduced by this work.

## Quick Fix Reference

### Missing Trait Declaration (1-line fix)

When a struct implements trait methods but is missing the trait in its declaration, CI will report:

```text
error: argument type 'X' does not conform to trait 'Y'
error: no matching function in call to 'hash'
```

**Root cause**: Implementing `__hash__` alone is not sufficient — `Hashable` must be declared explicitly in the struct header. Same applies to `Comparable`, `Stringable`, and all other traits.

**Fix**: Add the trait to the parenthesized conformance list (one-line change):

```mojo
# Before
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):

# After
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized, Hashable):
```

### GLIBC Version Mismatch Workaround

If local Mojo cannot run (host GLIBC 2.31, Mojo requires 2.32+), skip only the `mojo-format` pre-commit hook and let CI verify:

```bash
SKIP=mojo-format git commit -m "fix: add Hashable trait declaration to ExTensor"
```

CI runs in a Docker environment with the correct GLIBC version and will enforce formatting and run tests.

### Trait Conformance Debugging Checklist

```text
[ ] Read the CI error message: "argument type 'X' does not conform to trait 'Y'"
[ ] Find the struct declaration in the .mojo file (first line, parenthesized list)
[ ] Add the missing trait name to the parenthesized list
[ ] If mojo-format hook fails locally due to GLIBC: use SKIP=mojo-format
[ ] Push and verify CI passes (Docker CI has correct GLIBC)
```

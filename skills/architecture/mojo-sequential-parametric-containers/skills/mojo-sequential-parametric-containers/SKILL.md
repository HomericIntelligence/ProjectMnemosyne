---
name: mojo-sequential-parametric-containers
description: "Pattern for implementing Sequential neural network module containers in Mojo using parametric compile-time types. Use when: composing Module-conforming layers into a chain, hitting ImplicitlyCopyable/UnsafePointer errors from List[Trait] usage, or designing reusable containers that propagate train/eval modes."
category: architecture
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 does not support dynamic dispatch via `List[Module]` — trait objects are not heap-dispatchable without unsafe pointer indirection |
| **Solution** | Parametric structs `Sequential2[T0: Module, T1: Module]` resolved at compile time |
| **Benefit** | Type-safe, no `ImplicitlyCopyable` constraint, no `UnsafePointer`, matches Mojo idioms |
| **Cost** | One struct per depth (`Sequential2`, `Sequential3`, ...); verbose but explicit |
| **Language** | Mojo v0.26.1+ |
| **Context** | ML Odyssey project — `shared/core/module.mojo` defines `Module` trait |

## When to Use

1. Composing two or more `Module`-conforming Mojo structs into an ordered forward chain
2. Seeing `ImplicitlyCopyable` errors when trying to put trait objects in a `List`
3. Need `parameters()` aggregated from all sub-layers for an optimizer
4. Need `train()`/`eval()` mode propagated to all sub-layers
5. Replacing a Python-style `nn.Sequential([...])` pattern in Mojo

## Verified Workflow

### 1. Define the Module trait (already exists in project)

```mojo
trait Module:
    fn forward(mut self, input: ExTensor) raises -> ExTensor: ...
    fn parameters(self) raises -> List[ExTensor]: ...
    fn train(mut self): ...
    fn eval(mut self): ...
```

### 2. Implement Sequential2 (two-layer container)

```mojo
struct Sequential2[T0: Module, T1: Module](Movable):
    var layer0: T0
    var layer1: T1

    fn __init__(out self, owned layer0: T0, owned layer1: T1):
        self.layer0 = layer0^
        self.layer1 = layer1^

    fn __moveinit__(out self, owned other: Self):
        self.layer0 = other.layer0^
        self.layer1 = other.layer1^

    fn forward(mut self, input: ExTensor) raises -> ExTensor:
        var out0 = self.layer0.forward(input)
        return self.layer1.forward(out0)

    fn parameters(self) raises -> List[ExTensor]:
        var params: List[ExTensor] = []
        var p0 = self.layer0.parameters()
        var p1 = self.layer1.parameters()
        for i in range(len(p0)):
            params.append(p0[i])
        for i in range(len(p1)):
            params.append(p1[i])
        return params^

    fn train(mut self):
        self.layer0.train()
        self.layer1.train()

    fn eval(mut self):
        self.layer0.eval()
        self.layer1.eval()
```

### 3. Implement Sequential3 (three-layer container) — same pattern extended

```mojo
struct Sequential3[T0: Module, T1: Module, T2: Module](Movable):
    var layer0: T0
    var layer1: T1
    var layer2: T2
    # ... same pattern with three layers
```

### 4. Usage

```mojo
from shared.core.sequential import Sequential2, Sequential3
from shared.core.layers import Linear, ReLULayer

var model = Sequential2[Linear, ReLULayer](
    Linear(10, 5),
    ReLULayer(),
)
var input = zeros([4, 10], DType.float32)
var output = model.forward(input)  # Shape: [4, 5]
```

### 5. Testing with local dummy modules

To isolate Sequential logic from layer-specific behavior, define minimal dummy structs:

```mojo
struct ScaleModule:
    var scale: Float32
    var is_training: Bool

    fn __init__(out self, scale: Float32):
        self.scale = scale
        self.is_training = True

    fn forward(mut self, input: ExTensor) raises -> ExTensor:
        var result = zeros(input.shape(), DType.float32)
        for i in range(input.numel()):
            result._data.bitcast[Float32]()[i] = input._data.bitcast[Float32]()[i] * self.scale
        return result

    fn parameters(self) raises -> List[ExTensor]:
        return List[ExTensor]()

    fn train(mut self): self.is_training = True
    fn eval(mut self): self.is_training = False
```

Use FP-representable values (0.5, 0.25, 0.125) for deterministic numerical tests.

### 6. Export from `__init__.mojo`

```mojo
from shared.core.sequential import Sequential2, Sequential3
```

### 7. Run pre-commit before committing

```bash
pixi run pre-commit run --files shared/core/sequential.mojo tests/shared/core/test_sequential.mojo
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `List[Module]` dynamic dispatch | Store trait objects in a `List` and loop over them | Mojo v0.26.1 requires `ImplicitlyCopyable` for `List` elements; `Module` trait objects don't satisfy this without `UnsafePointer` indirection | Use parametric bounds `[T0: Module, T1: Module]` for compile-time dispatch |
| Single `Sequential[*Ts: Module]` variadic generics | Unify into one struct with variadic type params | Mojo v0.26.1 does not support variadic generic parameters | Two structs (`Sequential2`, `Sequential3`) per depth level; can unify when Mojo adds `*Ts: Module` |
| Adding `Copyable` to Sequential | Making Sequential both `Movable` and `Copyable` | Sub-layers (e.g., `Linear`) may not implement `ImplicitlyCopyable`; forces constraint on all contained layer types | Only implement `Movable`; use ownership transfer `^` in constructors |
| Calling `mojo test` locally | Running tests on host machine | GLIBC version mismatch (`GLIBC_2.32`/`2.33`/`2.34` not found); Mojo requires newer libc than host OS provides | Use Docker container or rely on CI for test execution; pre-commit hooks validate syntax |

## Results & Parameters

### Validated Configuration

```
Mojo version: v0.26.1
Struct traits: Movable only (not Copyable)
Ownership: owned parameters + ^ transfer in __init__ and __moveinit__
Test values: 0.5, 0.25, 0.125, 1.0, 0.0 (FP-representable)
Tolerance: 1e-6 for Float32 comparisons
Pre-commit: all hooks pass (mojo format, trailing whitespace, etc.)
```

### File Locations

```
shared/core/sequential.mojo          # Implementation
tests/shared/core/test_sequential.mojo  # 11 unit tests
shared/core/__init__.mojo            # Exports Sequential2, Sequential3
```

### Test Count by Category

```
Sequential2 tests: 7
  - forward_identity_chain       (shape + value preservation)
  - forward_values               (0.5 * 0.5 = 0.25 numerical check)
  - forward_order                (2.0 * 0.5 = 1.0 ordering check)
  - parameters_combined          (3 + 2 = 5 params)
  - parameters_empty             (0 + 0 = 0 params)
  - train_eval_mode              (mode propagation to both layers)
  - zero_input                   (zeros through identity chain)

Sequential3 tests: 4
  - forward_chain                (0.5^3 = 0.125 numerical check)
  - parameters_combined          (1 + 2 + 3 = 6 params)
  - train_eval_mode              (mode propagation to all 3 layers)
  - shape_preserved              (shape through 3 identity layers)
```

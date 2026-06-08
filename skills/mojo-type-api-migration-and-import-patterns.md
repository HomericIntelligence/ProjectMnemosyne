---
name: mojo-type-api-migration-and-import-patterns
description: "Use when: (1) upgrading Mojo to a new API baseline (Writable->WritableTo, trait/conformance refactors, parametric dtype migration), (2) migrating callers after a Mojo stdlib breaking change, (3) resolving 'import of X is ambiguous' errors caused by two modules exporting the same name, (4) systematically reviewing a large-scale parametric type system migration for dependency order and zero-copy conversion safety, (5) removing ImplicitlyCopyable trait from Mojo structs and fixing resulting compile errors, (6) migrating DType from runtime-typed patterns to native compile-time parametric patterns."
category: architecture
date: 2026-06-07
version: "1.1.0"
user-invocable: false
history: mojo-type-api-migration-and-import-patterns.history
tags: [mojo, type-migration, api-migration, parametric-dtype, implicitlycopyable, import-ambiguity, trait, dtype-native]
---

# Mojo Type API Migration and Import Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Canonical guide for Mojo type/API migrations: version baselines, trait/conformance refactors, parametric dtype migration, ImplicitlyCopyable removal, import-ambiguity aliasing, and dtype-native migration |
| **Outcome** | Consolidated 5 skills covering large-scale parametric migrations (~15,700 lines), ImplicitlyCopyable removal (132 errors/27 files), import-ambiguity aliasing, and native dtype migration (~5000 lines removed) |
| **Verification** | verified-ci |

## When to Use

1. Upgrading Mojo to a new API baseline (stdlib import qualification, keyword removal, trait updates, `Writable`/`write_to`)
2. Migrating callers after a Mojo stdlib breaking change
3. Resolving `error: import of '<Name>' is ambiguous` when two modules export the same name
4. Reviewing/planning a large-scale parametric type system migration (dependency order, zero-copy conversion safety)
5. Removing `ImplicitlyCopyable` from a struct and fixing the resulting compile cascade
6. Migrating custom dtype structs (BF16, FP8, E8M0) to Mojo native compile-time parametric dtypes
7. Fixing trait-conformance errors (`Boolable`, `Hashable`, `Module`) and overload pollution after a version bump

## Verified Workflow

### Quick Reference

```bash
# --- Triage version-upgrade errors first ---
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 \
  | grep ": error:" | sed 's/.*error: //' | sort | uniq -c | sort -rn | head -20

# Fix bottom-up: shared/core/ -> shared/tensor/ -> shared/layers/ -> tests/ -> examples/

# --- Stdlib import qualification (0.26.3 requires std. prefix) ---
find . -name "*.mojo" -exec python3 -c "
import re, sys
c = open(sys.argv[1]).read()
f = re.sub(r'^(from\s+)(testing|sys|memory|collections|algorithm|math|random|time|utils|os|bit)(\s+import\b)',
           r'\1std.\2\3', c, flags=re.MULTILINE)
if f != c: open(sys.argv[1],'w').write(f); print('Fixed:', sys.argv[1])
" {} \;

# --- Remove deprecated 'escaping' keyword ---
find . -name "*.mojo" | xargs grep -l "raises escaping" | while read f; do sed -i 's/raises escaping/raises/g' "$f"; done

# --- Detect overload pollution / parametric vs runtime dtype mismatches ---
grep -rn "_set_float64\|_set_int64" shared/ --include="*.mojo" | grep -v "float\|double"

# --- ImplicitlyCopyable removal: find implicit-copy sites after removing the trait ---
pixi run mojo build shared/core/extensor.mojo 2>&1 | grep "cannot implicitly copy"

# --- Import ambiguity: alias the wrapper at the consumer site ---
# from shared.training import SGD as TrainingSGD   # alias wrapper, keep primitive short

# --- Verify incrementally ---
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:"
pixi run mojo test tests/shared/
```

### Detailed Steps

#### 1. Triage before touching code

Run the error-count query. Categorize into **hard errors** (block compilation: struct field type
changes, import renames, keyword removal) vs **warnings** (deprecation notices — fix in a separate
PR). Fix bottom-up: types used everywhere first (`shared/core/` → `shared/tensor/` → `shared/layers/`
→ `tests/` → `examples/`).

#### 2. Removing ImplicitlyCopyable from a struct

`ImplicitlyCopyable` on a struct with `List`/`Dict`/`String`/manual-refcount fields triggers
**bitwise copies** that bypass `__copyinit__`, leaving the refcount un-incremented → double-free
crashes (often AFTER assertions pass). Remove the trait and fix the cascade:

```mojo
# BEFORE (buggy): bitwise copy bypasses __copyinit__
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):
    var _shape: List[Int]
    var _refcount: UnsafePointer[Int]

# AFTER: drop ImplicitlyCopyable; ensure __copyinit__ increments refcount
struct ExTensor(Copyable, Movable, Sized):
    fn __copyinit__(out self, existing: Self):
        self._data = existing._data
        self._shape = existing._shape.copy()       # deep-copy List fields
        self._refcount = existing._refcount
        if self._refcount:
            self._refcount[] += 1                  # CRITICAL
```

Add an explicit `copy()` via struct-literal construction (`__copyinit__` is NOT directly callable):

```mojo
fn copy(self) -> Self:
    var result = Self {
        _data: self._data, _shape: self._shape.copy(), _strides: self._strides.copy(),
        _dtype: self._dtype, _numel: self._numel, _refcount: self._refcount,
    }
    if result._refcount:
        result._refcount[] += 1
    return result^        # transfer ownership
```

Then fix each implicit-copy site flagged by the compiler:

| Pattern | Before | After |
| --------- | -------- | ------- |
| List index | `var t = list[i]` | `var t = list[i].copy()` |
| Tuple unpack | `var a, b = f()` | `var d = f(); var a = d[0].copy(); var b = d[1].copy()` |
| Fn return | `return self._t` | `return self._t.copy()` |
| Local move | `var r = some_t` | `var r = some_t^` |
| Tuple return | `return (a, b)` | `return (a^, b^)` |
| Closure capture | capture `weights` directly | capture `UnsafePointer.address_of(weights_copy)`, use `escaping` |
| Owned param | `fn argmax(var t: ExTensor)` | `fn argmax(t: ExTensor)` (borrow read-only) |

For large cascades (27+ files) parallelize fixes by module (autograd → core → data → testing/training).

#### 3. Parametric dtype migration (runtime-typed → compile-time)

Split a runtime-typed struct into a parametric `Tensor[dtype: DType]` plus a type-erased wrapper:

```mojo
struct Tensor[dtype: DType = DType.float32](TensorLike):
    var _data: UnsafePointer[Scalar[Self.dtype]]   # NO _dtype field — it's Self.dtype at compile time
    fn __getitem__(self, index: Int) raises -> Scalar[Self.dtype]:
        return self._data[index]                   # zero-branch typed access
```

Zero-copy conversion must share the refcount:

```mojo
fn __init__(out self, data: UnsafePointer[Scalar[dtype]], shape: List[Int],
            strides: List[Int], refcount: UnsafePointer[Int]):
    self._refcount = refcount
    self._refcount[] += 1     # CRITICAL: shared ownership
```

Add a backward-compat alias before removing the old name so all code compiles during migration:

```mojo
comptime ExTensor = AnyTensor
```

Critical rules:

- `UnsafePointer[Scalar[dtype]]` auto-scales — do NOT multiply by dtype size.
- Module boundaries (`forward(AnyTensor) -> AnyTensor`) can't be parametric in Mojo 0.26.1; use
  `input.as_tensor[dtype]()` → compute → `result.as_any()`.
- **Overload pollution**: importing `Tensor[dtype]` at all into a file with `AnyTensor` operations
  pollutes overload resolution (`cannot implicitly convert AnyTensor to AnyTensor`). Extract all
  typed code to an isolated package with no `AnyTensor` imports.
- Break circular imports with function-scoped local imports inside method bodies.

Review methodology for planning the migration: launch 3 parallel exploration agents (core struct
patterns, consumer/collection patterns, language-feature verification) + 2 plan agents (feasibility/
safety, phase-ordering/scope). Use a 3-layer package split (base = zero-dep utilities; tensor =
typed + type-erased + traits; core = ops + layers). Update trait signatures BEFORE parameterizing the
structs that implement them; defer file renames to a final cleanup phase. Cross-reference scope
estimates against actual grep counts and multiply 1.5–3×.

#### 4. Trait conformance fixes

- **Boolable** requires non-raising `__bool__`. Split into non-raising `__bool__` (returns False for
  multi-element, NumPy semantics) + raising `bool_strict()` (PyTorch-style). `Boolable` and
  `raises __bool__` are mutually exclusive.
- Trait list must be alphabetical: `Boolable` before `Copyable`.
- **Hashable**: implementing `__hash__` is not enough — declare `Hashable` in the trait list too.
- **Module**: requires `train(mut self)` and `inference(mut self)` (no-ops for stateless layers) and
  `fn forward(mut self, ...)` (not `self`).
- Wrapper structs containing `Sequential` (Movable-only) must NOT declare `Copyable`.
- **Writable / write_to** (0.26.3+): full migration replaces `__str__` with `write_to`; transitional
  delegation has `write_to` call `str(self)` while `__str__` is still used externally.

#### 5. Import ambiguity — local alias pattern

Mojo 1.0 rejects importing the same identifier from two modules with
`error: import of '<Name>' is ambiguous` (Python silently shadowed). When both names are intentional
public API referring to different types, alias the **wrapper** at the consumer site:

```mojo
# shared.training.SGD is a struct wrapper; shared.SGD re-exports the lower-level
# shared.autograd.optimizers.SGD. Two distinct types, same name — alias the wrapper here.
from shared.training import SGD as TrainingSGD   # alias wrapper -> <Module><Type>
from shared import SGD                           # keep primitive short
```

Apply only when ALL are true: two modules export the name, both are documented public API with
consumers, the names are **different types**, and one file needs both. Otherwise de-duplicate instead
of aliasing. Add a comment block citing both source paths (Mojo errors/traces don't preserve aliases).

#### 6. Dtype-native migration

Replace custom dtype structs (BF16, FP8, BF8, FP4, E8M0) with Mojo native types. Use `comptime` (not
deprecated `alias`):

```mojo
comptime BF16 = DType.bfloat16
comptime FP8  = DType.float8_e4m3fn
comptime E8M0 = DType.float8_e8m0fnu
```

**E8M0 (exponent-only) native conversion does NOT work** — extract the exponent manually:

```mojo
fn _e8m0_from_float32(scale: Float32) -> Scalar[E8M0]:
    if scale <= 0.0 or isnan(scale): return bitcast[E8M0, 1](SIMD[DType.uint8, 1](0))
    if isinf(scale):                 return bitcast[E8M0, 1](SIMD[DType.uint8, 1](255))
    var bits = bitcast[DType.uint32, 1](SIMD[DType.float32, 1](scale))
    var float_exp = ((bits[0] >> 23) & 0xFF).cast[DType.uint8]()
    if (bits[0] & 0x7FFFFF) >= 0x400000 and float_exp < 255: float_exp += 1   # round-to-nearest pow2
    return bitcast[E8M0, 1](SIMD[DType.uint8, 1](float_exp))
```

Raw-byte access uses `bitcast[DType.uint8, 1](scalar)[0]`; construct from bits with
`bitcast[FP8, 1](SIMD[DType.uint8, 1](raw_byte))`. Widen E8M0 test tolerances (power-of-2 scale can be
up to 2× off optimal). `DType.bfloat16` is NOT supported on Apple Silicon.

#### 7. Verify incrementally

After each directory: `pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:"`,
then `pixi run mojo test tests/shared/`. Local hosts may lack GLIBC 2.32+ — use CI/Podman for
execution. Local commits without mojo-format: `SKIP=mojo-format git commit -m "..."`.

#### 8. Reverse-dependency cycle breaking — decision tree

When a module-level import from Package A appears in Package B (a reverse dependency creating a
cycle), pick the fix by what the imported symbol actually is:

```text
Found module-level import from Package A in Package B (reverse dep):

1. Is the file a pure wrapper with zero callers?
   YES → DELETE the file (removes 100+ lines of dead code)

2. Is the imported function a pure utility with no package deps?
   YES → MOVE to shared/base/ (break cycle at root)

3. Is the import used in only 1-2 function bodies?
   YES → Convert to function-scoped import (deferred resolution)

4. Is it a constants-only import?
   YES → KEEP (constants don't create compilation cycles)

5. None of the above?
   → Consider co-locating or inlining the logic
```

#### 9. Test-writing gotchas during migration

**`assert_value_at` 4th-positional trap**: the signature is
`(tensor, index, expected, tolerance, message)`. Passing a string as the 4th positional argument
silently coerces it to `Float64` for the `tolerance` parameter — always use the `message=` keyword:

```mojo
# WRONG — string interpreted as tolerance: Float64
assert_value_at(parts[0], 0, 0.0, "should be 0.0")

# CORRECT — message= keyword bypasses the tolerance parameter
assert_value_at(parts[0], 0, 0.0, message="should be 0.0")
```

**Same-scope ASAP refcount trap**: Mojo's ASAP destruction does NOT fire within the same scope, so a
refcount test that creates the source and the converted tensor in one scope (source-dies /
target-survives) always passes regardless of correctness. Use a helper function that forces the
source out of scope before the assertion:

```mojo
fn _make_view() -> ExTensor:
    var src = make_source()       # source lives only inside the helper
    return src.as_view()^         # forces src to be destroyed on return
# Caller asserts on the returned view — source is now genuinely out of scope.
```

#### 10. Hyphenated-directory import ban

Mojo cannot import from directories whose names contain hyphens. Rename the directory at the OS level
(`git mv my-pkg my_pkg`) and update every import path, CI config glob, and doc reference to match.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Package split as first step | Physically moved files before code changes | 500+ import path changes with zero functional value; re-export chain limitation (#3754) breaks transparent compat | Keep files in place; create new packages only for genuinely new files |
| Auto-parameterized return types | `fn relu(t: Tensor) -> Tensor` without `[dt: DType]` | `failed to infer parameter 'dtype'`; codebase had 0 existing uses (strong signal) | All overloads need explicit `[dt: DType]`; zero existing uses = feature likely doesn't work |
| `bitcast[Float32]()` in parametric layers | Copied params via `bitcast[Float32]()` regardless of dtype | Silent data corruption for float64/float16 — bitcast reinterprets bytes | Use typed `Tensor[dtype]._data` directly; no bitcast |
| Removing `ImplicitlyCopyable` as the "easy" fix | Dropped the trait to fix a List field | 62-/132-file cascade of implicit-copy errors | Map cascade depth first; sometimes prefer `InlineArray` field replacement |
| `return self` in `copy()` | Returned `self` from the copy method | `cannot implicitly copy 'ExTensor'` — still needs the removed implicit copy | Build via struct literal + `^`, not `return self` |
| Call `__copyinit__` directly | `return Self.__copyinit__(self)` | `__copyinit__ is not directly callable` | Lifecycle methods are compiler-invoked only; use struct-literal construction |
| Tuple unpacking after trait removal | `var a, b = f()` | Tuple destructure requires every element ImplicitlyCopyable | Use indexing: `d[0].copy()` |
| Closure capturing non-ImplicitlyCopyable | Captured `weights` directly | `cannot synthesize __copyinit__ for closure` | Capture `UnsafePointer.address_of(copy)` and mark `escaping` |
| Delegating `__bool__` to `item()` | `fn __bool__(self) -> Bool { return self.item() != 0.0 }` | `item()` raises; non-raising `__bool__` can't call it | Access `_numel`/buffer directly; delegate to `item()` only in `bool_strict()` |
| `List[Module]` dynamic dispatch | Stored trait objects in a `List` | List elements need ImplicitlyCopyable; trait objects don't satisfy it | Use parametric bounds `[T0: Module, T1: Module]` for compile-time dispatch |
| Public typed wrappers beside AnyTensor fns | `add_typed[dt]` next to `add(AnyTensor)` in one file | 242 overload-resolution errors — `Tensor[dtype]` in scope pollutes resolution | Extract typed code to an isolated package; `Tensor[dtype]` must not appear with `AnyTensor` ops |
| Rename the wrapper struct to fix ambiguity | Considered renaming `shared.training.SGD` | Breaks every downstream `from shared.training import SGD` consumer | Fix at the consumer with an alias, not at the producer; API stability wins |
| Import a different symbol to dodge ambiguity | `from shared.training.optimizers import sgd_step` instead of `SGD` | `sgd_step` is a function, not the struct the test covered | Don't substitute a different shape just to dodge a name collision |
| Split test file to avoid ambiguity | Separate `shared.training` and top-level `shared` imports | Defeats the import-coverage test's regression signal | Alias instead of shrinking a test's scope |
| `def __init__(out self, *, take existing: Self)` | Used `take` in a `def` for ownership transfer | `mojo format` strips the space → `takeexisting`; compiles silently, field inaccessible | Delete dead constructors or use `fn __init__(out self, owned existing: Self)` |
| Skipping ADR re-test on version bump | Assumed a bump auto-supersedes old limitation ADRs | ADR stayed "Accepted" for months while FP16 SIMD already worked | Write a concrete test for the claimed limitation when bumping Mojo |
| String as 4th positional arg to `assert_value_at` | `assert_value_at(tensor, idx, 0.0, "message")` | Mojo coerced the `StringLiteral` to `Float64` for the `tolerance` parameter | Always use the `message=` keyword; check the function signature before writing tests |
| `__getitem__` widened to return `Float64` | Wider return type to accept more assignments | `Float32` cannot implicitly convert to `Float64` in Mojo — broke ~108 call sites | Mojo has zero implicit numeric conversions between float types |
| Mutable-proxy return from `__getitem__` | Return a mutable proxy that accepts any assignment | `"expression must be mutable in assignment"` — ownership blocks reference-returning subscript | Mojo's ownership model does not support reference-returning `__getitem__` |
| Refcount test in same scope | Created source + converted tensor in one scope to assert source-dies/target-survives | Mojo ASAP destruction doesn't fire within the same scope — the test always passes | Use a helper fn that forces the source out of scope before the assertion |

## Results & Parameters

### Parametric Dtype Critical Rules

```yaml
typed_pointer_rule: "UnsafePointer[Scalar[dtype]] auto-scales — do NOT multiply by dtype_size"
module_boundary:    "forward(AnyTensor) -> AnyTensor — can't be parametric in Mojo 0.26.1"
layer_pattern:      "input.as_tensor[dtype]() -> compute -> result.as_any()"
circular_import_fix: "function-scoped local import inside method body"
refcount_protocol:  "share _refcount pointer; increment in ctor/copyinit; both __del__ decrement"
overload_pollution: "Tensor[dtype] in a file with AnyTensor ops -> isolate typed code in its own package"
```

### Boolable Split (copy-paste ready)

```mojo
fn __bool__(self) -> Bool:                # non-raising; False for multi-element
    if self._numel != 1: return False
    return self._get_float64(0) != 0.0

fn bool_strict(self) raises -> Bool:      # raising; strict
    return self.item() != 0.0
```

### Dtype Type Mapping

| Custom Type | Mojo Built-in | Alias |
| ------------- | --------------- | ------- |
| `BF16` struct | `DType.bfloat16` | `BF16` |
| `FP8` struct | `DType.float8_e4m3fn` | `FP8` |
| `BF8` struct | `DType.float8_e5m2` | `BF8` |
| `FP4_E2M1` struct | `DType.float4_e2m1fn` | `FP4` |
| `E8M0Scale` struct | `DType.float8_e8m0fnu` | `E8M0` |

### Import-Ambiguity Pattern Conditions

Apply the alias fix only when ALL hold: (1) two modules export the same identifier, (2) both are
documented public API with consumers, (3) they are different types, (4) one file needs both. Otherwise
de-duplicate. Convention: alias to `<ModuleName><TypeName>` (e.g., `SGD as TrainingSGD`).

### Deprecated Syntax (Mojo 0.26.1+)

| Deprecated | Replacement |
| ------------ | ------------- |
| `inout self` in `__init__` | `out self` |
| `inout self` in methods | `mut self` |
| `@value` | `@fieldwise_init` + trait list |
| `DynamicVector` | `List` |
| `alias X = ...` | `comptime X = ...` |
| `-> (T1, T2)` tuple return | `-> Tuple[T1, T2]` |

### Agent Coordination for Bulk Migrations

```text
Agent 1: shared/core/   (types, tensor, memory)      — must finish first
Agent 2: shared/layers/ (NN layers)                  — parallel after Agent 1
Agent 3: shared/training/ (optimizers, losses)       — parallel after Agent 1
Agent 4: tests/ + examples/ (nothing depends on)     — runs last
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Epic #4998; PRs #5002-#5023, #5200-#5212; Mojo 0.26.1 → 0.26.3 | 600+ files, ~15,700 lines parametric dtype/trait/API migration |
| ProjectOdyssey | PR #2962 | ImplicitlyCopyable removal from ExTensor: 132 errors / 27 files; CI 45/45 |
| ProjectOdyssey | Epic #4998 (planning review) | 4,700-line ExTensor split review: 4 blockers/8 high; 3-layer split; 7→17 phases |
| ProjectOdyssey | PR #5388 (2026-05-10) | `import of 'SGD' is ambiguous` resolved via `SGD as TrainingSGD` consumer alias |
| ProjectOdyssey | dtype-native migration | Custom BF16/FP8/E8M0 structs → native DType: ~5000 lines removed, ~750 added |

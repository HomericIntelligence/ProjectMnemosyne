---
name: mojo-type-and-api-migration
description: "Canonical guide to Mojo type and API migration across language versions: parametric dtype migration, Writable -> WritableTo transition, API version baselines, trait/conformance refactors, method API symmetry, parametric vs runtime dtype, decorator/method-wrapper changes. Use when: (1) upgrading Mojo to a new API baseline, (2) migrating callers after a Mojo stdlib breaking change, (3) reconciling parametric dtype usage with new runtime dtype patterns, (4) fixing trait-conformance compile errors after a stdlib upgrade."
category: architecture
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: mojo-type-and-api-migration.history
tags: [merged, mojo, type-migration, api-migration, parametric-dtype, trait]
---

# Mojo Type and API Migration — Canonical Guide

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Consolidated canonical guide for Mojo type and API migration patterns across language versions |
| **Outcome** | Merged 40 skills (M3 sub-PR 2/4) covering stdlib import changes, parametric dtype, trait conformance, Writable/write\_to, overload disambiguation, Python interop, and more |
| **Coverage** | Mojo 0.26.1 → 0.26.3 and beyond; ProjectOdyssey ~600 files, ~15,700 lines |

## When to Use

1. Upgrading Mojo to a new version with breaking API changes (stdlib imports, keyword removal, trait updates)
2. Migrating a struct from runtime-typed to parametric (compile-time typed) design
3. Fixing `Boolable`, `Writable`, `ImplicitlyCopyable`, or other trait-conformance compile errors
4. Replacing deprecated `comptime` type aliases with canonical types
5. Resolving `cannot implicitly convert 'X' value to 'X'` circular-import type identity errors
6. Fixing overload ambiguity, parameter/method name collisions, or `escaping` closure mismatches
7. Migrating `__str__`/`Stringable` to `write_to`/`Writable` for Mojo 0.26.3+
8. Replacing `Python.import_module` calls with native Mojo stdlib equivalents
9. Adding FP16 SIMD paths after a version bump that fixes a prior compiler limitation
10. Promoting internal constants or API names to the public package surface

## Verified Workflow

### Quick Reference

```bash
# --- Version upgrade: triage errors first ---
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sed 's/.*error: //' | sort | uniq -c | sort -rn | head -20

# --- Fix in dependency order: core types → tensor → layers → tests ---
# shared/core/ first; shared/tensor/ second; shared/layers/ third; tests/ last

# --- Stdlib import qualification (0.26.3) ---
find . -name "*.mojo" -exec python3 -c "
import re, sys
content = open(sys.argv[1]).read()
fixed = re.sub(
    r'^(from\s+)(testing|sys|memory|collections|algorithm|math|random|time|utils|os|bit)(\s+import\b)',
    r'\1std.\2\3', content, flags=re.MULTILINE)
if fixed != content:
    open(sys.argv[1], 'w').write(fixed)
    print('Fixed:', sys.argv[1])
" {} \;

# --- Remove deprecated 'escaping' keyword ---
find . -name "*.mojo" | xargs grep -l "raises escaping" | while read f; do
  sed -i 's/raises escaping/raises/g' "$f"
done

# --- Audit __str__ / Stringable for Writable migration ---
grep -rn "def __str__" shared/ --include="*.mojo"
grep -rn "Writable" shared/ --include="*.mojo" -l | xargs grep -l "def __str__"

# --- Find parametric vs runtime dtype mismatches ---
grep -rn "_set_float64\|_set_int64" shared/ --include="*.mojo" | grep -v "float\|double"

# --- Verify package builds after fixes ---
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:"
pixi run mojo test tests/shared/
```

### Step 1 — Triage Before Touching Code

Run the error-count query above. Categorize into:

- **Hard errors** (block compilation): struct field type changes, import renames, keyword removal
- **Warnings** (don't block): deprecation notices — fix these in a separate PR after hard errors

Fix bottom-up: types used everywhere must be fixed first.

### Step 2 — Stdlib Import Qualification

Mojo 0.26.3 requires `std.` prefix for stdlib modules previously imported without qualification.
The bulk-fix script above handles 92+ test files safely. Also remove `escaping` from `fn` type
parameters — the keyword was removed in 0.26.3.

### Step 3 — Parametric Dtype Migration

When splitting a runtime-typed struct (`UnsafePointer[UInt8]`) into a parametric type
(`Tensor[dtype: DType]` with `UnsafePointer[Scalar[dtype]]`) plus a type-erased wrapper:

```mojo
struct Tensor[dtype: DType = DType.float32](TensorLike):
    var _data: UnsafePointer[Scalar[Self.dtype]]
    # NO _dtype field — it's Self.dtype at compile time

    fn __getitem__(self, index: Int) raises -> Scalar[Self.dtype]:
        return self._data[index]  # Zero-branch typed access
```

Zero-copy conversion (shared refcount):

```mojo
fn __init__(out self, data: UnsafePointer[Scalar[dtype]], shape: List[Int],
            strides: List[Int], refcount: UnsafePointer[Int], ...):
    self._refcount = refcount
    self._refcount[] += 1  # CRITICAL: shared ownership
```

Add backward-compat alias before removing the old name:

```mojo
comptime ExTensor = AnyTensor  # ALL existing code compiles during migration
```

### Step 4 — Trait Conformance Fixes

**Boolable**: `Boolable` requires non-raising `__bool__`. Split into two methods:

```mojo
fn __bool__(self) -> Bool:          # Non-raising; returns False for multi-element (NumPy semantics)
    if self._numel != 1:
        return False
    return self._get_float64(0) != 0.0

fn bool_strict(self) raises -> Bool:  # Raising; PyTorch-style strict
    return self.item() != 0.0
```

**Writable / write\_to** (Mojo 0.26.3+). Full migration (preferred):

```mojo
struct MyStruct(Writable):
    def write_to(self, mut writer: Some[Writer]):
        writer.write("MyStruct(", self.value, ")")
```

Transitional delegation (when `__str__` still called externally):

```mojo
struct MyStruct(Writable, Stringable):
    def write_to(self, mut writer: Some[Writer]):
        writer.write(str(self))  # delegates during transition

    def __str__(self) -> String:
        return "MyStruct(" + str(self.value) + ")"
```

**Sequential parametric containers** — Mojo 0.26.1 has no `List[Trait]` dynamic dispatch. Use
compile-time parametric bounds instead:

```mojo
struct Sequential2[T0: Module, T1: Module](Movable):
    var layer0: T0
    var layer1: T1

    fn forward(mut self, input: ExTensor) raises -> ExTensor:
        return self.layer1.forward(self.layer0.forward(input))
```

**Module trait conformance**: `forward` must be `fn forward(mut self, ...)` (not `self`).

### Step 5 — Circular Import Resolution

When two Mojo modules form a cycle, the compiler reports
`cannot implicitly convert 'X' value to 'X'` even though both sides look identical. Fix: use
function-scoped local imports to break the cycle:

```mojo
fn as_tensor[dtype: DType](self) raises -> Tensor[dtype]:
    from shared.tensor.tensor import Tensor  # local import breaks cycle
    return Tensor[dtype](self._data.bitcast[Scalar[dtype]](), ...)
```

### Step 6 — Overload and Collision Fixes

**Parameter/method name collision** (`struct Foo[dtype: DType]` + `fn dtype() -> DType`): the
collision doesn't exist in Mojo 0.26.1 — test the actual compiler before "fixing" it.

**Overload disambiguation** with `is_defined`:

```mojo
@parameter
if is_defined["APPLE_SILICON"]():
    ...
```

**Float literal overloads**: add `Float32` overload alongside `Float64` to avoid users needing
`Float64(9.5)` everywhere.

**`escaping` closure regression**: `escaping` is part of the fn type signature. Removing it is a
breaking API change — preserve it if callers pass escaping closures.

### Step 7 — API Cleanup Patterns

**Deprecated alias removal**: always grep for all occurrences before removing — aliases appear in
return types, docstrings, and test files. Replace with the ORIGINAL aliased-to type, not a new
invented name.

**Hyphenated directory rename**: Mojo cannot import from directories with hyphens. Rename at OS
level and update all import paths, CI configs, and docs.

**Promote constants to public API**: move shared constants (epsilon, tolerance) to a lightweight
module imported without pulling in heavy dependencies.

**Public API table**: distinguish "importable today" from "planned future" in `__init__.mojo`
docstring tables.

**Python interop → stdlib**: replace `Python.import_module("os")` / `Python.import_module("pathlib")`
with native Mojo stdlib (`os.listdir`, etc.) once available. Use function-scoped Python bridge only
for ops not yet in stdlib.

### Step 8 — Verify Incrementally

```bash
# After each directory:
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:"

# Run tests (CI environment; GLIBC mismatch prevents local execution on older hosts)
pixi run mojo test tests/shared/

# Track warnings separately
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": warning:" | wc -l
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Package split as first step | Moved files to `shared/base/`, `shared/tensor/` physically before code changes | 500+ import path changes with zero functional value; Mojo re-export chain limitation (\#3754) breaks transparent backward compat | Keep files in place; create new packages only for genuinely new files |
| Auto-parameterized return types | `fn relu(t: Tensor) -> Tensor` without explicit `[dt: DType]` | `failed to infer parameter 'dtype'` — Mojo cannot infer return-type params from input params | All overloads need explicit `[dt: DType]` parameter |
| Renaming struct param to avoid collision | Renamed `dtype` param to `dt` on struct to avoid `fn dtype()` collision | The collision doesn't exist in Mojo 0.26.1 — compiler accepts both | Test the actual compiler before fixing assumed issues |
| `bitcast[Float32]()` in parametric layers | Copied layer parameters via `bitcast[Float32]()` regardless of dtype | Silent data corruption for float64/float16 — bitcast reinterprets bytes | Use typed `Tensor[dtype]._data` directly; no bitcast needed |
| B4 refcount test in same scope | Created source + converted tensor in same scope to assert data valid | Mojo ASAP destruction doesn't fire within same scope — test always passes | Use helper functions that force source out of scope before assertion |
| Removing `ImplicitlyCopyable` to fix List field | Dropped the trait as the "easy" fix | Caused 62-file cascade of implicit copy errors across codebase | Prefer `InlineArray` field replacement; map cascade depth before choosing approach |
| `sed` bulk `fn` → `def` | Used sed to replace `fn` globally | Replaces `fn` inside comments, strings, identifiers | Use targeted regex at definition sites only; `fn` is only a warning (not error) in 0.26.3 |
| Delegating `__bool__` to `item()` | `fn __bool__(self) -> Bool { return self.item() != 0.0 }` | `item()` raises for multi-element tensors; non-raising `__bool__` cannot call raising fn | Access `_numel` and buffer directly; delegate to `item()` only in `bool_strict()` |
| `List[Module]` dynamic dispatch | Store trait objects in a `List` | Requires `ImplicitlyCopyable` for `List` elements; trait objects don't satisfy it without `UnsafePointer` | Use parametric bounds `[T0: Module, T1: Module]` for compile-time dispatch |
| Single `Sequential[*Ts: Module]` | Unify into one struct with variadic type params | Mojo 0.26.1 does not support variadic generic parameters | Two structs (`Sequential2`, `Sequential3`) per depth; can unify when Mojo adds `*Ts: Module` |
| `set(UInt32)` assuming bitcast semantics | `tensor.set(0, UInt32(0x7FC00000))` expecting raw bit write | Delegates to `_set_int64` which silently ignores float dtypes | Check the implementation of `set()` overloads — numeric conversion != bitcast |
| Automated sed for Pattern-A comments in set() | `sed` to move inline comments out of parens in `set()` calls | sed is line-oriented; failed on multi-paren depth where comment is inside nested parens | Manual inspection per file; `grep -n "set(.*#"` locates candidates |
| Moving AnyTensor only to break import cycle | Moved AnyTensor from shared.core to shared.tensor | Fixed some cycles but other cross-package imports maintained the cycle | Moving a type can leave other cycles; audit ALL cross-package imports before moving |
| Skipping ADR re-test on version bump | Assumed version bump automatically supersedes old ADRs | ADR-010 stayed "Accepted" for months while FP16 SIMD already worked in 0.26.3 | Always write a concrete test for the claimed limitation when bumping Mojo version |
| Multiple agents on overlapping files | Ran agents fixing different files simultaneously without file locks | Merge conflicts when agents modified the same shared type | Assign agents to non-overlapping directories; one agent per directory subtree |

## Results & Parameters

### Version Upgrade Command Reference

```bash
# Get unique error categories
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sort -u

# Fix order (bottom-up dependency)
# shared/core/ → shared/tensor/ → shared/layers/ → tests/ → examples/

# After each phase, verify:
pixi run mojo package -I . shared -o /tmp/shared.mojopkg && echo "OK"
```

### Writable Migration Decision Table

| Condition | Pattern |
| ----------- | --------- |
| `__str__` used only for string representation | Full migration (replace with `write_to`) |
| `__str__` called by other code (logging, display) | Transitional delegation (`write_to` calls `str(self)`) |
| Formatting logic is simple (one or two fields) | Full migration |
| Formatting logic is complex or multi-line | Transitional delegation |

### Parametric Dtype Critical Rules

```yaml
typed_pointer_rule: "UnsafePointer[Scalar[dtype]] auto-scales — do NOT multiply by dtype_size"
module_boundary: "forward(AnyTensor) -> AnyTensor — can't be parametric in Mojo 0.26.1"
layer_pattern: "input.as_tensor[dtype]() → compute → result.as_any()"
circular_import_fix: "Function-scoped local import inside method body"
refcount_protocol: "Share _refcount pointer; increment in constructor; both __del__ methods decrement"
```

### Agent Coordination for Bulk Migrations

```
Agent 1: shared/core/           (types, tensor, memory)       — must finish first
Agent 2: shared/layers/         (neural network layers)        — parallel after Agent 1
Agent 3: shared/training/       (optimizers, loss functions)   — parallel after Agent 1
Agent 4: tests/ + examples/     (nothing depends on these)     — runs last
```

### set() API Migration Patterns (bitcast→set())

```bash
# Find Pattern A: inline comment inside set() parens (# swallows closing delimiter)
grep -n "set(.*#.*)" tests/ -r --include="*.mojo"

# Find Pattern B: empty Float32(()) calls
grep -n "Float32(())" tests/ -r --include="*.mojo"

# Find Pattern C: garbled = in call args
grep -n "set(.*= " tests/ -r --include="*.mojo"
```

Fix Pattern A: move `# comment` to after all closing `)`.
Fix Pattern B: remove `Float32(())` wrapper and collapse actual value to one line.
Fix Pattern C1: restore original comparison expression. Fix Pattern C2: comment out all
references to commented-out declaration.

### GLIBC Constraint

Mojo binary requires GLIBC 2.32+ which is unavailable on many host OSes. Always use CI or Docker
for Mojo compilation. For local commits with mojo-format unavailable:

```bash
SKIP=mojo-format git commit -m "fix: ..."
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Epic \#4998; PRs \#5002-\#5023, \#5200-\#5212; Mojo 0.26.1 → 0.26.3 | 600+ files, ~15,700 lines; 40 absorbed skills across parametric dtype, trait conformance, API migration |

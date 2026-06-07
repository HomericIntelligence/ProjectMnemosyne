---
name: mojo-type-and-api-migration
description: "Canonical guide to Mojo type and API migration across language versions: parametric dtype migration, Writable -> WritableTo transition, API version baselines, trait/conformance refactors, method API symmetry, parametric vs runtime dtype, decorator/method-wrapper changes. Use when: (1) upgrading Mojo to a new API baseline, (2) migrating callers after a Mojo stdlib breaking change, (3) reconciling parametric dtype usage with new runtime dtype patterns, (4) fixing trait-conformance compile errors after a stdlib upgrade."
category: architecture
date: 2026-06-07
version: "1.1.0"
user-invocable: false
verification: verified-local
history: mojo-type-and-api-migration.history
tags: [merged, mojo, type-migration, api-migration, parametric-dtype, trait]
---

# Mojo Type and API Migration — Canonical Guide

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
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

# --- Detect formatter bug: space-stripped take/owned modifiers ---
grep -rn "\btake[A-Z]\|\bowned[A-Z]" examples/ shared/
grep -rn "def.*\*, take \|def.*\*, owned " examples/ shared/

# --- Detect overload pollution from Tensor[dtype] in core files ---
grep -l "from shared.tensor.tensor import Tensor" \
  shared/core/arithmetic.mojo shared/core/elementwise.mojo \
  shared/core/activation.mojo shared/core/matrix.mojo
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

Trait list order: `Boolable` must come alphabetically before `Copyable`:

```mojo
struct ExTensor(
    Boolable,       # alphabetical position BEFORE Copyable
    Copyable,
    Hashable,
    ImplicitlyCopyable,
    Movable,
    ...
):
```

Prior workaround (before the split): tests called `t.__bool__()` directly when `Bool(t)` was
not yet available. Error `"no matching function in initialization"` with note about `Boolable`
trait conformance failure indicates the struct still has a raising `__bool__`.

Boolean syntax comparison:

| Syntax | Requires | Works with `raises __bool__`? |
| -------- | ---------- | ------------------------------- |
| `Bool(t)` | `Boolable` trait (non-raising) | No |
| `t.__bool__()` | Just the method | Yes (workaround) |
| `t.bool_strict()` | Just the method | Yes (post-split canonical) |
| `if t:` | Non-raising OR raising `__bool__` | Yes |

**Hashable**: implementing `__hash__` alone is not sufficient — `Hashable` must also be declared
in the struct trait list. Error `"no matching function in call to hash"` indicates the trait
declaration is missing even when the method exists. Fix: add `Hashable` to the trait list
(one-line change).

**Module trait**: requires both `train(mut self)` and `inference(mut self)` even for stateless
layers (allows stateful layers like BatchNorm to switch modes). Add no-op implementations
for stateless layers.

**Sequential containers**: wrapper structs containing `Sequential` must NOT declare `Copyable` —
`Sequential` is `Movable`-only; the compiler rejects copying non-Copyable fields.

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

**Overload pollution**: having `Tensor[dtype]` in scope at all (even private functions with
`Tensor[dtype]` signatures in the same file) pollutes overload resolution. Error
`"cannot implicitly convert AnyTensor to AnyTensor"` signals multiple candidate overloads,
not a type-path mismatch. Of 242 build errors observed, 188 were this exact message. Fix:
extract typed code to an isolated package with no `AnyTensor` imports.

**Decision tree for reverse dependencies**:

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

**Method wrapper template** — insert after `slice()` (analogous shape operation):

```mojo
fn tile(self, reps: List[Int]) raises -> ExTensor:
    from shared.core.shape import tile as _tile   # local-scope import
    return _tile(self, reps)

fn split(self, num_splits: Int, axis: Int = 0) raises -> List[ExTensor]:
    from shared.core.shape import split as _split
    return _split(self, num_splits, axis)^   # ^ transfers ownership for List returns
```

**API symmetry audit**:

```bash
# 1. What's exported from the module
grep -n "split\|tile\|repeat" shared/core/__init__.mojo

# 2. What methods already exist on the struct
grep -n "^    fn " shared/core/extensor.mojo | grep -E "split|tile|repeat"
# The difference is the set of missing wrappers
```

**assert\_value\_at gotcha**: signature is `(tensor, index, expected, tolerance, message)`.
Passing a string as the 4th positional argument fails because Mojo converts it to `Float64`.
Always use the `message=` keyword:

```mojo
# WRONG — string interpreted as tolerance: Float64
assert_value_at(parts[0], 0, 0.0, "should be 0.0")

# CORRECT — message= keyword bypasses the tolerance parameter
assert_value_at(parts[0], 0, 0.0, message="should be 0.0")
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
invented name. `Edit` with `replace_all=True` is safe on PascalCase Mojo type names — no
substring collision risk; one pass handles signatures, docstrings, and body.

Import-vs-comment rule: only add a concrete-type import if the alias is used as an actual type
annotation, not just in a comment.

Partial backward-compat test file removal: removing some aliases requires selective removal of
relevant imports, test functions, and `main()` calls, plus updating the test count printed in
`main()`.

**Hyphenated directory rename**: Mojo cannot import from directories with hyphens. Rename at OS
level and update all import paths, CI configs, and docs.

**Promote constants to public API**: move shared constants (epsilon, tolerance) to a lightweight
module imported without pulling in heavy dependencies.

**Public API table**: distinguish "importable today" from "planned future" in `__init__.mojo`
docstring tables.

**Python interop → stdlib**: replace `Python.import_module("os")` / `Python.import_module("pathlib")`
with native Mojo stdlib (`os.listdir`, etc.) once available. Use function-scoped Python bridge only
for ops not yet in stdlib.

### Step 8 — Deprecated Syntax for Mojo 0.26.1+

| Deprecated Pattern | Replacement |
| -------------------- | ------------- |
| `inout self` in `__init__` | `out self` |
| `inout self` in methods | `mut self` |
| `@value` decorator | `@fieldwise_init` with trait list |
| `DynamicVector` | `List` |
| `-> (T1, T2)` tuple syntax | `-> Tuple[T1, T2]` |

**Formatter bug — space-stripped `take`/`owned` in `def` functions**:
`def __init__(out self, *, take existing: Self)` — `mojo format` strips the space from
`take existing`, transforming it to `takeexisting` as a single parameter name. Compiles
silently but the field is inaccessible. Detection:

```bash
grep -rn "\btake[A-Z]\|\bowned[A-Z]" examples/ shared/
grep -rn "def.*\*, take \|def.*\*, owned " examples/ shared/
```

Fix: delete the constructor if it has no callers (most common), or convert to
`fn __init__(out self, owned existing: Self):` if genuinely needed.

### Step 9 — Worktree Discipline for Alias Removal

When working in git worktrees:

- Changes made in the main checkout do NOT automatically appear in the worktree branch.
  Copy files explicitly to the worktree if needed, or work exclusively in the worktree.
- A prior session may have already applied some changes. Always grep for remaining occurrences
  FIRST before reading a task plan — the actual work may be a tiny fraction of what the plan
  describes.
- Check worktree branch state before applying replace\_all edits: some replacements may already
  be done.

### Step 10 — Verify Incrementally

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
| Using `Bool(t)` in old test before non-raising `__bool__` | Called `Bool(t)` in the raising test before implementing the non-raising split | `Bool(t)` would not raise once `__bool__` became non-raising | After the split, raising tests must call `bool_strict()` explicitly |
| Add `Boolable` to trait list without splitting `__bool__` | Conforming to `Boolable` while keeping `raises` on `__bool__` | `Boolable` requires non-raising `__bool__` — incompatible | `Boolable` and `raises __bool__` are mutually exclusive in Mojo |
| Change `__bool__` to non-raising directly (no split) | Remove `raises` from `__bool__` to satisfy `Boolable` | Breaks multi-element error test semantics | Can't drop `raises` without adding `bool_strict()` and updating all raising tests |
| Public typed wrappers alongside AnyTensor functions | Added `fn add_typed[dt: DType](a: Tensor[dt])` alongside `fn add(a: AnyTensor)` in same file | 242 Mojo overload resolution errors — having `Tensor[dtype]` in scope at all pollutes resolution | Extract all typed code to an isolated package; `Tensor[dtype]` must not appear in files with `AnyTensor` operations |
| `Removing` only public typed wrappers, keeping internal | Removed `add_typed` etc. but kept `_add_typed` and `_dispatch_add` in same file | Same errors persisted — the issue is the `Tensor` TYPE being imported, not function visibility | Import of `Tensor[dtype]` is the problem, not function naming or visibility |
| Change `__getitem__` to return `Float64` | Wider return type to accept more assignments | `Float32` cannot implicitly convert to `Float64` in Mojo; broke 108 call sites | Mojo has zero implicit numeric conversions between float types |
| Proxy/reference return type from `__getitem__` | Return a mutable proxy that accepts any assignment | `"expression must be mutable in assignment"` — Mojo ownership prevents mutable references from `__getitem__` | Mojo ownership model does not support reference-returning subscript |
| `def __init__(out self, *, take existing: Self)` | Used `take` modifier in a `def` function for ownership transfer | Parse error in Mojo 0.26.3; `mojo format` strips the space, turning `take existing` into `takeexisting` — compiles silently but field is inaccessible | Delete dead constructors (zero callers) or convert to `fn __init__(out self, owned existing: Self):` |
| Making changes in main checkout without checking worktree | Edited main checkout directly while working on a worktree branch | Changes don't appear in worktree branch — required manual copy | Always work in the worktree for the PR branch, or explicitly copy changed files |
| `replace_all` on already-handled aliases | Expected to find usages of removed alias name | String not found — prior session had already applied the replacement in worktree | Check worktree branch state before applying; some changes may already be done |
| Assuming detailed plan means lots of work | Issue plan described removing 8 aliases from 6 files | All source/import changes had already been done by a prior session; only 1 comment update remained | Always grep for remaining occurrences FIRST before reading the plan |
| Passing string as 4th positional arg to `assert_value_at` | Called `assert_value_at(tensor, idx, 0.0, "message")` | Mojo tried to convert `StringLiteral` to `Float64` for tolerance parameter | Always use `message=` keyword argument; check function signature before writing tests |
| Keep `forward(self, ...)` immutable for `Module` trait | Left `forward()` as `fn forward(self, ...)` | Mojo compiler: signature mismatch with `Module` trait's `fn forward(mut self, ...)` | `Module` trait requires `mut self` on `forward()` to allow stateful layers |
| Add `Copyable` to struct wrapping `Sequential` | Tried `struct SimpleMLP2(Copyable, Model, Movable)` | `Sequential3` is `Movable` only; compiler rejects copying a non-Copyable field | Don't declare `Copyable` on wrapper structs containing Sequential containers |

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

### Boolable Split — Copy-Paste Ready

```mojo
fn __bool__(self) -> Bool:
    if self._numel != 1:
        return False
    return self._get_float64(0) != 0.0

fn bool_strict(self) raises -> Bool:
    return self.item() != 0.0
```

Trait list addition (alphabetical):

```mojo
struct MyStruct(
    Boolable,   # new — must precede Copyable alphabetically
    Copyable,
    ...
):
```

### Deprecated Alias Removal Command Reference

```bash
# Find all DEPRECATED aliases in a module
grep -n "DEPRECATED" shared/core/<module>.mojo

# Find all alias usages (always grep FIRST before reading the plan)
grep -rn "AliasName" --include="*.mojo" --exclude-dir=".worktrees" --exclude-dir="build" .

# Verify removal complete
grep -rn "AliasName" --include="*.mojo" . || echo "All removed"

# Commit message pattern
# cleanup(<module>): remove deprecated <Module> backward result type aliases
```

### Parametric Dtype Critical Rules

```yaml
typed_pointer_rule: "UnsafePointer[Scalar[dtype]] auto-scales — do NOT multiply by dtype_size"
module_boundary: "forward(AnyTensor) -> AnyTensor — can't be parametric in Mojo 0.26.1"
layer_pattern: "input.as_tensor[dtype]() → compute → result.as_any()"
circular_import_fix: "Function-scoped local import inside method body"
refcount_protocol: "Share _refcount pointer; increment in constructor; both __del__ methods decrement"
```

### Agent Coordination for Bulk Migrations

```text
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

### Module Trait Conformance Checklist

```text
[ ] Module import added to layer file
[ ] "Module" added to struct trait list
[ ] forward(self) changed to forward(mut self)
[ ] train(mut self) method added (no-op for stateless layers)
[ ] inference(mut self) method added (no-op for stateless layers)
[ ] Struct compiles with: pixi run mojo build <layer-file>
[ ] Existing layer tests still pass
```

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
| ProjectOdyssey | Issues \#4091/\#3393, PR \#4869 | Boolable split: Bool(t) + bool\_strict() for ExTensor |
| ProjectOdyssey | PRs \#5062-\#5063; Issue \#4998 | Circular import resolution: 255+ errors fixed via typed package isolation |
| ProjectOdyssey | Issues \#3065/\#3064/\#3267, PRs \#3262/\#3264/\#3833 | Deprecated alias removal for Linear (2) and Conv (6) modules |
| ProjectOdyssey | Issue \#3742 | Module trait conformance for Sequential container integration |

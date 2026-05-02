---
name: mojo-tuple-destructor-clone-pattern
description: "Mojo 0.26.x Tuple does not call __del__ on non-trivial element types; Dataset.__getitem__ must return .clone() not .slice() to prevent ASAN memory leaks. Use when: (1) implementing __getitem__ in Dataset structs that return Tuple[AnyTensor, AnyTensor], (2) debugging ASAN pooled_alloc leaks where leak count matches dataset count, (3) refcount elevation survives tuple scope exit."
category: debugging
date: 2026-04-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - asan
  - leak
  - tuple
  - destructor
  - clone
  - slice
  - refcount
  - dataset
  - mojo
  - getitem
---

# Mojo Tuple Destructor + Dataset.__getitem__ Clone Pattern

Fix ASAN memory leaks caused by `Tuple.__del__` not calling `__del__` on its elements in
Mojo 0.26.x. The correct fix is to return `.clone()` (owned deep copies) from
`__getitem__` rather than `.slice()` views.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-09 |
| **Objective** | Fix ASAN `pooled_alloc` leak in Dataset tests — 7 datasets, 12072 bytes leaked |
| **Outcome** | Success -- returning `.clone()` from `__getitem__` eliminates all ASAN leaks |
| **Repository** | ProjectOdyssey |
| **PR** | #5210 |
| **Fix Commit** | `15fa7f24` |
| **CI Runs Confirming Fix** | `24229346898` and `24229510642` — all 6 ASAN tests green |

## When to Use

- ASAN reports `N bytes in M allocations of pooled_alloc` where M matches the number of
  datasets created in the test (e.g., 7 datasets → 7 pooled_alloc leaks)
- `Dataset.__getitem__` returns a `Tuple[AnyTensor, AnyTensor]` that wraps `.slice()` views
- Caller's tuple variable goes out of scope but the underlying tensor refcounts remain > 0
- Refcounts never reach 0 so `pooled_free` is never called
- The leak byte count matches the exact tensor sizes returned by `__getitem__`

## Verified Workflow

### Quick Reference

```mojo
# OLD — leaks under Mojo 0.26.x Tuple destructor limitation:
fn __getitem__(self, idx: Int) -> Tuple[AnyTensor, AnyTensor]:
    return (
        self.data.slice(idx, idx + 1, axis=0),
        self.labels.slice(idx, idx + 1, axis=0),
    )

# NEW — clone() gives each returned tensor its own refcount=1
# so it IS freed at scope exit regardless of Tuple.__del__ behavior:
fn __getitem__(self, idx: Int) -> Tuple[AnyTensor, AnyTensor]:
    return (
        self.data.slice(idx, idx + 1, axis=0).clone(),
        self.labels.slice(idx, idx + 1, axis=0).clone(),
    )
```

```bash
# Reproduce the leak with ASAN:
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/test_dataset tests/shared/data/test_datasets.mojo
/tmp/test_dataset
# Look for: "N bytes in M allocations of pooled_alloc"
# M should match the number of dataset instances created in the test

# After fix, ASAN should show no leaks:
# Expected: "All tests passed!" with no ASAN errors
```

### Detailed Steps

#### Step 1: Identify the ASAN leak signature

The leak from Tuple destructor omission has a distinctive pattern:

```text
Direct leak of 12072 byte(s) in 7 object(s) allocated from:
    #0 0x... in pooled_alloc
    #4 0x... in shared::data::_datasets_core::AnyTensorDataset::__getitem__
    ...
```

Key indicators:
- The allocation site is `pooled_alloc` inside `__getitem__`
- The count (7 objects) matches exactly how many datasets were created in the test
- The byte count matches the tensor size × number of `__getitem__` calls

#### Step 2: Understand why Tuple.__del__ omits element destruction

In Mojo 0.26.x, `Tuple[AnyTensor, AnyTensor].__del__` does **not** call `AnyTensor.__del__`
on its elements. This is a known Mojo runtime limitation.

The problematic refcount lifecycle when using `.slice()`:

```text
dataset created → AnyTensor._refcount = 1
dataset[0] called → slice view returned, parent refcount += 1 → _refcount = 2
var sample = dataset[0]  # sample holds Tuple[AnyTensor, AnyTensor]
sample goes out of scope → Tuple.__del__ called
  BUT: Tuple.__del__ does NOT call AnyTensor.__del__ on elements
  RESULT: parent refcount stays at 2
dataset goes out of scope → AnyTensor.__del__ called → refcount 2 → 1
  refcount never reaches 0 → pooled_free is NEVER called → LEAK
```

#### Step 3: Apply the clone() fix

Replace `.slice()` return values with `.slice().clone()` in all `__getitem__` methods.

Files changed in ProjectOdyssey:

- `shared/data/_datasets_core.mojo`: `AnyTensorDataset.__getitem__` and
  `EMNISTDataset.__getitem__`
- `shared/data/datasets/cifar10.mojo`: `CIFAR10Dataset.__getitem__`

Why `.clone()` works: each clone has an **independent** refcount initialized to 1. When the
caller's variable goes out of scope, the variable destructor IS called (Mojo does call
destructors for named variables), which decrements the clone's refcount to 0 and triggers
`pooled_free`. The clone does not share its memory with the parent, so the parent's refcount
is completely unaffected.

```text
dataset created → parent AnyTensor._refcount = 1
dataset[0] called → clone() creates independent tensor, clone._refcount = 1
                  → parent refcount UNCHANGED (stays at 1)
var sample = dataset[0]  # sample holds Tuple[AnyTensor, AnyTensor] of clones
sample goes out of scope → Tuple.__del__ called
  BUT: even if Tuple.__del__ skips AnyTensor.__del__, the variable binding
  destructor for `sample` DOES run → clone._refcount 1 → 0 → pooled_free called
dataset goes out of scope → parent refcount 1 → 0 → pooled_free called
  RESULT: no leak
```

#### Step 4: Verify with ASAN

```bash
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/test_dataset tests/shared/data/test_datasets.mojo
/tmp/test_dataset
# Expected output: all tests pass, no ASAN "pooled_alloc" leak reports
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Return `.slice()` views directly from `__getitem__` | Shared parent's refcount through view; relied on Tuple.__del__ to call element destructors | Tuple.__del__ in Mojo 0.26.x does NOT call __del__ on non-trivial element types; refcount never reaches 0; ASAN reports `pooled_alloc` leak matching dataset count | Tuple is not a smart container in Mojo 0.26.x; don't rely on it to destroy elements |
| Give slice() views independent refcounts (not shared with parent) | Modified `slice()` to create a view with its own refcount=1 instead of sharing parent's | Fixed the Tuple destructor leak BUT introduced heap-use-after-free: Mojo's ASAP destruction destroys `dataset` as soon as the last syntactic use is detected; independent refcount=1 on the view meant parent refcount went 0→freed while view still held offset pointer into freed memory; `sample[0][0]` triggered `heap-use-after-free in AnyTensor::_get_float32` | Independent refcount on a view is dangerous with ASAP destruction: the parent can be freed before the view is done using it; views MUST share parent's refcount to extend parent lifetime |
| Leave `.slice()` and add explicit `_ = dataset` to extend lifetime | Attempted to keep dataset alive past last syntactic use using `_ = dataset` binding | Fragile: requires every call site to remember the trick; doesn't fix the Tuple.__del__ omission; breaks encapsulation | Caller should not need to know about internal ownership tricks; fix at the API boundary instead |

## Results & Parameters

### ASAN Error Signatures

#### Leak (before fix -- slice() without clone())

```text
Direct leak of 12072 byte(s) in 7 object(s) allocated from:
    #0 0x... in pooled_alloc (libclang_rt.asan.so)
    #4 0x... in shared::data::_datasets_core::AnyTensorDataset::__getitem__
    #5 0x... in test_datasets::test_anytensor_dataset_basic()
```

Count of 7 = number of dataset instances created across all test functions.
Byte count = sum of `slice()` tensor sizes returned by each `__getitem__` call.

#### Heap-use-after-free (intermediate broken fix -- independent refcount on view)

```text
READ of size 4 at 0x... thread T0
    #0 0x... in shared::tensor::any_tensor::AnyTensor::_get_float32
    ...
0x... is located 0 bytes inside of 576-byte region [0x...,0x...)
freed by thread T0 here:
    #0 0x... in pooled_free (libclang_rt.asan.so)
    #4 0x... in shared::data::_datasets_core::AnyTensorDataset::__del__
```

This occurs because ASAP (As Soon As Possible) destruction frees `dataset` before
`sample[0][0]` can access the slice's data.

### Clone Pattern (Correct Fix)

```mojo
# In any Dataset.__getitem__ that returns Tuple[AnyTensor, AnyTensor]:
fn __getitem__(self, idx: Int) -> Tuple[AnyTensor, AnyTensor]:
    return (
        self.data.slice(idx, idx + 1, axis=0).clone(),   # owned copy
        self.labels.slice(idx, idx + 1, axis=0).clone(), # owned copy
    )
```

### Key Principle

> **Views must share parent refcount. Owned values returned from __getitem__ must be clones.**

If you need to return a tensor that outlives the dataset (i.e., the caller may not hold a
reference to the dataset), use `.clone()`. Views are only safe when the parent is
guaranteed to outlive all views.

### Mojo 0.26.x Known Limitations (Relevant to This Pattern)

| Limitation | Impact | Workaround |
| ------------ | -------- | ------------ |
| `Tuple.__del__` does not call element `__del__` | AnyTensor elements inside tuples are not freed when tuple goes out of scope | Return `.clone()` so elements have independent ownership via variable binding |
| ASAP destruction fires when last syntactic use is detected | Parent tensor freed before views are done using it | Views must share parent refcount, not have independent refcounts |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5210, ASAN dataset leak investigation | Fix commit `15fa7f24`; CI runs `24229346898` and `24229510642` — all 6 ASAN tests green |

## References

- [debugging-slice-view-bad-free-destructor.md](debugging-slice-view-bad-free-destructor.md) — related: bad-free from offset __del__, different bug
- [investigate-mojo-heap-corruption.md](investigate-mojo-heap-corruption.md) — related: general Mojo heap corruption workflow

---
name: mojo-copyinit-double-free
description: "Fix double-free crashes when Mojo synthesizes shallow __copyinit__ for structs with UnsafePointer fields. Use when: (1) a Copyable struct with UnsafePointer has no explicit __copyinit__, (2) struct is stored in List and crashes on lock/use after append, (3) crash is non-deterministic and follows List reallocation."
category: debugging
date: 2026-04-07
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: []
---

## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | `struct MyType(Copyable, Movable)` with `UnsafePointer` fields and no explicit `__copyinit__` gets a synthesized shallow copy |
| **Symptom** | Non-deterministic double-free crash when the struct is stored in a `List` that reallocates |
| **Fix** | Add explicit `__copyinit__` with `alloc` + `memcpy`, and explicit `__moveinit__` that transfers the pointer without allocating |
| **Context** | Discovered in `shared/base/memory_pool.mojo` — `SpinLock` and `AtomicStats` triggered crash during `TensorMemoryPool.__init__` (ProjectOdyssey PR #5199) |
| **Affects** | Any heap-owning `Copyable` struct stored in a `List` that grows via `append()` |

## When to Use

- A `struct` declared `Copyable, Movable` owns heap memory via `UnsafePointer` but has no explicit `__copyinit__`
- The struct is placed into a `List[MyType]` and `append()` is called in a loop
- Crashes are non-deterministic — they depend on `List` reallocation timing (capacity grows 0→1→2→4→8…)
- Crash manifests as a double-free, use-after-free, or segfault during the first use after the list is built
- `mojo build` succeeds; the crash is runtime-only

## Verified Workflow

> Pre-commit passed; CI was pending at time of writing (PR #5199).

1. **Identify the struct** — search for `UnsafePointer` fields in `Copyable` structs:

   ```bash
   grep -rn "UnsafePointer" shared/ --include="*.mojo" -l
   grep -n "Copyable" shared/base/memory_pool.mojo
   ```

2. **Confirm no explicit `__copyinit__`** — if absent, Mojo will synthesize a shallow memberwise copy:

   ```bash
   grep -n "__copyinit__\|__moveinit__" shared/base/memory_pool.mojo
   ```

3. **Write a reproducer test** that triggers `List` reallocation and exercises the struct after build:

   ```mojo
   # tests/shared/base/test_spinlock_double_free.mojo
   fn test_spinlock_list_realloc() raises:
       var locks = List[SpinLock]()
       for _ in range(5):          # forces 0→1→2→4 realloc sequence
           locks.append(SpinLock())
       locks[0].lock()             # crash here if double-free occurred
       locks[0].unlock()
   ```

4. **Add explicit `__copyinit__`** — allocate fresh storage and copy data:

   ```mojo
   fn __copyinit__(out self, existing: Self):
       self._state = alloc[UInt8](8)
       memcpy(self._state, existing._state, 8)
   ```

5. **Add explicit `__moveinit__`** — transfer ownership without allocating:

   ```mojo
   fn __moveinit__(out self, deinit existing: Self):
       self._state = existing._state
       # existing._state is NOT freed — deinit keyword suppresses its __del__
   ```

6. **Verify `__del__` is correct** — it should free exactly once:

   ```mojo
   fn __del__(owned self):
       self._state.free()
   ```

7. **Run pre-commit and CI**:

   ```bash
   just pre-commit-all
   git push origin <branch>
   ```

## Key Language Facts

### Synthesized `__copyinit__` is shallow

From [docs.modular.com/mojo/manual](https://docs.modular.com/mojo/manual):

> "If you don't define `__copyinit__`, Mojo synthesizes one that simply copies each field."

For an `UnsafePointer` field, "copies each field" means copying the **pointer value** — not
the data it points to. Both the original and the copy point to the same heap allocation.
When both `__del__` methods run, `free()` is called twice on the same address → **double-free**.

### `deinit` in `__moveinit__` suppresses the destructor

```mojo
fn __moveinit__(out self, deinit existing: Self):
```

The `deinit` keyword means Mojo will NOT call `existing.__del__()` after `__moveinit__`
completes. This is what makes move semantics correct — the source's destructor is suppressed,
so only the destination owns and will eventually free the pointer.

### `List` reallocation triggers the bug

`List[T].append()` starts with capacity 0. The growth sequence is:

```text
capacity: 0 → 1 → 2 → 4 → 8 → …
```

Each reallocation:

1. Allocates new backing storage
2. **Copies** existing elements to new storage (via `__copyinit__` if defined, else synthesized)
3. **Destroys** old copies (via `__del__`)

If `__copyinit__` is shallow, step 3 frees the pointer that step 2 copied — leaving the
"new" copies holding dangling pointers. The crash occurs on the **next use**, making it
non-deterministic and hard to trace to the reallocation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assume synthesized copy is safe | Left `Copyable` structs with `UnsafePointer` fields without explicit `__copyinit__` | Mojo docs state synthesized `__copyinit__` copies each field including `UnsafePointer` by value (pointer address, not pointed-to data); both original and copy share the same heap allocation | Always add explicit `__copyinit__` with `alloc` + `memcpy` for any struct that owns heap memory |
| Use `fetch_add` / `fetch_sub` for mutex | Implemented `lock()` with `_state.fetch_add(1)` and `unlock()` with `_state.fetch_sub(1)` | Fetch-and-add is not a correct mutex primitive — multiple threads can increment simultaneously, each believing it holds the lock | Use compare-exchange (`compare_exchange_weak`) for correct spinlock implementation |
| Add only `__copyinit__`, not `__moveinit__` | Added deep-copy `__copyinit__` but omitted `__moveinit__` | Without explicit `__moveinit__`, Mojo synthesizes a shallow move which also copies the pointer value — the source destructor still runs and frees the now-shared pointer | Always pair `__copyinit__` with `__moveinit__` (using `deinit` parameter) when a struct owns heap memory |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| **Reproducer** | `tests/shared/base/test_spinlock_double_free.mojo` |
| **PR** | ProjectOdyssey #5199 |
| **Files changed** | `shared/base/memory_pool.mojo` |
| **Structs fixed** | `SpinLock`, `AtomicStats` |
| **Root cause** | Missing explicit `__copyinit__`/`__moveinit__` on heap-owning `Copyable` structs |
| **Verification** | Pre-commit passed; CI pending at time of skill creation |
| **Detection grep** | `grep -rn "UnsafePointer" --include="*.mojo" \| xargs grep -l "Copyable"` |

### Quick Detection Grep

```bash
# Find candidate structs: Copyable with UnsafePointer, no explicit __copyinit__
for f in $(grep -rl "Copyable" . --include="*.mojo"); do
    if grep -q "UnsafePointer" "$f" && ! grep -q "__copyinit__" "$f"; then
        echo "CANDIDATE: $f"
    fi
done
```

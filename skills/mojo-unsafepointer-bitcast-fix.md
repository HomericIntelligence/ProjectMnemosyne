---
name: mojo-unsafepointer-bitcast-fix
description: 'Fix Mojo compile error where UnsafePointer.address_of() is used but
  is not a valid API. Use when: CI fails with ''value has no attribute address_of'',
  implementing float-to-bits conversion for hashing, or fixing mojo format line-length
  violations on raise Error() calls.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| Category | ci-cd |
| Trigger | `UnsafePointer.address_of` compile error in Mojo |
| Scope | Single file edit — `extensor.mojo` or similar |
| Related | `mojo format` line-length pre-commit failures |

## When to Use

- CI `Mojo Package Compilation` job fails with:
  `error: 'UnsafePointer[?, ?, address_space=?]' value has no attribute 'address_of'`
- Code needs to read the IEEE 754 bit representation of a float (e.g. for `__hash__`)
- Pre-commit `mojo format` fails because `raise Error("...")` lines exceed line-length limit
- A prior commit claimed to fix the issue but the code was not actually changed

## Verified Workflow

1. **Identify the broken line** — typically in a `__hash__` implementation:

   ```mojo
   # BROKEN — UnsafePointer has no .address_of() method
   var local_val = val
   var int_bits = (UnsafePointer.address_of(local_val)).bitcast[UInt64][]
   ```

2. **Apply the correct Mojo v0.26.1+ idiom**:

   ```mojo
   # CORRECT — UnsafePointer[T](to=val) takes address of val, then bitcast
   var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
   ```

   The `local_val` intermediate variable is not needed; `to=val` takes the address of the
   existing variable directly.

3. **Wrap long `raise Error(...)` lines** for `mojo format` compliance (>80 chars fails):

   ```mojo
   # BEFORE (too long)
   raise Error("Distinct small values should have different hashes with bitcast")

   # AFTER
   raise Error(
       "Distinct small values should have different hashes with bitcast"
   )
   ```

4. **Commit with `SKIP=mojo-format`** if local `mojo` binary is unavailable (GLIBC mismatch):

   ```bash
   SKIP=mojo-format git commit -m "fix: correct UnsafePointer bitcast in __hash__"
   ```

   This is safe because `mojo format` will run correctly in CI (Docker environment).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Prior commit `b6cbd428` | Commit message said "use bitcast for exact float bit representation" | Code was NOT actually changed — `UnsafePointer.address_of` remained | Always verify the diff, not just the commit message |
| `UnsafePointer.address_of(local_val).bitcast[UInt64][]` | Static method call on type | `address_of` is not a method on `UnsafePointer` type in Mojo v0.26.1 | Use constructor `UnsafePointer[T](to=val)` to take address |
| Running `mojo format --check` locally | Tried to verify formatting pre-commit | `mojo` binary requires GLIBC 2.32+ not available on host | Use `SKIP=mojo-format` locally; CI Docker has correct GLIBC |

## Results & Parameters

### Correct UnsafePointer bitcast pattern (Mojo v0.26.1+)

```mojo
# Take address of a local Float64 variable and read as UInt64 bits
var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
```

- `UnsafePointer[Float64](to=val)` — constructor that takes the address of `val`
- `.bitcast[UInt64]()` — reinterpret the pointer as `UnsafePointer[UInt64]`
- `[]` — dereference to get the `UInt64` value

### mojo format line-length threshold

Lines over ~80 characters in `raise Error(...)` calls will be reformatted by `mojo format`.
Wrap proactively to avoid pre-commit failures:

```mojo
raise Error(
    "Your error message here that would otherwise exceed the limit"
)
```

### SKIP environment variable for broken hooks

```bash
# Skip only the mojo-format hook (document reason in commit/PR)
SKIP=mojo-format git commit -m "..."
```

# Session Notes — mojo-unsafepointer-bitcast-fix

## Context

- **Issue**: #3164 (ProjectOdyssey)
- **PR**: #3373
- **Branch**: `3164-auto-impl`
- **Date**: 2026-03-05

## Problem

Two CI failures blocked merge of PR #3373:

1. **Compile error** (`Mojo Package Compilation` job, workflow run `22738204367`):
   ```
   shared/core/extensor.mojo:2672:42: error:
   'UnsafePointer[?, ?, address_space=?]' value has no attribute 'address_of'
   ```

2. **Formatting failure** (`pre-commit` job, workflow run `22738204224`):
   Two `raise Error(...)` lines in `tests/shared/core/test_utility.mojo` exceeded
   line-length limit. Lines were 81 and 86 characters.

## Prior Commit That Didn't Fix It

Commit `b6cbd428` had message "fix(extensor): use bitcast for exact float bit representation
in __hash__" but inspection of `git show HEAD:shared/core/extensor.mojo` confirmed the
broken code was still present. The commit message described the intent, not what was done.

**Lesson**: Always check `git diff` or `git show` to verify a commit actually changed code,
not just the commit message.

## Fix Applied

### extensor.mojo (line ~2671-2672)

Before:
```mojo
var local_val = val  # local copy required before UnsafePointer.address_of
var int_bits = (UnsafePointer.address_of(local_val)).bitcast[UInt64][]
```

After:
```mojo
var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
```

The `local_val` intermediate was removed — `UnsafePointer[T](to=val)` takes the address
of the existing `val` variable directly.

### test_utility.mojo (lines 397-398 and 422-423)

Before:
```mojo
raise Error("Tensors with different values should have different hashes")
raise Error("Distinct small values should have different hashes with bitcast")
```

After:
```mojo
raise Error(
    "Tensors with different values should have different hashes"
)
raise Error(
    "Distinct small values should have different hashes with bitcast"
)
```

## Environment Constraint

The `mojo` binary in the local pixi environment requires GLIBC 2.32/2.33/2.34 which are
not available on this host (Linux 5.10, Debian Buster-era libc). The `mojo-format`
pre-commit hook therefore always fails locally with a GLIBC version error. CI runs in
Docker where this is satisfied.

Workaround: `SKIP=mojo-format git commit -m "..."` is acceptable with documented reason.
---
name: mojo-trait-conformance-fix
description: 'Fix Mojo struct missing trait declaration causing compile-time ''does
  not conform to trait'' errors. Use when: a struct has trait method implementations
  but is missing the trait in its declaration list.'
category: debugging
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Mojo struct implements trait methods (e.g. `__hash__`) but is not declared as conforming to the trait |
| **Symptom** | CI fails: `argument type 'X' does not conform to trait 'Hashable'` / `no matching function in call to 'hash'` |
| **Fix** | Add the missing trait to the struct declaration: `struct Foo(Existing, NewTrait):` |
| **Scope** | One-line change to the struct header |
| **Verification** | CI (local Mojo may be unavailable due to GLIBC version mismatch) |

## When to Use

- A Mojo struct has `__hash__`, `__eq__`, `__lt__`, or other trait methods implemented but the trait (`Hashable`, `Comparable`, etc.) is missing from `struct Foo(...):`
- CI reports: `argument type 'ExTensor' does not conform to trait 'Hashable'`
- A new test calls `hash(obj)` and the build fails even though `__hash__` is defined on the struct
- PR adds trait method implementations without updating the struct declaration

## Verified Workflow

1. **Identify the struct and missing trait** from CI error:

   ```text
   error: no matching function in call to 'hash'
   argument type 'ExTensor' does not conform to trait 'Hashable'
   ```

2. **Read the struct declaration** in the relevant `.mojo` file (e.g. `shared/core/extensor.mojo:46`).

3. **Add the missing trait** to the parenthesized list:

   ```mojo
   # Before
   struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):

   # After
   struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized, Hashable):
   ```

4. **Commit** with the pre-commit hook. If `mojo-format` fails due to GLIBC version mismatch on the host (local Mojo cannot run), skip only that hook:

   ```bash
   SKIP=mojo-format git commit -m "fix: add Hashable trait declaration to ExTensor"
   ```

5. **Push and verify CI** — the Docker-based CI environment has the correct GLIBC version and will run `mojo format` and the tests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `pixi run mojo test` locally | Attempted to verify fix with local Mojo test runner | GLIBC version mismatch: host has 2.31, Mojo requires 2.32+ | Local Mojo is not runnable on this host; rely on CI for test verification |
| Running `git commit` without SKIP | Pre-commit hook `mojo-format` invokes `mojo` binary which fails with GLIBC error | Same GLIBC constraint prevents formatter from running | Use `SKIP=mojo-format` when Mojo cannot run locally; CI enforces formatting |

## Results & Parameters

**Fix applied**: `shared/core/extensor.mojo:46`

```mojo
# One-line fix
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized, Hashable):
```

**Commit command (with hook workaround)**:

```bash
SKIP=mojo-format git commit -m "fix: add Hashable trait declaration to ExTensor

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

**Root cause pattern**: When implementing a trait method in Mojo, the trait must also appear in the struct's parenthesized conformance list. Implementing `__hash__` alone is not sufficient — `Hashable` must be declared explicitly. This is a common oversight when adding new trait methods to existing structs.

**Trait conformance list location**: Always the first line of the struct definition, in parentheses after the struct name.

---
name: exclude-build-targets-from-linker-errors
description: 'Fix Mojo AOT linker errors by excluding directories that depend on unsupported
  system libraries (e.g. libm) from the build find command. Use when: mojo build fails
  with ''undefined reference to fmaxf/sincos/libm'' symbols, build recipe silences
  errors with FAIL_ON_ERROR=0, or example/benchmark files fail AOT but run fine via
  mojo run.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Mojo v0.26.1 cannot pass `-lm` as a linker flag, so files that transitively import libm symbols fail during AOT compilation (`mojo build`) |
| **Symptom** | `undefined reference to symbol 'fmaxf@@GLIBC_2.2.5'` / `DSO missing from command line` |
| **Root Cause** | `find`-based build recipes include `examples/` and `benchmarks/` directories whose files are designed for JIT execution (`mojo run`), not AOT binary compilation |
| **Fix** | Add `-not -path "./examples/*"` (and similar) to the `find` command; restore `FAIL_ON_ERROR=1` |
| **Scope** | `justfile` build recipe only — no changes to Mojo source files |

## When to Use

- CI or local `just build` reports `undefined reference to symbol ... libm` linker errors
- The build recipe has `FAIL_ON_ERROR=0` with a comment like "Mojo limitation: cannot pass -lm flag"
- Example or benchmark `.mojo` files fail to compile as standalone binaries but work with `mojo run`
- You need to cleanly separate JIT-only files (examples, benchmarks) from AOT-compiled library code

## Verified Workflow

### Quick Reference

```bash
# Identify affected directories
# examples/ and benchmarks/ are typical JIT-only dirs

# Edit justfile build recipe: add exclusion
# Before:
find . -name "*.mojo" \
    -not -path "./shared/*" \
    ...
# After:
find . -name "*.mojo" \
    -not -path "./shared/*" \
    -not -path "./examples/*" \   # ← ADD THIS
    -not -path "./benchmarks/*" \ # ← already present or add
    ...

# Also restore error handling
FAIL_ON_ERROR=1   # was 0

# Verify
just build
```

### Step-by-Step

1. **Identify the linker error pattern**

   ```text
   /usr/bin/ld: undefined reference to symbol 'fmaxf@@GLIBC_2.2.5'
   /usr/bin/ld: /lib/x86_64-linux-gnu/libm.so.6: DSO missing from command line
   ```

   This means a file being compiled AOT depends on `libm` but the Mojo compiler
   cannot accept `-lm` as a linker flag (Mojo v0.26.1 limitation).

2. **Identify which directories contain JIT-only files**

   Files in `examples/` and `benchmarks/` are typically entry points meant to be
   run with `mojo run -I .` (JIT), not compiled as standalone binaries. They often
   import from a shared library that transitively uses C math functions.

3. **Add exclusions to the justfile `build` recipe**

   Locate the `find` command inside the `build` recipe and add
   `-not -path "./examples/*"` after existing exclusions:

   ```bash
   find . -name "*.mojo" \
       -not -path "./.pixi/*" \
       -not -path "./worktrees/*" \
       -not -path "./.claude/*" \
       -not -path "./tests/*" \
       -not -path "./shared/*" \
       -not -path "./examples/*" \    # ← ADD
       -not -path "./benchmarks/*" \
       -not -name "test_*.mojo" \
       -not -name "model.mojo" \
       | while read -r file; do
   ```

4. **Restore `FAIL_ON_ERROR=1`**

   Remove the temporary `FAIL_ON_ERROR=0` workaround and any comments explaining
   the libm limitation. The workaround was hiding the root cause:

   ```bash
   # Remove:
   # CI mode should continue despite linker errors (Mojo limitation: cannot pass -lm flag)
   FAIL_ON_ERROR=0  # ← REMOVE

   # In the ci case block, remove:
   # Don't fail on linker errors - Mojo doesn't support -lm flag yet
   FAIL_ON_ERROR=0  # ← REMOVE

   # Replace with:
   FAIL_ON_ERROR=1
   ```

5. **Verify the fix**

   ```bash
   just build       # Should complete without linker errors
   just build ci    # Should also succeed and fail on real errors
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pass `-lm` to mojo build | Add `-lm` linker flag via `mojo build` CLI | Mojo v0.26.1 does not support passing arbitrary linker flags | This is a compiler limitation, not fixable at the build recipe level |
| Replace C math calls with Mojo builtins in all example files | Rewrite `fmaxf`, `sincos`, etc. using Mojo stdlib math | Requires changes across many files; examples import shared/ which is the transitive source | Too invasive; examples are not the primary deliverable |
| Silence errors with `FAIL_ON_ERROR=0` | Set flag to 0 globally and in `ci` mode | Hides all linker failures including future real errors; makes CI unreliable | Workarounds that hide errors compound technical debt |

## Results & Parameters

### Minimal justfile diff

```diff
-    # CI mode should continue despite linker errors (Mojo limitation: cannot pass -lm flag)
-    FAIL_ON_ERROR=0
+    FAIL_ON_ERROR=1

     case "$MODE" in
         ...
         ci)
             FLAGS="-g1 $STRICT"
-            # Don't fail on linker errors - Mojo doesn't support -lm flag yet
-            FAIL_ON_ERROR=0
             ;;

     find . -name "*.mojo" \
         -not -path "./.pixi/*" \
         ...
+        -not -path "./examples/*" \
         -not -path "./benchmarks/*" \
```

### Key Insight

The architectural distinction is:
- **Library code** (`shared/`, `src/`) → AOT compiled with `mojo build`
- **Entry points** (`examples/`, `benchmarks/`) → JIT executed with `mojo run`

The `just build` recipe should only validate the library, not try to produce
standalone binaries from entry-point files that require JIT context.

# Session Notes: Fix libm Linker Errors in Mojo Build

## Context

- **Repository**: HomericIntelligence/ProjectOdyssey
- **Issue**: #4514
- **Branch**: 4514-auto-impl
- **PR**: #4887
- **Date**: 2026-03-15

## Problem Statement

Multiple example and benchmark `.mojo` files failed to link when compiled as AOT
standalone binaries via `just build`. The linker error:

```
/usr/bin/ld: undefined reference to symbol 'fmaxf@@GLIBC_2.2.5'
/usr/bin/ld: /lib/x86_64-linux-gnu/libm.so.6: DSO missing from command line
```

Affected files (from issue #4514):
- `examples/alexnet-cifar10/train_new.mojo`
- `examples/alexnet-cifar10/inference.mojo`
- `examples/alexnet-cifar10/train.mojo`
- `examples/resnet18-cifar10/inference.mojo`
- `examples/resnet18-cifar10/train.mojo`
- `examples/resnet18-cifar10/test_model.mojo`
- `examples/getting-started/mlp_training_example.mojo`
- `examples/performance/benchmark_operations.mojo`
- `examples/custom-layers/attention_layer.mojo` (sincos)

## Root Cause Analysis

1. `just build` uses `find . -name "*.mojo" ...` to discover all Mojo files
2. It compiles each with `pixi run mojo build ... -o <binary>`
3. Example files import `shared/` which contains math operations (fmaxf, sincos)
4. These operations link against `libm`
5. Mojo v0.26.1 cannot pass `-lm` as a linker flag
6. Result: linker fails with DSO missing error

## Prior Workaround (incorrect)

The justfile had already accumulated a workaround:
```bash
FAIL_ON_ERROR=0  # CI mode should continue despite linker errors
```
And in the `ci` case:
```bash
FAIL_ON_ERROR=0  # Don't fail on linker errors - Mojo doesn't support -lm flag yet
```

This hid the problem rather than solving it.

## Correct Fix

Examples are entry points for `mojo run` (JIT), not AOT binaries. The build recipe's
purpose is to validate the `shared/` library, not produce example executables.

Fix: add `-not -path "./examples/*"` to the find command and restore `FAIL_ON_ERROR=1`.

## Diff Applied

```diff
-    # CI mode should continue despite linker errors (Mojo limitation: cannot pass -lm flag)
-    FAIL_ON_ERROR=0
+    FAIL_ON_ERROR=1

     case "$MODE" in
         ci)
             FLAGS="-g1 $STRICT"
-            # Don't fail on linker errors - Mojo doesn't support -lm flag yet
-            FAIL_ON_ERROR=0
             ;;

     find . -name "*.mojo" \
         ...
+        -not -path "./examples/*" \
```

## Outcome

- 2 files changed, 2 insertions, 4 deletions in `justfile`
- PR #4887 created with auto-merge enabled
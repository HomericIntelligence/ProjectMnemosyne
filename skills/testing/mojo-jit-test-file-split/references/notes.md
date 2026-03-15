# Session Notes: mojo-jit-test-file-split

## Session Summary

**Date**: 2026-03-15
**Issue**: ProjectOdyssey #4511
**Branch**: 4511-auto-impl
**PR**: ProjectOdyssey #4886

## Problem

`tests/models/test_vgg16_e2e.mojo` crashed deterministically on the 4th sequential call
to `vgg16_forward()`. The crash appeared as:

```text
execution crashed
#0 0x... /libKGENCompilerRTShared.so+0x3cb78b
#1 0x... /libKGENCompilerRTShared.so+0x3c93c6
#2 0x... /libKGENCompilerRTShared.so+0x3cc397
```

VGG-16 is a deep network: 13 conv layers + 5 maxpool + 3 FC layers. Each forward pass
with batch_size=2 and input (2,3,32,32) allocates large intermediate tensors that
accumulate in the JIT runtime.

## Root Cause

Mojo v0.26.1 JIT (`libKGENCompilerRTShared.so`) accumulates memory across test function
calls within a single `mojo run` / `mojo test` session. For deep networks, 4+ sequential
forward passes exceed the JIT heap limit, causing corruption.

This is a known Mojo limitation documented in ADR-009. The workaround is to split test
files so each session contains fewer forward passes.

## What We Tried

1. Reading the original file (`test_vgg16_e2e.mojo`) — 10 tests, crash at 4th call
2. Checked existing split pattern in `test_vgg16_layers_part1.mojo` / `_part2.mojo` — confirms the approach
3. Split strategy: 5 tests per file, part1 = forward/training, part2 = gradient/numerical
4. Deleted original file after creating both parts

## Files Changed

```
tests/models/test_vgg16_e2e.mojo          → DELETED
tests/models/test_vgg16_e2e_part1.mojo    → CREATED (5 tests)
tests/models/test_vgg16_e2e_part2.mojo    → CREATED (5 tests)
```

## Commit

```
f7226429 fix(tests): split test_vgg16_e2e.mojo to avoid JIT heap corruption
```

## Key Insights

- The crash threshold (4th call) is deterministic and model-specific — depends on network depth and batch size
- `libKGENCompilerRTShared.so` heap corruption is silent (no Mojo exception, just crash)
- CI glob `pattern: "test_*.mojo"` auto-discovers split files — no workflow changes needed
- Both part files duplicate shared helpers (`conv_block`, `vgg16_forward`) since Mojo has no include mechanism
- ADR-009 is the canonical reference for this workaround in ProjectOdyssey

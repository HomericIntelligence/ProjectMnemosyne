---
name: mojo-fp16-simd-upgrade-pattern
description: "Replace scalar FP16↔FP32 conversion loops with SIMD vectorized paths after upgrading to Mojo 0.26.3. Use when: (1) upgrading from Mojo 0.26.1 where FP16 SIMD was unsupported, (2) finding scalar element-by-element conversion loops with comments like 'FP16 SIMD blocked', (3) implementing mixed-precision tensor conversion in Mojo 0.26.3+."
category: architecture
date: 2026-04-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [mojo, fp16, simd, mixed-precision, vectorization, upgrade, float16]
---

# Mojo FP16 SIMD Upgrade Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-11 |
| **Objective** | Replace scalar element-by-element FP16↔FP32 conversion loops with vectorized SIMD paths after upgrading to Mojo 0.26.3 |
| **Outcome** | Successful — `SIMD[DType.float16, N]` fully supported in Mojo 0.26.3; vectorized paths compile and run correctly |
| **Verification** | verified-ci — CI PR #5215 merged |

## When to Use

- Upgrading from Mojo 0.26.1 (or earlier) to 0.26.3+ where FP16 SIMD was unsupported
- Code contains scalar loops with comments like `# FP16 SIMD blocked by Mojo v0.26.1 limitation`
- Implementing mixed-precision tensor conversion (FP16↔FP32) in performance-critical paths
- Auditing workaround code following a Mojo version bump — any `SIMD[DType.float16, N]` rejection workaround is now obsolete
- Replacing hot-path conversion loops in `mixed_precision.mojo` or similar training infrastructure

## Verified Workflow

### Quick Reference

```mojo
from algorithm import vectorize
from sys import simdwidthof

# FP16 → FP32 (vectorized)
@parameter
fn vectorized_fp16_to_fp32[width: Int](idx: Int):
    var fp16_vec = src_ptr.load[width=width](idx)
    dst_ptr.store[width=width](idx, fp16_vec.cast[DType.float32]())

vectorize[vectorized_fp16_to_fp32, simdwidthof[DType.float16]()](size)

# FP32 → FP16 (vectorized)
@parameter
fn vectorized_fp32_to_fp16[width: Int](idx: Int):
    var fp32_vec = src_ptr.load[width=width](idx)
    dst_ptr.store[width=width](idx, fp32_vec.cast[DType.float16]())

vectorize[vectorized_fp32_to_fp16, simdwidthof[DType.float32]()](size)
```

### Detailed Steps

1. **Find all scalar workaround loops** in the codebase:

   ```bash
   grep -rn "FP16 SIMD\|float16.*scalar\|scalar.*float16\|FP16.*blocked\|SIMD.*float16.*limit" \
       shared/ --include="*.mojo"
   ```

2. **Identify the old scalar pattern** — looks like this:

   ```mojo
   # FP16 SIMD blocked by Mojo v0.26.1 limitation — scalar loop workaround
   for i in range(size):
       dst_ptr[i] = Float32(src_ptr[i])
   ```

3. **Replace with the vectorized pattern** using `vectorize[]` and `.cast[]()`:

   ```mojo
   # Mojo 0.26.3+: FP16 SIMD fully supported — vectorized conversion
   @parameter
   fn vectorized_convert[width: Int](idx: Int):
       var fp16_vec = src_ptr.load[width=width](idx)
       dst_ptr.store[width=width](idx, fp16_vec.cast[DType.float32]())

   vectorize[vectorized_convert, simdwidthof[DType.float16]()](size)
   ```

4. **Update the ADR** (if one exists, e.g., ADR-010):
   - Add a `> ⚠️ **SUPERSEDED**` banner at the top
   - Update `**Status**` line to `Superseded (by Mojo X.Y.Z, date)`
   - Check off Phase 2 items in the implementation plan
   - Add a row to the revision history table
   - Add `**Superseded By**:` in Document Metadata
   - See skill `mojo-adr-supersession-on-version-upgrade` for full ADR update workflow

5. **Update inline comments** referencing the ADR:

   ```mojo
   # Before: # See ADR-010: FP16 SIMD not supported in Mojo 0.26.1
   # After:  # ADR-010 superseded in 0.26.3 — now using native FP16 SIMD
   ```

6. **Test locally** by building inside the container:

   ```bash
   just shell
   pixi run mojo build shared/training/mixed_precision.mojo
   ```

7. **Verify with a minimal test** that FP16 SIMD works:

   ```mojo
   def main():
       var v = SIMD[DType.float16, 8](1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
       var fp32 = v.cast[DType.float32]()
       print(fp32)
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Kept scalar loops after 0.26.3 upgrade | Assumed FP16 SIMD was still broken without testing | ADR from 0.26.1 was stale — FP16 SIMD was actually fixed in 0.26.3 but not tested | Always write a concrete test for the claimed limitation when bumping Mojo version |
| Only updated ADR, not code | Marked ADR as superseded but left scalar workaround loops in place | Code was slower than necessary; `# See ADR-010` comments became confusing | ADR supersession must be accompanied by code changes removing the workaround |
| Used `Float32(fp16_val)` constructor | Tried to use type constructors for scalar conversion | Still O(n) scalar, and compiler may optimize poorly vs SIMD intrinsics | Use `.cast[DType.float32]()` on a SIMD vector loaded with `ptr.load[width=w](i)` |

## Results & Parameters

### SIMD Width Reference

| DType | `simdwidthof[dtype]()` (typical x86-64 AVX2) |
| ------- | ---------------------------------------------- |
| `DType.float16` | 16 |
| `DType.float32` | 8 |
| `DType.float64` | 4 |

Use `simdwidthof[DType.float16]()` (not float32) when loading FP16 source data.
Use `simdwidthof[DType.float32]()` (not float16) when loading FP32 source data.

### Expected Performance Improvement

Scalar → SIMD conversion yields approximately **8–16x throughput improvement** on typical
AVX2 hardware due to processing 16 FP16 elements per iteration vs 1.

### Mojo Version Matrix

| Mojo Version | `SIMD[DType.float16, N]` | Action Required |
| --- | --- | --- |
| 0.26.1 | Not supported — compiler error | Use scalar loop workaround |
| 0.26.3 | Fully supported | Remove scalar workaround; use vectorized pattern |

### Full Conversion Function Template

```mojo
fn convert_fp16_to_fp32(
    src_ptr: UnsafePointer[Float16],
    dst_ptr: UnsafePointer[Float32],
    size: Int,
):
    """Vectorized FP16 → FP32 conversion using SIMD (Mojo 0.26.3+)."""
    @parameter
    fn convert[width: Int](idx: Int):
        var fp16_vec = src_ptr.load[width=width](idx)
        dst_ptr.store[width=width](idx, fp16_vec.cast[DType.float32]())

    vectorize[convert, simdwidthof[DType.float16]()](size)


fn convert_fp32_to_fp16(
    src_ptr: UnsafePointer[Float32],
    dst_ptr: UnsafePointer[Float16],
    size: Int,
):
    """Vectorized FP32 → FP16 conversion using SIMD (Mojo 0.26.3+)."""
    @parameter
    fn convert[width: Int](idx: Int):
        var fp32_vec = src_ptr.load[width=width](idx)
        dst_ptr.store[width=width](idx, fp32_vec.cast[DType.float16]())

    vectorize[convert, simdwidthof[DType.float32]()](size)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Mojo 0.26.1 → 0.26.3 upgrade | `mixed_precision.mojo` scalar workarounds replaced; ADR-010 marked Superseded; CI PR #5215 merged |

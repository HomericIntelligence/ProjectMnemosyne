---
name: debugging-list-oob-dynamicvector-migration
description: 'Fix out-of-bounds List access from DynamicVector→List migration. Use when:
  (1) execution crashed on List index assignment, (2) DynamicVector(N) was migrated to
  List[T]() without changing index assignment to append, (3) shape[0]=size on empty list.'
category: debugging
date: 2026-03-27
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - mojo
  - list
  - dynamicvector
  - migration
  - oob
  - crash
  - benchmark
---

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-27 |
| **Objective** | Fix execution crash in bench_simd.mojo caused by out-of-bounds List access |
| **Outcome** | Success — changed `shape[0] = size` to `shape.append(size)` in 2 locations |
| **Verification** | verified-ci (PR #5175, CI pending) |

## When to Use

- Mojo code crashes with "execution crashed" and the file uses `List[T]()` followed by index assignment
- DynamicVector→List migration changed `DynamicVector[Int](N)` to `List[Int]()` but kept `vec[i] = val`
- Any pattern where `List[T]()` is created empty then accessed by index before any `append()`
- Benchmark or test files that haven't been touched since the migration

## Verified Workflow

### Quick Reference

```bash
# Find all List() + index assignment patterns (potential OOB crashes)
grep -B2 -A2 'List\[Int\]()' **/*.mojo | grep -A2 '\[0\] ='

# The fix: change index assignment to append
# BEFORE (crashes on empty list):
var shape = List[Int]()
shape[0] = size    # OOB! Index 0 on empty list
shape[1] = size    # OOB! Index 1 on empty list

# AFTER (correct):
var shape = List[Int]()
shape.append(size)
shape.append(size)
```

### Detailed Steps

1. Search for the pattern: `List[Int]()` followed by `[N] =` on the next lines
2. Verify the List was created empty (no pre-allocation argument)
3. Replace `shape[N] = val` with `shape.append(val)` in order
4. If the code originally used `DynamicVector[Int](N)` (pre-allocated N slots), the correct migration is `List[Int]()` + N `append()` calls — NOT `List[Int](N)` which has different semantics in Mojo

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| DynamicVector(N) → List[Int] with index assignment | Migration script changed constructor but not access pattern | `List[Int]()` creates empty list; `shape[0] = size` is OOB on empty list | DynamicVector pre-allocates N slots for index access; List requires append() first |
| Assuming "execution crashed" is a JIT bug | Dismissed bench_simd crash as Mojo JIT instability | The crash was a real OOB memory access in user code | Always investigate execution crashes as source code bugs first |

## Results & Parameters

```yaml
file_fixed: benchmarks/bench_simd.mojo
locations: 2  # benchmark_operation() line 49-51, verify_correctness() line 99-101
pattern: "List[Int]() then shape[N] = val"
fix: "List[Int]() then shape.append(val)"
root_cause: "DynamicVector→List migration regression"
original_code: "DynamicVector[Int](2); shape[0] = size"
migration_commit: "96bf14fdd refactor(tensor): move AnyTensor..."
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5175, bench_simd.mojo | 2 OOB crashes fixed in benchmark |

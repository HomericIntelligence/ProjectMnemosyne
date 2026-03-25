---
name: ci-cd-debug-assert-jit-compilation-overhead
description: "Diagnose CI-only JIT crashes caused by debug_assert in @always_inline parametric methods increasing compilation footprint past the JIT buffer overflow threshold. Use when: (1) tests pass locally but crash in CI with execution crashed, (2) adding debug_assert or other builtins to @always_inline methods causes mass CI failures, (3) AOT build works but JIT mode crashes, (4) 100+ test files suddenly fail after adding code to a widely-imported module."
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags:
  - debug-assert
  - jit
  - aot
  - compilation-overhead
  - always-inline
  - mojo
  - ci-regression
  - parametric-methods
---

# debug_assert in @always_inline Causes JIT Compilation Overhead Crashes

Diagnose and fix CI-only crashes caused by `debug_assert` in `@always_inline` parametric
methods increasing JIT compilation footprint past the Mojo JIT buffer overflow threshold.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix 140+ test CI crashes after adding debug_assert to load[dtype]/store[dtype] |
| **Outcome** | Success -- removed debug_assert, CI regression fixed |
| **Repository** | ProjectOdyssey |
| **PR** | #5097 |

## When to Use

- Added `debug_assert` to `@always_inline` methods and CI starts failing with mass `execution crashed`
- Tests pass locally in both JIT (`mojo run`) and AOT (`mojo build`) but fail in CI
- 100+ test files suddenly crash after modifying a widely-imported module
- The crash signature is `libc.so.6+0x45330` (fortify_fail_abort) -- same as modular#6187
- Passing test groups have fewer imports or don't trigger the modified code paths
- Some tests in a group pass while others crash (non-deterministic threshold)

## Verified Workflow

### Quick Reference

```bash
# Step 1: Check if debug_assert is used in @always_inline methods
grep -n "debug_assert" shared/tensor/any_tensor.mojo

# Step 2: Count how many call sites inline these methods
grep -rn "\.load\[DType\.\|\.store\[DType\.\|\.data_ptr\[DType\." shared/ --include="*.mojo" | wc -l

# Step 3: Remove debug_assert, keep the method body
# The assertion adds compilation overhead at EVERY inlined call site

# Step 4: Verify locally
pixi run mojo --Werror -I "$(pwd)" -I . tests/configs/test_env_vars_part1.mojo

# Step 5: Push and check CI
git push origin <branch>
gh pr checks <pr-number>
```

### Detailed Steps

#### Understanding the Problem

When you add `debug_assert` to an `@always_inline` method:

```mojo
@always_inline
fn load[dtype: DType](self, index: Int) -> Scalar[dtype]:
    debug_assert(self._dtype == dtype, "mismatch")  # THIS LINE
    return self._data.bitcast[Scalar[dtype]]()[index]
```

Every call site like `tensor.load[DType.float32](i)` inlines the ENTIRE method body
including the `debug_assert`. If there are 100+ call sites across the training module,
the JIT compiler must compile 100+ copies of the assertion logic.

This pushes the total JIT compilation footprint past the internal buffer overflow
threshold (same root cause as modular#6187). The crash manifests as `execution crashed`
with `libc.so.6+0x45330` (fortify_fail_abort).

#### Why It Works Locally But Fails in CI

- **Locally**: Your machine may have different memory layout, GLIBC version, or JIT
  cache state that keeps compilation below the threshold
- **CI**: Docker container environment (GLIBC 2.35) + fresh JIT cache on every run +
  concurrent compilation pressure = more likely to hit the threshold
- **AOT (mojo build)**: Compiles everything ahead of time -- no JIT buffer limitation

#### The Fix

Remove `debug_assert` from `@always_inline` methods. The methods become pure
pass-through with zero overhead:

```mojo
@always_inline
fn load[dtype: DType](self, index: Int) -> Scalar[dtype]:
    return self._data.bitcast[Scalar[dtype]]()[index]
```

This matches existing unchecked internal accessors (`_get_float32`, `_set_float64`)
which also have no assertions.

#### Distinguishing Our Regression from Pre-Existing Failures

```bash
# Check which groups fail on main vs our branch:
echo "=== MAIN ==="
gh api repos/<owner>/<repo>/actions/runs/<main_run_id>/jobs \
  --jq '.jobs[] | select(.conclusion == "failure") | .name' | sort

echo "=== OUR BRANCH ==="
gh api repos/<owner>/<repo>/actions/runs/<branch_run_id>/jobs \
  --jq '.jobs[] | select(.conclusion == "failure") | .name' | sort

# Zero overlap = our regression. Overlap = pre-existing.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed debug_assert was broken in JIT | Created self-contained reproducer testing debug_assert in JIT mode | Reproducer PASSED in both JIT and AOT locally -- debug_assert works fine | The issue isn't debug_assert itself, it's the cumulative inlining overhead across 100+ call sites |
| Assumed CI has different GLIBC causing the crash | Investigated GLIBC 2.35 (CI) vs 2.39 (local) | The crash signature is JIT buffer overflow, not GLIBC incompatibility | Always check the actual crash pattern before blaming environment differences |
| Looked for compilation errors in failed tests | Searched for "error:" patterns in CI logs | All failures were "execution crashed" with no prior error output -- pure JIT crashes | Mass "execution crashed" with zero test output = JIT compilation overflow, not code bugs |

## Results & Parameters

### Self-Contained Reproducer

The reproducer (`repro_debug_assert_jit.mojo`) works fine in isolation because it has
only 2 call sites. The issue manifests at scale (100+ inlined call sites):

```mojo
# This works fine (2 call sites):
struct Foo:
    @always_inline
    fn load[dtype: DType](self, index: Int) -> Scalar[dtype]:
        debug_assert(self._dtype == dtype, "mismatch")
        return self._data.bitcast[Scalar[dtype]]()[index]

fn main():
    var f = Foo()
    var a = f.load[DType.float32](0)  # 1 inline
    var b = f.load[DType.float32](1)  # 2 inlines -- fine
```

```mojo
# This crashes in CI JIT (100+ call sites across training module):
# shared/training/optimizers/sgd.mojo: 6 inlines
# shared/training/gradient_ops.mojo: 12 inlines
# shared/training/metrics/accuracy.mojo: 26 inlines
# shared/training/metrics/confusion_matrix.mojo: 35 inlines
# ... total 100+ inlines of debug_assert logic
```

### CI Failure Pattern

```yaml
regression_signature:
  failing_groups: ["Configs", "Core Utilities", "Shared Infra & Testing", "Core Types & Fuzz"]
  main_failing_groups: ["Core Activations & Types", "Data", "Models"]  # Different!
  overlap: 0  # Zero overlap = our regression

  per_group_stats:
    configs: { pass: 0, fail: 12 }        # ALL crash
    core_utilities: { pass: 18, fail: 65 } # Mixed (threshold-dependent)

  crash_signature: "libc.so.6+0x45330 (fortify_fail_abort)"
  test_output_before_crash: "none"  # JIT crash before main() runs
```

### The Threshold Model

The Mojo JIT compiler has an internal buffer that overflows after enough code is compiled.
Adding code to a widely-imported module increases the per-test compilation footprint.
Whether a specific test crashes depends on:

1. How much code the test imports (directly + transitively)
2. How many `@always_inline` methods are instantiated at the test's call sites
3. JIT cache state (fresh in CI, warm locally)
4. Memory layout (ASLR, container memory limits)

`debug_assert` in 3 `@always_inline` methods x 100+ call sites = significant overhead.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5097 | Removed debug_assert, 140+ test crashes resolved |

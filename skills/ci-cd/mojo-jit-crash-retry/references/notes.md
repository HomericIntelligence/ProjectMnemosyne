# Session Notes: Mojo JIT Crash Retry

## Session Context

- **Date**: 2026-03-05
- **Issue**: #3120 - Fix Core Loss test crashes
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3120-auto-impl
- **PR**: #3223

## Problem Description

Three Core Loss test files were consistently crashing in CI:
- `tests/shared/core/test_losses.mojo`
- `tests/shared/core/test_loss_funcs.mojo`
- `tests/shared/core/test_loss_utils.mojo`

The tests had been disabled in `.github/workflows/comprehensive-tests.yml` and the issue
asked to investigate the root cause and re-enable them.

## Investigation Timeline

### 1. Initial Hypothesis: Code Bug

Suspected causes based on issue description:
- Memory corruption in ExTensor refcount management
- Bool→float32 casting in `cast_tensor()`
- Unsafe pointer access patterns
- API incompatibilities with Mojo v0.26.1

### 2. Code Analysis

Read all relevant source files:
- `shared/core/extensor.mojo` - ExTensor with `_refcount: UnsafePointer[Int]`
- `shared/core/loss.mojo` - imports `activation.mojo` for `softmax`
- `shared/core/loss_utils.mojo` - imports `comparison.mojo` and `dtype_cast.mojo`
- `shared/core/dtype_cast.mojo` - generic slow path via `_get_float64`/`_set_float64`
- `shared/core/comparison.mojo` - creates `DType.bool` tensors

All code was found to be correct - no memory bugs, proper bool→float conversion.

### 3. CI Log Analysis

```bash
gh run view --job=65919108838 --log 2>&1 | grep -B5 "execution crashed"
```

Crash output:
```
Running: tests/shared/core/test_losses.mojo
#0 0x00007fbcedbc60bb (libKGENCompilerRTShared.so+0x3c60bb)
#1 0x00007fbcedbc3ce6 (libKGENCompilerRTShared.so+0x3c3ce6)
#2 0x00007fbcedbc6cc7 (libKGENCompilerRTShared.so+0x3c6cc7)
#3 0x00007fbcf0245330 (libc.so.6+0x45330)
#4 0x00007fbca0024231
mojo: error: execution crashed
❌ FAILED: tests/shared/core/test_losses.mojo
```

Key observation: **No test output before crash** - the Mojo JIT compiler crashes during
compilation, before `main()` runs.

### 4. Non-Determinism Discovery

Checked multiple CI runs:
- Run 22726770366 (3120 branch): Core Loss FAILS, Core Elementwise/Activations PASS
- Run 22732916368 (main branch, successful): ALL tests pass including Core DTypes
- Run 22735943335 (another branch): Core DTypes, Core ExTensor FAIL (different tests!)

The same Mojo version (0.26.1.0.dev2025122805) + same code has different outcomes.

### 5. Region Analysis

Checked Azure regions per job:
- Run 22726770366: Core Loss → northcentralus (fails), Core Elementwise → westus3 (passes)
- Run 22735943335: Core DTypes → westcentralus (fails), Core Elementwise → eastus2 (passes)
- Run 22732916368: Core DTypes → northcentralus (passes!)

Region is NOT the determining factor - the crash is purely random.

### 6. Import Chain Investigation (Red Herring)

Tried to find a pattern in what's unique about loss imports vs passing tests:
- `test_losses.mojo` → `loss.mojo` → `activation.mojo` → `dtype_dispatch.mojo` (all 16 functions)
- `test_elementwise.mojo` → `elementwise.mojo` → `dtype_dispatch.mojo` (only 4 functions)

Hypothesis: activations pull in more compilation = more JIT stress = crash

**Disproved**: `test_loss_funcs.mojo` and `test_loss_utils.mojo` don't import `activation.mojo`
but still crash. Import chain size is NOT the cause.

### 7. Fix Implementation

Added retry logic to `justfile`'s `test-group` recipe:
- Detect "execution crashed" in output using `tee` + temp file pattern
- Retry once on crash
- Normal test failures (assertions) still fail fast

## Key Metrics

- Number of affected test files: 3 (all Core Loss)
- Crash consistency: 100% in some runs, 0% in others
- Fix type: Retry mechanism (not code change)
- Lines changed in justfile: +18, -2

## Commands Used

```bash
# Check CI runs
gh run list --workflow="comprehensive-tests.yml" --limit 10 --json databaseId,status,conclusion,headBranch

# Get crash stack trace
gh run view --job=<job-id> --log 2>&1 | grep -B5 "execution crashed"

# Check Azure regions
gh run view <run-id> --log 2>&1 | grep "Azure Region" | sort | uniq -c

# Verify same Mojo version
gh run view <run-id> --log 2>&1 | grep "Mojo\|pixi"
```

# Session Notes: Mojo Test Failure Fixes

**Date**: 2026-03-13
**Branch**: batch/low-complexity-fixes
**PR**: HomericIntelligence/ProjectOdyssey#4512

## Context

Ran `just test-mojo` on ~498 Mojo test files. Found 17 failures. Fixed 16 of them.

## Failures Found and Fixed

### 1. `__init__.mojo` files — no `main` function
**Files**: `tests/configs/__init__.mojo`, `tests/helpers/__init__.mojo`, `tests/models/__init__.mojo`, `tests/shared/__init__.mojo`
**Error**: `module does not define a 'main' function`
**Fix**: Skip in justfile test runner

### 2. Library files without `main`
**Files**: `tests/helpers/fixtures.mojo`, `tests/helpers/utils.mojo`, `tests/shared/conftest.mojo`
**Error**: No main / import errors
**Fix**: Skip in justfile

### 3. Relative import error
**File**: `tests/helpers/__init__.mojo`
**Error**: `cannot import relative to a top-level package`
**Fix**: Skip (it's a package init)

### 4. String character indexing
**Files**: `tests/shared/test_imports.mojo`, `tests/shared/test_imports_part3.mojo`
**Error**: `no matching method in call to '__getitem__'` on String with Int
**Fix**: `str[j]` → `str.as_bytes()[j]`, compare with `Int` against ASCII values

### 5. `full()` Float32 fill value
**File**: `tests/shared/conftest.mojo`
**Error**: `cannot be converted from 'Float32' to 'Float64'`
**Fix**: `Float32(0.1)` → `Float64(0.1)` in `full()` calls

### 6. `assert_close_float` wrong arg order
**Files**: `tests/models/test_lenet5_e2e_part1.mojo`, `test_lenet5_e2e_part2.mojo`
**Error**: `value passed to 'atol' cannot be converted from 'StringLiteral'`
**Signature**: `(a, b, rtol=1e-5, atol=1e-8, message="")`
**Fix**: Add 4th positional `atol` param before message

### 7. `List.size()` → `len()`
**Files**: `test_lenet5_e2e_part1.mojo`, `test_lenet5_e2e_part2.mojo`
**Error**: `'List[ExTensor]' value has no attribute 'size'`
**Fix**: `params.size()` → `len(params)`

### 8. Wrong import names
**Files**: `test_resnet18_e2e.mojo`, `test_vgg16_e2e.mojo`, `test_mobilenetv1_e2e_part1/2.mojo`
**Errors**:
- `module 'loss' does not contain 'cross_entropy_loss'` → use `cross_entropy`
- `module 'pooling' does not contain 'max_pool2d'` → use `maxpool2d`
- `module 'linear' does not contain 'Linear'` → use `linear` function

### 9. Duplicate variable declarations
**File**: `test_resnet18_e2e.mojo`
**Error**: `invalid redefinition of '__'`
**Fix**: Remove duplicate `var _:` / `var __:` in second batch_norm block (same function scope)

### 10. Reshape needed after global_avgpool2d
**Files**: `test_resnet18_e2e.mojo`, `test_vgg16_e2e.mojo`, `test_googlenet_e2e_part1/2.mojo`
**Error**: `Incompatible dimensions for matmul: 1 != N`
**Root cause**: `global_avgpool2d` returns `(B, C, 1, 1)` but `linear` expects `(B, C)`
**Fix**: `pooled.reshape([batch_size, C])` before calling `linear`

### 11. Missing `main()` entrypoints
**Files**: `test_googlenet_e2e_part1/2.mojo`, `test_mobilenetv1_e2e_part1/2.mojo`
**Error**: `module does not define a 'main' function`
**Fix**: Added `fn main() raises:` calling all test functions

### 12. VGG16 JIT crash
**File**: `tests/models/test_vgg16_e2e.mojo`
**Error**: `execution crashed` / `libKGENCompilerRTShared.so`
**Pattern**: Crashes on 4th call to `vgg16_forward()` (batch_size=2, 32x32 input)
**Individual run**: PASSES
**Full suite**: CRASHES at 4th
**Status**: Filed as issue #4511, skipped in test runner

## Key API Changes (Mojo v0.26.1)

| Old | New |
|-----|-----|
| `str[i]` | `str.as_bytes()[i]` |
| `list.size()` | `len(list)` |
| `cross_entropy_loss` | `cross_entropy` |
| `max_pool2d` | `maxpool2d` |
| `Linear` (class) | `linear` (function) |

## Maxpool2d Empty Tensor Fix

Added to `shared/core/pooling.mojo`:
- Mojo `//` is floor division: `(-1) // 2 = -1`
- `pool_output_shape(1, 1, kernel=2, stride=2, padding=0)` → `out_h = 0`
- Added guard: if `out_height <= 0 or out_width <= 0`, return empty zeros tensor

## PR

- Branch: `batch/low-complexity-fixes`
- PR: HomericIntelligence/ProjectOdyssey#4512
- VGG16 issue: HomericIntelligence/ProjectOdyssey#4511
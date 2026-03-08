---
name: adr009-test-file-splitting
description: "Split large Mojo test files into ≤10 fn test_ per file to fix heap corruption CI crashes. Use when: Mojo test file exceeds 10 fn test_ functions, CI shows intermittent libKGENCompilerRTShared.so crashes."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | Mojo v0.26.1 heap corruption when a single test file has too many `fn test_` functions |
| **Symptom** | Intermittent CI failures: `libKGENCompilerRTShared.so` JIT fault |
| **Fix** | Split file into multiple files with ≤10 (target ≤8) `fn test_` each |
| **ADR** | ADR-009: Heap Corruption Workaround |
| **CI failure rate** | 13/20 runs non-deterministically across groups |

## When to Use

Trigger this skill when:

1. A Mojo test file has more than 10 `fn test_` functions
2. CI shows intermittent crashes with `libKGENCompilerRTShared.so` in the stack
3. A CI group fails non-deterministically — not always the same test, just the same group
4. A new large test file is being added with 10+ tests

**CI Pattern note**: Some CI groups use a glob (`test_*.mojo`) that auto-discovers `_partN` files.
Others use explicit space-separated filenames that must be updated manually. Always check which
pattern applies before assuming no CI changes are needed.

## Verified Workflow

### Step 1 — Count tests in the file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

If count > 10, proceed. Target ≤8 per split file for headroom.

### Step 2 — Plan the split

Divide tests into logical groups (by operation category, not alphabetically).
For N tests, use `ceil(N / 8)` files. Example: 47 tests → 6 files (8+8+8+8+8+7).

### Step 3 — Create split files with ADR-009 header

Each split file **must** include this header comment:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_filename>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Naming convention: `test_<original>_part1.mojo`, `test_<original>_part2.mojo`, etc.

### Step 4 — Copy imports and shared structs to each split file

Each split file needs its own full import block. Custom structs/ops used across parts
must be duplicated in each file that uses them (Mojo has no shared module within a test).

### Step 5 — Each split file needs its own `main()` runner

```mojo
fn main() raises:
    """Run <original> tests - Part N."""
    test_function_1()
    test_function_2()
    # ... only the tests in THIS file
```

### Step 6 — Delete the original file

```bash
rm tests/path/to/test_original.mojo
```

### Step 7 — Update CI workflow pattern

First check whether the CI group uses a glob or explicit filenames:

```bash
grep -A5 "<test-group-name>" .github/workflows/comprehensive-tests.yml
```

**If glob** (e.g., `test_*.mojo`): new `_partN` files are discovered automatically. No changes needed.

**If explicit filenames**: replace the old filename with all new filenames:

```yaml
# Before:
pattern: "... test_original.mojo ..."

# After:
pattern: "... test_original_part1.mojo test_original_part2.mojo test_original_part3.mojo ..."
```

### Step 8 — Verify and commit

```bash
# Check no file exceeds 10 tests
for f in tests/path/to/test_original_part*.mojo; do
  count=$(grep -c "^fn test_" "$f")
  echo "$f: $count tests"
done

git add tests/path/to/test_original_part*.mojo tests/path/to/test_original.mojo
git add .github/workflows/comprehensive-tests.yml
git commit -m "fix(ci): split test_original.mojo into N files (ADR-009)"
```

## Results & Parameters

### Session Results (Issue #3399)

- **Original file**: `tests/shared/core/test_elementwise_dispatch.mojo` — 47 tests
- **Split into**: 6 files of 8/8/8/8/8/7 tests
- **All pre-commit hooks**: Passed (mojo format, deprecated syntax check, validate test coverage, YAML)
- **PR**: #4106

### Session Results (Issue #3429)

- **Original file**: `tests/shared/core/test_activation_funcs.mojo` — 24 tests
- **Split into**: 3 files of 9/8/7 tests (ReLU+Sigmoid / Tanh+Softmax basic / Softmax axis+Integration)
- **All pre-commit hooks**: Passed
- **PR**: #4209

### Session Results (Issue #3432)

- **Original file**: `tests/shared/utils/test_logging.mojo` — 22 tests
- **Split into**: 3 files of 8/7/7 tests (log levels+formatters+console / file+multi+training / config+error+integration)
- **CI pattern**: `utils/test_*.mojo` glob — new files auto-discovered, no CI changes needed
- **Coverage script**: `validate_test_coverage.py` uses `Path.rglob("test_*.mojo")` — also auto-covered
- **All pre-commit hooks**: Passed on first attempt
- **PR**: #4215

### Session Results (Issue #3455)

- **Original file**: `tests/models/test_mobilenetv1_layers.mojo` — 19 tests
- **Split into**: 3 files of 7/7/5 tests (depthwise+pointwise conv / separable+BatchNorm+ReLU / avgpool+channel configs)
- **CI pattern**: `test_*_layers.mojo` glob in `Models` group — `_part1/2/3` files auto-discovered, no CI changes needed
- **validate_test_coverage.py**: No changes needed (auto-discovers split files via glob)
- **All pre-commit hooks**: Passed on first attempt
- **PR**: #4276

### Session Results (Issue #3458)

- **Original file**: `tests/models/test_googlenet_layers.mojo` — 18 tests
- **Split into**: 3 files of 8/6/4 tests (inception module+branches / concat+avgpool+FC / backward passes)
- **CI pattern**: `test_*_layers.mojo` glob in `Models` group does NOT match `test_googlenet_layers_part1.mojo` — explicit CI update required
- **validate_test_coverage.py**: Flagged part files as uncovered until CI pattern was updated
- **All pre-commit hooks**: Passed on first attempt
- **PR**: #4279

### Session Results (Issue #3607)

- **Original file**: `tests/shared/training/test_mixed_precision.mojo` — 13 tests
- **Split into**: 2 files of 8/5 tests (GradientScaler tests / gradient checking + clipping)
- **CI pattern**: `training/test_*.mojo` glob in `Shared Infra` group — new files auto-discovered, no CI changes needed
- **validate_test_coverage.py**: Exclusion list update required — replaced `test_mixed_precision.mojo` with `test_mixed_precision_part1.mojo` and `test_mixed_precision_part2.mojo`
- **All pre-commit hooks**: Passed on first attempt (mojo format, validate_test_coverage, mypy, ruff, bandit)
- **PR**: #4402

### Session Results (Issue #3623)

- **Original file**: `tests/shared/training/test_gradient_ops.mojo` — 12 tests
- **Split into**: 2 files of 8/4 tests (accumulate + scale operations / zero operations + workflow)
- **CI pattern**: `training/test_*.mojo` glob in `Shared Infra` group — new files auto-discovered, no CI changes needed
- **validate_test_coverage.py**: No changes needed — no explicit reference to original filename
- **All pre-commit hooks**: Passed on first attempt (mojo format, validate_test_coverage, YAML)
- **PR**: #4412

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Max tests per file (ADR-009 limit) | 10 |
| Target tests per file (headroom) | ≤8 |
| Naming convention | `test_<original>_partN.mojo` |
| Header comment | ADR-009 tracking comment (required) |
| CI workflow key | `pattern:` field in test group (glob or explicit) |

### Grouping Strategy

Group tests by **logical category** (operation type), not alphabetically:

- Part 1: First set of unary ops (ExpOp, LogOp, SqrtOp, SinOp, CosOp)
- Part 2: Next set of unary ops (TanhOp, AbsOp, NegateOp, SquareOp, SignOp)
- Part 3: Custom unary + first binary ops (AddOp, SubtractOp, MultiplyOp, DivideOp, PowerOp)
- Part 4: More binary ops (MaxOp, MinOp, comparison ops)
- Part 5: Logical ops, custom binary, dtype preservation
- Part 6: Error cases, 2D tensors, edge cases

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Share struct definitions via import | Tried to import `DoubleOp` from part1 in part3 | Mojo test files don't export symbols to other test files | Duplicate custom structs in each split file that needs them |
| Single combined CI pattern glob | Tried `test_elementwise_dispatch_part*.mojo` wildcard | `comprehensive-tests.yml` `pattern:` field uses space-separated literal names for explicit-list groups | List all filenames explicitly when the group uses explicit filenames |
| Keep original file + add split files | Considered keeping original for backwards compat | Would re-introduce the heap corruption bug | Delete original; replace completely |
| Assuming glob pattern for all CI groups | Did not check CI pattern type first | Some groups use explicit filenames, some use glob | Always check CI pattern type before deciding if workflow update is needed |
| Trusting issue description for CI group name | Issue said "Core NN Modules" | Actual CI group was "Core Utilities" — different name | Always grep the actual workflow: `grep -r "test_filename" .github/` |
| Using label in PR creation | `gh pr create --label "fix"` | Label "fix" didn't exist in the repo | Check `gh label list` first or omit `--label` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3399, PR #4106 | Split test_elementwise_dispatch.mojo (47 → 6 files) |
| ProjectOdyssey | Issue #3429, PR #4209 | Split test_activation_funcs.mojo (24 → 3 files), explicit CI update needed |
| ProjectOdyssey | Issue #3432, PR #4215 | Split test_logging.mojo (22 → 3 files), glob CI pattern auto-covered |
| ProjectOdyssey | Issue #3435, PR #4220 | Split test_arithmetic_backward.mojo (23 → 3 files), explicit CI pattern update |
| ProjectOdyssey | Issue #3455, PR #4276 | Split test_mobilenetv1_layers.mojo (19 → 3 files), glob CI pattern auto-covered |
| ProjectOdyssey | Issue #3458, PR #4279 | Split test_googlenet_layers.mojo (18 → 3 files, 8+6+4), explicit CI pattern update required |
| ProjectOdyssey | Issue #3490, PR #4352 | Split test_linear.mojo (14 → 2 files, 8+6), explicit CI list; issue named wrong CI group |
| ProjectOdyssey | Issue #3607, PR #4402 | Split test_mixed_precision.mojo (13 → 2 files, 8+5), glob CI auto-discovered; validate_test_coverage.py exclusion list update required |
| ProjectOdyssey | Issue #3623, PR #4412 | Split test_gradient_ops.mojo (12 → 2 files, 8+4), glob CI auto-discovered; no validate_test_coverage.py changes needed |

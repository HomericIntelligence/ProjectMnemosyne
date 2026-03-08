# Session Notes: ADR-009 Test File Splitting (Issue #3399)

## Context

- **Date**: 2026-03-07
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3399-auto-impl
- **Issue**: #3399 — fix(ci): split test_elementwise_dispatch.mojo (47 tests) — Mojo heap corruption (ADR-009)
- **PR**: #4106

## Problem

`tests/shared/core/test_elementwise_dispatch.mojo` had 47 `fn test_` functions.
ADR-009 mandates ≤10 per file to avoid Mojo v0.26.1 heap corruption from
`libKGENCompilerRTShared.so` JIT faults under high test load.

CI failure rate: 13/20 recent runs on main, rotating across groups (load-dependent).

## Approach Taken

1. Read original 47-test file end-to-end
2. Identified logical groupings (unary ops by type, binary ops by type, edge cases)
3. Created 6 split files of ≤8 tests each (target below the 10 limit for headroom)
4. Each file: full import block + required ADR-009 header comment + own `main()`
5. Custom structs (DoubleOp, IncrementOp, AverageOp) duplicated in files that need them
6. Deleted original file
7. Updated comprehensive-tests.yml pattern from old filename to 6 new filenames
8. All pre-commit hooks passed on first attempt

## Files Changed

- DELETED: `tests/shared/core/test_elementwise_dispatch.mojo`
- CREATED: `tests/shared/core/test_elementwise_dispatch_part1.mojo` (8 tests)
- CREATED: `tests/shared/core/test_elementwise_dispatch_part2.mojo` (8 tests)
- CREATED: `tests/shared/core/test_elementwise_dispatch_part3.mojo` (8 tests)
- CREATED: `tests/shared/core/test_elementwise_dispatch_part4.mojo` (8 tests)
- CREATED: `tests/shared/core/test_elementwise_dispatch_part5.mojo` (8 tests)
- CREATED: `tests/shared/core/test_elementwise_dispatch_part6.mojo` (7 tests)
- MODIFIED: `.github/workflows/comprehensive-tests.yml`

## Key Technical Observations

- Mojo test files cannot import from each other — each split file is fully self-contained
- The CI `pattern:` field takes space-separated literal filenames (no glob support)
- `validate_test_coverage.py` did not need updating (it passed automatically)
- Pre-commit hooks include a "Validate Test Coverage" step that auto-passed
- The `mojo format` hook took ~4 minutes for 6 new Mojo files

## Time Breakdown

- Reading/analyzing original file: ~1 min
- Creating 6 split files: ~3 min
- Updating CI workflow: ~1 min
- Waiting for pre-commit (mojo format): ~4 min

---

# Session Notes: ADR-009 Test File Splitting (Issue #3429)

## Context

- **Date**: 2026-03-07
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3429-auto-impl
- **Issue**: #3429 — fix(ci): split test_activation_funcs.mojo (24 tests) — Mojo heap corruption (ADR-009)
- **PR**: #4209

## Problem

`tests/shared/core/test_activation_funcs.mojo` had 24 `fn test_` functions (limit: 10, target: ≤8),
causing intermittent heap corruption in the `Core Activations & Types` CI group.

CI failure rate: 13/20 recent runs on main.

## Approach Taken

1. Read original 24-test file end-to-end
2. Distributed into 3 logical groups (ReLU+Sigmoid, Tanh+Softmax-basic, Softmax-axis+Integration)
3. Created 3 split files with ADR-009 header comment and full import blocks
4. Deleted original file
5. Updated `comprehensive-tests.yml` — the `Core Activations & Types` group uses an explicit
   file list (not a glob), so `test_activation_funcs.mojo` had to be replaced with 3 new names
6. All pre-commit hooks passed on first attempt

## Files Changed

- DELETED: `tests/shared/core/test_activation_funcs.mojo`
- CREATED: `tests/shared/core/test_activation_funcs_part1.mojo` (9 tests: ReLU + Sigmoid)
- CREATED: `tests/shared/core/test_activation_funcs_part2.mojo` (8 tests: Tanh + Softmax basic)
- CREATED: `tests/shared/core/test_activation_funcs_part3.mojo` (7 tests: Softmax axis + Integration)
- MODIFIED: `.github/workflows/comprehensive-tests.yml`

## Key Difference vs Issue #3399

Issue #3399 split a file in a CI group that used a glob (`test_*.mojo`), so new files were
auto-discovered. Issue #3429's `Core Activations & Types` group used a space-separated explicit
file list — new files are invisible to CI until the list is updated manually.

---

# Session Notes: ADR-009 Test File Splitting (Issue #3432)

## Context

- **Date**: 2026-03-07
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3432-auto-impl
- **Issue**: #3432 — fix(ci): split test_logging.mojo (22 tests) — Mojo heap corruption (ADR-009)
- **PR**: #4215

## Problem

`tests/shared/utils/test_logging.mojo` had 22 `fn test_` functions, causing intermittent
heap corruption crashes (`libKGENCompilerRTShared.so`) in Mojo v0.26.1 CI.
CI failure rate: 13/20 recent runs on `main` in the `Shared Infra` group.

## Approach Taken

1. Read original 22-test file end-to-end
2. Grouped into 3 logical categories (log levels+formatters+console / file+multi+training / config+error+integration)
3. Created 3 split files with ADR-009 header comment and full import blocks
4. Deleted original file
5. Checked `comprehensive-tests.yml` — the `Shared Infra` group uses `utils/test_*.mojo` glob,
   so new `_part1/2/3` files are auto-discovered. No CI matrix changes needed.
6. All pre-commit hooks passed on first attempt

## Files Changed

- DELETED: `tests/shared/utils/test_logging.mojo`
- CREATED: `tests/shared/utils/test_logging_part1.mojo` (8 tests: log levels, formatters, console handler)
- CREATED: `tests/shared/utils/test_logging_part2.mojo` (7 tests: file handler, multi-handler, training logging)
- CREATED: `tests/shared/utils/test_logging_part3.mojo` (7 tests: logger config/factory, error handling, integration)
- MODIFIED: `.github/workflows/comprehensive-tests.yml` (comment update only)

## Key Technical Observations

- `utils/test_*.mojo` is a glob pattern — new files with `_partN` suffix auto-discovered
- `validate_test_coverage.py` uses `Path.rglob("test_*.mojo")` — also auto-covered
- No CI matrix changes needed when the group uses glob-based pattern

## What Failed

Nothing. Approach was straightforward on first attempt. Pre-commit hooks passed immediately.

---

# Session Notes: ADR-009 Test File Splitting (Issue #3435)

## Context

- **Date**: 2026-03-07
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3435-auto-impl
- **Issue**: #3435 — fix(ci): split test_arithmetic_backward.mojo (23 tests) — Mojo heap corruption (ADR-009)
- **PR**: #4220

## Problem

`tests/shared/core/test_arithmetic_backward.mojo` had 23 `fn test_` functions, causing
intermittent heap corruption in the `Core Tensors` CI group (13/20 recent runs failing).

## Approach Taken

1. Read original 23-test file end-to-end
2. Grouped into 3 logical categories:
   - Part 1 (8): element-wise + scalar backward ops (add/subtract/multiply/divide, tests 1–8)
   - Part 2 (8): broadcasting tests + numerical gradient checking for A operand (tests 9–16)
   - Part 3 (7): numerical gradient checking for B operand + broadcast grad checks (tests 17–23)
3. Created 3 split files with ADR-009 header comment and full import blocks
4. Deleted original file entirely
5. Updated `comprehensive-tests.yml` — `Core Tensors` group uses explicit filename list;
   replaced `test_arithmetic_backward.mojo` with the three new filenames
6. All pre-commit hooks passed on first attempt

## Files Changed

- DELETED: `tests/shared/core/test_arithmetic_backward.mojo`
- CREATED: `tests/shared/core/test_arithmetic_backward_part1.mojo` (8 tests)
- CREATED: `tests/shared/core/test_arithmetic_backward_part2.mojo` (8 tests)
- CREATED: `tests/shared/core/test_arithmetic_backward_part3.mojo` (7 tests)
- MODIFIED: `.github/workflows/comprehensive-tests.yml`

## Key Technical Observations

- This is the 4th application of this pattern; the explicit-vs-glob distinction was recognized immediately
- ADR-009 header comment placed at very top of file (before docstring) — consistent with other splits
- `validate_test_coverage.py` did not require changes (uses `Path.rglob("test_*.mojo")`)

## What Failed

Nothing. Pattern well-established by this point. Pre-commit hooks passed on first attempt.

---

# Session Notes: ADR-009 Test File Splitting (Issue #3455)

## Context

- **Date**: 2026-03-07
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3455-auto-impl
- **Issue**: #3455 — fix(ci): split test_mobilenetv1_layers.mojo (19 tests) — Mojo heap corruption (ADR-009)
- **PR**: #4276

## Problem

`tests/models/test_mobilenetv1_layers.mojo` had 19 `fn test_` functions across 6 categories
(depthwise conv, pointwise conv, separable blocks, batchnorm, relu, pooling + channel configs),
exceeding ADR-009 limit of ≤10 per file.

## Approach Taken

1. Read original 19-test file end-to-end
2. Checked CI workflow — `Models` group uses `test_*_layers.mojo` glob pattern
3. New files named `_part1/2/3` match this glob automatically
4. Created 3 split files with ADR-009 header comment and full import blocks
5. Deleted original file
6. No CI workflow changes needed
7. All pre-commit hooks passed on first attempt

## Files Changed

- DELETED: `tests/models/test_mobilenetv1_layers.mojo`
- CREATED: `tests/models/test_mobilenetv1_layers_part1.mojo` (7 tests: depthwise + pointwise conv)
- CREATED: `tests/models/test_mobilenetv1_layers_part2.mojo` (7 tests: separable blocks + BatchNorm + ReLU)
- CREATED: `tests/models/test_mobilenetv1_layers_part3.mojo` (5 tests: global avgpool + channel configs)

## Key Technical Observations

- `test_*_layers.mojo` glob in the `Models` CI group auto-discovers `_partN` files
- `validate_test_coverage.py` uses glob patterns — auto-discovers split files without changes
- This is the 5th application of the pattern; glob vs explicit check is now the first step

## What Failed

Nothing. Approach was straightforward on first attempt. Pre-commit hooks passed immediately.

---

# Session #3458: test_googlenet_layers.mojo

- **Issue**: #3458
- **PR**: #4279
- **Original**: 18 tests → 3 parts (8+6+4)
- **Key finding**: `test_*_layers.mojo` glob does NOT match `test_googlenet_layers_part1.mojo` — explicit CI update required
- **validate_test_coverage.py**: Caught uncovered part files, confirmed CI update was needed
- **Pre-commit hooks**: All passed on first attempt

---

# Session #3462: test_advanced_activations.mojo

- **Issue**: #3462
- **PR**: #4288
- **Original**: 17 tests → 3 parts (4+8+5)
- **Split**: Part1=Swish/SiLU (4), Part2=Mish+ELU forward (8), Part3=ELU backward (5)
- **CI group**: `Core Activations & Types` uses explicit space-separated filename list
- **Workflow update**: Required — replaced `test_advanced_activations.mojo` with 3 new filenames
- **Pre-commit hooks**: All passed on first attempt (mojo format, validate_test_coverage, YAML)
- **Key note**: Targeting ≤8 tests per file (not just ≤10) provides a safety margin

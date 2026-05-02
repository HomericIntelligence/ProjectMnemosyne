# Session Notes: retry-all-mojo-workflow-calls

## Context

- **Date**: 2026-03-07
- **Repository**: ProjectOdyssey
- **Issue**: #3329 (follow-up to #3120)
- **PR**: #3950
- **Branch**: `3329-auto-impl`

## Background

Issue #3120 added retry logic to `just test-group` for Mojo JIT crashes
(see `mojo-jit-crash-retry` skill). However the retry only covered tests
run via `just test-group`. Other workflows still called `pixi run mojo`
directly — `build-validation.yml`, `model-e2e-tests-weekly.yml`,
`test-gradients.yml`, `test-data-utilities.yml`, etc.

Issue #3329 was filed to audit ALL workflows and extend retry everywhere.

## Audit Results

Bare `pixi run mojo` calls found (excluding `mojo --version` and `mojo format`):

| File | Line | Call | Type |
| ------ | ------ | ------ | ------ |
| `comprehensive-tests.yml` | 114 | `mojo package -I "$REPO_ROOT" shared` | Package build |
| `test-gradients.yml` | 39-40 | `mojo -I . tests/shared/core/test_gradient_checking_basic.mojo` + dtype | Test file |
| `test-data-utilities.yml` | 47,52,60,67,75,84 | `mojo -I . tests/shared/data/...` | Test files (5) |
| `simd-benchmarks-weekly.yml` | 45 | `mojo run -I . benchmarks/bench_simd.mojo` | Benchmark |
| `benchmark.yml` | 96 | `mojo -I . "$SUITE_PATH/run_benchmark.mojo"` | Benchmark |
| `release.yml` | 142,251,268 | `mojo build`, `mojo test tests/unit/`, `mojo test tests/integration/` | Build + tests |
| `paper-validation.yml` | 253,306 | `mojo test -I . "$paper_dir/tests"`, `mojo -I . "$paper_dir/train.mojo"` | Tests + training |

## Decision: Route vs Inline Retry

Test workflows were routed through `just test-group` because:
- Inherits any future improvements to `just test-group` automatically
- Cleaner YAML (one line vs 12-line retry loop)
- Consistent with how `comprehensive-tests.yml` already works

Non-test calls (benchmarks, builds, package compilation) used inline loops because:
- `just test-group` pattern-matches `.mojo` test files by pattern
- Benchmark scripts have different output expectations
- `mojo build` in a `find | while read` pipe needs the retry nested inside

## Key Implementation Notes

### `test-data-utilities.yml` — Per-file existence checks dropped

The original workflow had per-file `if [ -f ... ]` guards before each `pixi run mojo`
call. These were dropped when routing to `just test-group` because:
- `just test-group` handles missing files gracefully (exits 0 with a warning)
- The guards only existed to prevent hard failures on missing files
- This matches the intent of the original code (soft-fail when files don't exist yet)

### `paper-validation.yml` — `|| true` preserved

The paper-validation mojo calls already had `|| true` (soft failures).
The retry loop was wrapped to preserve this semantic:

```bash
while [ ... ]; do
  attempt=$((attempt + 1))
  if pixi run mojo ...; then break; fi
  ...
  else echo "failed after 3 attempts (soft failure)"; fi
done || true  # <-- preserved soft-fail
```

### `justfile` — Upgraded from 2 to 3 attempts

Original justfile had a simple if/else (attempt 1 + 1 retry = 2 attempts total).
Upgraded to 3 attempts with 1s/2s exponential backoff using a while loop.
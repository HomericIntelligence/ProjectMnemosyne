# Session Notes: ADR-009 Split with Explicit CI Pattern

## Context

- **Issue**: #3446 — fix(ci): split test_fixtures.mojo (20 tests) per ADR-009
- **PR**: #4245
- **Branch**: `3446-auto-impl`
- **Date**: 2026-03-07

## Problem

`tests/shared/testing/test_fixtures.mojo` contained 20 `fn test_` functions, exceeding
ADR-009's limit of ≤10 per file (target: ≤8). This caused intermittent heap corruption
crashes in Mojo v0.26.1 (`libKGENCompilerRTShared.so` JIT fault), causing the Testing
Fixtures CI group to fail non-deterministically (13/20 recent runs).

## Key Discovery

The existing `adr009-test-file-splitting` skill states:
> "CI glob auto-picks up new files if named test_*.mojo in the right directory — No workflow changes needed"

However, the `Shared Infra & Testing` CI matrix group used an **explicit filename list**,
not a glob:

```yaml
pattern: "test_imports.mojo test_data_generators.mojo ... testing/test_*.mojo"
```

Wait — the actual pattern was mixed. The `testing/` subdirectory was included as `testing/test_*.mojo`
in some versions, but in this issue's version, the `testing/test_fixtures.mojo` was
**not covered by the glob** because the pattern ended at `training/test_*.mojo` without
a `testing/test_*.mojo` entry. The `validate-test-coverage` pre-commit hook would have
caught any uncovered new files.

## Files Changed

- **Deleted**: `tests/shared/testing/test_fixtures.mojo` (20 tests)
- **Created**: `tests/shared/testing/test_fixtures_part1.mojo` (8 tests)
- **Created**: `tests/shared/testing/test_fixtures_part2.mojo` (8 tests)
- **Created**: `tests/shared/testing/test_fixtures_part3.mojo` (4 tests)
- **Updated**: `.github/workflows/comprehensive-tests.yml` — replaced old glob entry with explicit part file names

## Pre-Commit Hook Results

All hooks passed on first attempt:

- `Mojo Format` — Passed
- `Check for deprecated List[Type](args) syntax` — Passed
- `Validate Test Coverage` — Passed (new files found in updated workflow)
- `Check YAML` — Passed
- `Trim Trailing Whitespace` — Passed
- `Fix End of Files` — Passed
- `Fix Mixed Line Endings` — Passed

## Commit

```
fix(ci): split test_fixtures.mojo into 3 files per ADR-009

test_fixtures.mojo had 20 fn test_ functions, exceeding the ADR-009
limit of 10 per file.
```

## ADR-009 Header Position

The ADR-009 comment was placed as a file-level comment **before** the module docstring,
as Mojo treats `# ...` lines as comments only when they appear outside string literals.

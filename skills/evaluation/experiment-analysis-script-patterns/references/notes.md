# Session Notes — experiment-analysis-script-patterns

**Date**: 2026-03-15
**Branch**: `1490-always-retry-infra-failures`
**PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1500

## Context

dryrun3 experiment suite: 47 tests (test-001 through test-047), 65 experiment directories
spanning two generations (Feb 23-26 and March 4, 2026). The analysis script and retry
shell script both had bugs discovered after the experiment completed.

## Bugs Fixed

### Bug 1: Regex in `discover_experiments()` (scripts/analyze_dryrun3.py:55)

**Old**: `r"^(\d{4}-\d{2}-\d{2}T\d{6})-(\w+)-(test-\d{3})$"`
- Expected format: `2026-02-23T185610-word-test-017`
- Actual format: `2026-02-23T18-56-10-test-017`
- `T\d{6}` requires 6 contiguous digits; actual has dashes (`T18-56-10`)
- Group 3 captured test name; removing intermediate group breaks indexing

**New**: `r"^(\d{4}-\d{2}-\d{2}T[\d-]+)-(test-\d{3})$"`
- group(2) = test name (group count reduced from 3 to 2)

### Bug 2: Run multiplier `* 3` (lines 223-225, 334, 372)

- Code assumed 3 runs per subtest (standard config)
- dryrun3 uses 1 run per subtest
- `expected_runs = TOTAL_SUBTESTS_FULL * 3` → `* 1`
- `total_missing_runs += (expected - actual) * 3` → `* 1`
- Report line `{total_ms} subtests = {total_ms * 3} runs` → simplified

### Bug 3: No exit code from analysis script

- `generate_report()` returned `None`
- `main()` did not use verdict to set exit code
- Added return value `(verdict, reasons)` to `generate_report()`
- `main()`: `sys.exit(1)` for NOGO, `sys.exit(0)` for GO/CONDITIONAL_GO

### Bug 4: `set -e` in retry_dryrun3.sh

- `set -euo pipefail` caused entire 47-test suite to abort on first non-zero exit
- Infrastructure failures (which are expected and being retried) triggered abort
- Replaced with `set -uo pipefail` + per-test `if !` error capture + `FAILED_TESTS` array

## Additional Changes

- Orphan label: removed "test-004 only" specificity → generic "ignored"
- Added pre-run analysis call (with `|| true`) before retry loop
- Added post-run analysis call after retry loop (exit code propagates)
- Added `--parallel 1` flag to full-ablation tests (was missing)

## Commit

`9fb37229 fix(dryrun3): fix regex, run multiplier, exit codes, and retry error handling`

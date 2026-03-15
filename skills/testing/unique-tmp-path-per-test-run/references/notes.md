# Session Notes: unique-tmp-path-per-test-run

## Session Context

- **Date**: 2026-03-15
- **Issue**: ProjectOdyssey #3878
- **Branch**: 3878-auto-impl
- **PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4818

## Objective

Fix `test_safe_remove()` in `tests/shared/utils/test_io_part2.mojo` to prevent
stale `/tmp` files across test runs. The hardcoded path
`/tmp/test_remove_safely_3283.txt` could be left behind if the test aborted
between file creation and the `finally` block, causing subsequent runs to see
unexpected filesystem state.

## Steps Taken

1. Read the issue body and existing implementation plan from `gh issue view 3878 --comments`
2. Read `tests/shared/utils/test_io_part2.mojo` to understand the current structure
3. Confirmed the `try/finally` was already correct — only the path was the problem
4. Added `from time import perf_counter_ns` inline in the function
5. Replaced the hardcoded path with `"/tmp/test_remove_safely_" + String(perf_counter_ns()) + ".txt"`
6. Verified `grep -r "test_remove_safely_3283" tests/` returned no results
7. Committed, pushed, and opened PR

## What Worked

- Inline `from time import perf_counter_ns` import compiles fine in Mojo v0.26.1
- `String(perf_counter_ns())` produces a unique numeric suffix with nanosecond granularity
- The change was 3 lines: +2 additions, -1 deletion — minimal and focused

## What Failed / Was Rejected

- `uuid` module not available in Mojo v0.26.1 stdlib
- Considered extracting a helper function — rejected as YAGNI (single call site)

## Key Insight

The issue plan correctly identified that the `try/finally` structure was already
sound. The only risk was the fixed path being shared across runs. Using
`perf_counter_ns()` is the idiomatic Mojo solution when `uuid` is unavailable.

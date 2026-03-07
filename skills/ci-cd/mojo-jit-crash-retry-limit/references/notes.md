# Session Notes: mojo-jit-crash-retry-limit

## Context

- **Date**: 2026-03-07
- **Issue**: HomericIntelligence/ProjectOdyssey #3328
- **PR**: HomericIntelligence/ProjectOdyssey #3949
- **Branch**: `3328-auto-impl`
- **Follow-up to**: Issue #3120, PR #3223 (mojo-jit-crash-retry)

## Problem Statement

After the original retry fix (PR #3223), the `just test-group` recipe:

1. Retried all failures (not just JIT crashes) — wasted CI minutes on deterministic failures
2. Emitted the same `FAILED` message regardless of whether a retry was used
3. Had no `MAX_RETRIES` variable — retry count was hard-coded implicitly

Issue #3328 asked for:
- Counter/limit to prevent infinite retry loops (not a real risk with 1 retry, but good hygiene)
- Distinct messages: `FAILED after retry` vs `FAILED (no crash, no retry)`
- CI log parsers to tell the two failure modes apart

## Implementation

Single file changed: `justfile` lines 499-521 (the per-file loop in `test-group`).

### Before (22 lines)

```bash
# Run each test file
for test_file in $test_files; do
    if [ -f "$test_file" ]; then
        echo ""
        echo "Running: $test_file"
        test_count=$((test_count + 1))

        if pixi run mojo -I "$REPO_ROOT" -I . "$test_file"; then
            echo "PASSED: $test_file"
            passed_count=$((passed_count + 1))
        else
            echo "FAILED (attempt 1), retrying: $test_file"
            if pixi run mojo -I "$REPO_ROOT" -I . "$test_file"; then
                echo "PASSED on retry: $test_file"
                passed_count=$((passed_count + 1))
            else
                echo "FAILED: $test_file"
                failed_count=$((failed_count + 1))
                failed_tests="$failed_tests\n  - $test_file"
            fi
        fi
    fi
done
```

### After (47 lines)

See SKILL.md Verified Workflow section for the full replacement block.

## Tests Run

- `pixi run python -m pytest tests/scripts/test_retry_logic.py -v` — 20/20 passed
- Pre-commit hooks passed (trailing whitespace, end-of-file, large files, line endings)

## Notes

- The `test_retry_logic.py` file tests the Python `scripts/utils/retry.py` module (network retry backoff),
  not the justfile bash logic. There are no Python-level tests for the bash retry behavior.
- The issue plan explicitly noted "no new test files needed" — the change is a bash script edit.
- `just` was not available in the worktree environment; bash syntax checked via `grep -P "\s+$"` and
  manual review of the diff.

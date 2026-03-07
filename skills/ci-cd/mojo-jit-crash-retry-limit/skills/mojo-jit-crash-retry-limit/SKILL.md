---
name: mojo-jit-crash-retry-limit
description: "Add retry limit and distinct failure messages to just test-group crash retry. Use when: blind retry-all loop needs to be replaced with crash-aware retry, or CI logs cannot distinguish retry-exhausted from normal failures."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

# mojo-jit-crash-retry-limit

Refine `just test-group` retry logic to only retry on `execution crashed` (JIT crash marker),
add a `MAX_RETRIES` limit, and emit distinct failure messages for retry-exhausted vs normal failures.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Mojo Version | 0.26.1.0.dev2025122805 |
| Objective | Distinguish crash-retry failures from normal failures in CI logs |
| Outcome | Success - crash-aware retry with distinct `FAILED after retry` / `FAILED (no crash, no retry)` messages |
| Repository | ProjectOdyssey |
| Issue | #3328 (follow-up to #3120) |
| PR | #3949 |
| Prereq Skill | mojo-jit-crash-retry |

## When to Use

- The `just test-group` retry loop retries ALL failures (not just JIT crashes)
- CI logs show `FAILED` with no indication of whether a retry was used
- You need to distinguish "crash-exhausted retry" from "test logic failure" in CI logs
- Follow-up to `mojo-jit-crash-retry` skill — the original fix added retry but without a limit or distinct messages

## Verified Workflow

### Problem: Blind Retry (Post mojo-jit-crash-retry, Pre This Fix)

After the original fix (issue #3120, PR #3223), the `just test-group` recipe looked like this:

```bash
if pixi run mojo -I "$REPO_ROOT" -I . "$test_file"; then
    echo "PASSED: $test_file"
    passed_count=$((passed_count + 1))
else
    echo "FAILED (attempt 1), retrying: $test_file"
    if pixi run mojo -I "$REPO_ROOT" -I . "$test_file"; then
        echo "PASSED on retry: $test_file"
        passed_count=$((passed_count + 1))
    else
        echo "FAILED: $test_file"          # same message for both failure modes
        failed_count=$((failed_count + 1))
        failed_tests="$failed_tests\n  - $test_file"
    fi
fi
```

**Problems:**
- Retries all failures (even non-crash ones), wasting CI time
- Both failure modes produce identical `FAILED` output — no diagnostic value
- No `MAX_RETRIES` variable — hard to adjust retry count

### Fix: Crash-Aware Retry with Distinct Messages

Replace the entire per-file execution block with:

```bash
MAX_RETRIES=1

# Run each test file
for test_file in $test_files; do
    if [ -f "$test_file" ]; then
        echo ""
        echo "Running: $test_file"
        test_count=$((test_count + 1))

        file_passed=false
        retry_used=false
        fail_reason=""

        for attempt in $(seq 1 $((MAX_RETRIES + 1))); do
            output=$(pixi run mojo -I "$REPO_ROOT" -I . "$test_file" 2>&1)
            exit_code=$?
            echo "$output"

            if [ $exit_code -eq 0 ]; then
                file_passed=true
                break
            fi

            # Check for JIT/execution crash and retry if attempts remain
            if echo "$output" | grep -q "execution crashed" && [ $attempt -le $MAX_RETRIES ]; then
                echo "Execution crashed, retrying ($attempt/$MAX_RETRIES)..."
                retry_used=true
            else
                if [ "$retry_used" = true ]; then
                    fail_reason="FAILED after retry"
                else
                    fail_reason="FAILED (no crash, no retry)"
                fi
                break
            fi
        done

        if [ "$file_passed" = true ]; then
            echo "PASSED: $test_file"
            passed_count=$((passed_count + 1))
        else
            echo "$fail_reason: $test_file"
            failed_count=$((failed_count + 1))
            failed_tests="$failed_tests\n  - $test_file [$fail_reason]"
        fi
    fi
done
```

**Key design decisions:**
- `MAX_RETRIES=1` — easy to adjust, documents intent
- `output=$(... 2>&1)` — captures combined stdout+stderr for crash detection
- `echo "$output"` — immediately prints captured output for CI log visibility
- `grep -q "execution crashed"` — only retries on known JIT crash marker
- `retry_used=true` flag — tracks whether a retry was attempted (for the final message)
- Failure reason appended in summary list: `- test_file.mojo [FAILED after retry]`

### Output Comparison

| Scenario | Before | After |
|----------|--------|-------|
| JIT crash → retry → fail | `FAILED: test_file.mojo` | `FAILED after retry: test_file.mojo` |
| Normal assertion failure | `FAILED: test_file.mojo` (after blind retry) | `FAILED (no crash, no retry): test_file.mojo` |
| JIT crash → retry → pass | `PASSED on retry: test_file.mojo` | `PASSED: test_file.mojo` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3328, PR #3949 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `tee` + `${PIPESTATUS[0]}` | Stream output in real-time while capturing (pattern from mojo-jit-crash-retry SKILL.md) | Works but adds temp file complexity; `$(... 2>&1)` with immediate `echo` is simpler for this use case | Capturing with subshell is fine when output is short (test file output); `tee` pattern better for very long-running processes |
| Separate crash-check run | Run mojo twice: once to capture, once to check exit code | Doubles execution time unnecessarily | Capture once with `$()`, check exit code and output from same run |

## Results & Parameters

```bash
# Verify the fix: search for distinct failure messages in CI logs
gh run view <run-id> --log 2>&1 | grep -E "FAILED after retry|FAILED \(no crash"

# Adjust retry limit (default 1)
# Edit justfile: change MAX_RETRIES=1 to desired value

# Manually test the crash detection logic
echo "execution crashed" | grep -q "execution crashed" && echo "crash detected"
```

**Summary list format** (appended for each failed test):

```text
Failed tests:
  - tests/shared/core/test_foo.mojo [FAILED after retry]
  - tests/shared/core/test_bar.mojo [FAILED (no crash, no retry)]
```

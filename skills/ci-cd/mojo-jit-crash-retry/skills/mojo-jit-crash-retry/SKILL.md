---
name: mojo-jit-crash-retry
description: "Diagnose and fix intermittent Mojo JIT compiler crashes in CI. Use when: Mojo tests report 'execution crashed' before printing any output, crash stack shows libKGENCompilerRTShared.so, same test passes/fails non-deterministically."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

# mojo-jit-crash-retry

Fix intermittent Mojo JIT compiler crashes (`libKGENCompilerRTShared.so` abort) in CI by
adding retry logic to the `just test-group` recipe.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Mojo Version | 0.26.1.0.dev2025122805 |
| Objective | Fix intermittent CI crashes in Mojo tests that fail before executing any test code |
| Outcome | Success - retry on "execution crashed" output |
| Repository | ProjectOdyssey |
| Issue | #3120 |
| PR | #3223 |

## When to Use

- Mojo test files crash with `error: execution crashed` and no test output is printed
- Crash stack: `libKGENCompilerRTShared.so+0x3c60bb` → `libc.so.6+0x45330` (abort)
- Same test files pass on some CI runs and fail on others (non-deterministic)
- Multiple unrelated test groups fail simultaneously in the same CI run
- Tests were passing previously with the same code and same Mojo version
- CI failure occurs during JIT compilation phase (before `main()` runs)

## Diagnosis Steps

### 1. Confirm It's a JIT Crash (Not a Code Bug)

Check CI logs for this exact pattern:

```text
Running: tests/shared/core/test_foo.mojo
#0 0x00007f... (/path/to/.pixi/envs/default/lib/libKGENCompilerRTShared.so+0x3c60bb)
#1 0x00007f... (/path/to/.pixi/envs/default/lib/libKGENCompilerRTShared.so+0x3c3ce6)
#2 0x00007f... (/path/to/.pixi/envs/default/lib/libKGENCompilerRTShared.so+0x3c6cc7)
#3 0x00007f... (/lib/x86_64-linux-gnu/libc.so.6+0x45330)
/path/to/mojo: error: execution crashed
❌ FAILED: tests/shared/core/test_foo.mojo
```

Key distinguishing characteristics:
- Stack trace appears **before** any test code output (not after `print` statements)
- Identical offsets in `libKGENCompilerRTShared.so` across all affected tests
- `libc.so.6+0x45330` is the `__fortify_fail_abort` function in glibc
- Frame #4 varies per test file (different JIT code paths)

### 2. Confirm Non-Determinism

```bash
# Check multiple recent CI runs for the same tests
gh run list --workflow="comprehensive-tests.yml" --limit 10 --json databaseId,status,conclusion,headBranch

# Check if same test passed in a different run
gh run view <passing-run-id> --log 2>&1 | grep -E "PASSED.*test_foo|FAILED.*test_foo"
gh run view <failing-run-id> --log 2>&1 | grep -E "PASSED.*test_foo|FAILED.*test_foo"
```

### 3. Rule Out Code Bugs

- Verify no changes to the affected test files or their imported modules
- Check that other test groups (not affected by the crash) pass fine
- Compare import chains: what does the failing test import vs passing tests?
- Note: A larger import chain does NOT cause crashes - it's purely a JIT flakiness issue

## Verified Workflow

### Fix: Add Retry Logic to `justfile`

Modify the `test-group` recipe in `justfile` to detect "execution crashed" and retry once:

```bash
# Original (no retry)
if pixi run mojo -I "$REPO_ROOT" -I . "$test_file"; then
    echo "✅ PASSED: $test_file"
    passed_count=$((passed_count + 1))
else
    echo "❌ FAILED: $test_file"
    failed_count=$((failed_count + 1))
    failed_tests="$failed_tests\n  - $test_file"
fi
```

Replace with (retry on "execution crashed"):

```bash
# With retry for Mojo JIT crashes
tmp_out=$(mktemp)
# ... (in loop, before this block) ...

pixi run mojo -I "$REPO_ROOT" -I . "$test_file" 2>&1 | tee "$tmp_out"
exit_code=${PIPESTATUS[0]}

if [ $exit_code -eq 0 ]; then
    echo "✅ PASSED: $test_file"
    passed_count=$((passed_count + 1))
elif grep -q "execution crashed" "$tmp_out"; then
    # Retry once on Mojo JIT compiler crashes (intermittent CI flakiness)
    echo "⚠️  Mojo runtime crash detected, retrying: $test_file"
    if pixi run mojo -I "$REPO_ROOT" -I . "$test_file"; then
        echo "✅ PASSED (retry): $test_file"
        passed_count=$((passed_count + 1))
    else
        echo "❌ FAILED: $test_file"
        failed_count=$((failed_count + 1))
        failed_tests="$failed_tests\n  - $test_file"
    fi
else
    echo "❌ FAILED: $test_file"
    failed_count=$((failed_count + 1))
    failed_tests="$failed_tests\n  - $test_file"
fi

# ... after loop ...
rm -f "$tmp_out"
```

**Key design decisions:**
- Use `tee` to stream output in real-time while capturing to temp file (preserves CI observability)
- Use `${PIPESTATUS[0]}` (not `$?`) to get `mojo`'s exit code through the pipe
- Only retry on "execution crashed" - normal test assertion failures fail fast
- Only retry once - if it crashes twice, it's likely a harder failure
- The temp file approach avoids losing the crash stack trace in CI logs

### Root Cause

The Mojo JIT compiler (`libKGENCompilerRTShared.so`) has a race condition or memory corruption
bug that causes sporadic `abort()` calls during code generation. This is:

- **NOT related to test code correctness** - the test logic never executes
- **NOT Azure-region-specific** - crashes observed on northcentralus, westcentralus, westus3
- **NOT deterministic** - same commit/Mojo version passes/fails randomly
- **A known Mojo compiler issue** - fixed offset `0x3c60bb` suggests specific internal assertion

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Removing `activation.mojo` import | Changed `loss.mojo` to import `dispatch_softmax` directly instead of `softmax` from `activation.mojo` | `test_loss_funcs.mojo` and `test_loss_utils.mojo` don't import activation at all but still crash - so import chain is irrelevant | The crash is in the JIT compiler itself, not triggered by any specific Mojo code pattern |
| Identifying bad code patterns | Analyzed ExTensor refcount, bool→float casts, memory management | All patterns are correct - no bugs found | The crash happens before any runtime code executes, so runtime bugs aren't the cause |
| Region-specific theory | Checked if specific Azure region (northcentralus) always fails | Crashes occur on westcentralus and westus3 too; northcentralus passes sometimes | Azure region is not the determining factor |
| Code change investigation | Compared git history between passing (Feb 8) and failing commits | Same code, same Mojo version, different outcomes | Confirms intermittent JIT issue, not a regression from code changes |

## Results & Parameters

```bash
# Crash identification command
gh run view <run-id> --log-failed 2>&1 | grep -E "execution crashed|libKGENCompilerRTShared|#[0-9]"

# Check if failure is in the same test across multiple runs
for run_id in <run1> <run2> <run3>; do
  echo "Run $run_id:"
  gh run view $run_id --log 2>&1 | grep -E "PASSED.*test_|FAILED.*test_" | grep test_loss | head -5
done

# Verify same Mojo version in passing vs failing run
gh run view <passing-run-id> --log 2>&1 | grep "Mojo"
gh run view <failing-run-id> --log 2>&1 | grep "Mojo"
```

**Mojo crash signature** (exact offsets may differ between Mojo versions):

```text
#0 libKGENCompilerRTShared.so+0x3c60bb  # Mojo internal assertion
#1 libKGENCompilerRTShared.so+0x3c3ce6  # Mojo internal assertion
#2 libKGENCompilerRTShared.so+0x3c6cc7  # Mojo internal assertion
#3 libc.so.6+0x45330                    # __fortify_fail_abort in glibc
#4 <varies per test file>               # Different JIT codegen path
```

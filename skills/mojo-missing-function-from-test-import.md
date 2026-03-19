---
name: mojo-missing-function-from-test-import
description: 'Debug Mojo test import failures where a function exists in tests but
  not in the source module. Use when: (1) Mojo test imports a function that causes
  compilation errors, (2) CI tests are skipped due to package compilation failure,
  (3) investigating why a Mojo test file was added without the corresponding implementation.'
category: debugging
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-15 |
| **Category** | debugging |
| **Problem** | Mojo test file imports a function that doesn't exist in the source module |
| **Symptom** | CI tests all skipped because `mojo-compilation` job fails |
| **Root cause** | Function was planned but not implemented, or removed due to API incompatibility |
| **Fix** | Add the missing function to the source module matching the test's expected signature |

## When to Use

- A Mojo test file imports a symbol that causes `mojo package` compilation to fail
- CI shows all test matrix jobs as SKIPPED (they `need: [mojo-compilation]`)
- A test file was created before the implementation was complete
- Prior PR added a test but the implementation PR failed CI due to a different issue

Do NOT use when:

- The test failure is a value assertion error (dtype partial support — separate skill)
- The import error is a known-broken module unrelated to a missing function
- The test was intentionally added to document planned future work

## Verified Workflow

### Quick Reference

```bash
# 1. Find the import error
gh run view <run-id> --log-failed | grep "error:"

# 2. Search git history for prior fix attempts
git log --oneline --all | grep -i "<keyword>"

# 3. See exact diff from prior fix
git show <sha> -- <file>

# 4. Verify coverage without Mojo
python3 scripts/validate_test_coverage.py
```

### Step 1: Identify which CI job is failing

The key symptom is ALL test jobs showing as SKIPPED. This means a prerequisite job failed.

```bash
# Check which jobs failed on a PR
gh pr view <PR_NUMBER> --json statusCheckRollup | jq '.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name'

# Get logs from the failed job
gh run view <RUN_ID> --log-failed | grep -E "error:|FAILED|Failed:"
```

The compilation failure will show: `module 'X' does not contain 'Y'` or `unable to locate module`.

### Step 2: Find the missing symbol in the test file

```bash
# Check what the test imports
grep "^from\|^import" tests/path/to/test_file.mojo

# Check if the symbol exists in the source
grep -n "fn <symbol_name>" shared/path/to/source.mojo
```

### Step 3: Search git history for prior fix attempts

Often, someone has already tried to fix this. Check git history:

```bash
# Search all branches for prior fix commits
git log --oneline --all | grep -i "<function_name>"
git log --oneline --all | grep -i "fix.*<keyword>"

# See the exact diff of a prior fix
git show <sha> -- <source_file>

# Check which branches contain the fix
git branch --contains <sha>
```

This avoids reinventing the wheel and reveals the correct implementation approach.

### Step 4: Understand why the original PR failed

If a prior fix exists in a branch but not on main, check why it wasn't merged:

```bash
# The original PR may have had unrelated CI failures
# Template files with {{placeholder}} syntax fail mojo build — this is pre-existing
# Focus on the actual symbol error, not template errors
gh run view <RUN_ID> --log-failed | grep "<your_module>"
```

### Step 5: Implement the missing function

Add the function to the source module. Match the exact signature the test expects:

```mojo
# Example: test calls _check_bf16_platform_support(True) and _check_bf16_platform_support(False)
# So the function takes is_apple: Bool (not a platform detection API call)

fn _check_bf16_platform_support(is_apple: Bool) raises:
    """Check if BF16 is supported on the target platform.

    Args:
        is_apple: True if running on Apple Silicon, False otherwise.

    Raises:
        Error: If BF16 is requested on Apple Silicon.
    """
    if is_apple:
        raise Error(
            "BF16 (bfloat16) is NOT supported on Apple Silicon (M1/M2/M3). "
            "Use PrecisionConfig.fp16() instead, which is fully supported."
        )
```

**Critical**: In Mojo v0.26.1, `sys.info.is_apple_silicon()` does NOT exist. Do not use
platform detection APIs — accept the boolean as a parameter for testability.

### Step 6: Verify test coverage configuration

Check that the test file is already covered by CI (often it is via wildcard patterns):

```bash
# Run coverage validation (no Mojo needed)
python3 scripts/validate_test_coverage.py
# Exit 0 with no output = all tests covered
```

If the test file is already matched by `training/test_*.mojo` or a similar wildcard,
**no workflow changes are needed**.

### Step 7: Verify error message matches test assertions

Read the test carefully to match all expected substrings in error messages:

```bash
# Check what the test asserts about the error message
grep '"' tests/path/to/test.mojo | grep "Error\|raise\|msg"
```

For the bf16 guard tests, the error message must contain:

- `"Apple Silicon"`
- `"fp16"` or `"PrecisionConfig.fp16()"`
- `"BF16"` or `"bfloat16"`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3717 / PR #4779 | [notes.md](../../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Original PR #3714 | Used `sys.info.is_apple_silicon()` for platform detection | `sys.info` module does not have `is_apple_silicon` in Mojo v0.26.1 | Always check Mojo v0.26.1 stdlib before using platform detection APIs |
| Edit tool with non-unique string | Tried `Edit` tool with a string that appeared twice in the file | Tool returned "Found 2 matches" error | Provide more surrounding context to make the match unique |
| Assumed tests weren't covered by CI | Considered adding test to workflow before checking | Test was already covered by `training/test_*.mojo` wildcard pattern | Run `validate_test_coverage.py` first before modifying CI workflows |

## Results & Parameters

**Fix applied**: Added `_check_bf16_platform_support(is_apple: Bool)` to
`<project-root>/shared/training/precision_config.mojo`

**Mojo v0.26.1 Platform API Status**:

- `sys.info.is_apple_silicon()` — does NOT exist
- Accept `is_apple: Bool` as parameter — works on all platforms

**Validation command** (no Mojo required):

```bash
python3 scripts/validate_test_coverage.py
# Exit 0 with no output = all tests covered
```

**Key investigation commands**:

```bash
# Find prior fix attempts across all branches
git log --oneline --all | grep -i "bf16\|apple\|<keyword>"

# See exact changes from any commit
git show <sha> -- <file>

# Check CI failure logs (filter for relevant module)
gh run view <run-id> --log-failed | grep -E "Building:|Failed:|<module_name>"
```

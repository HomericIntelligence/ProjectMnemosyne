---
name: fix-placeholder-code-ci
description: "Fix CI failures caused by partially commented placeholder code and dtype migration assertion mismatches"
category: testing
date: 2025-12-31
---

# Fix Placeholder Code CI Failures

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2025-12-31 |
| **Objective** | Fix CI failures from partially commented placeholder code and dtype migration assertion mismatches |
| **Outcome** | Success - All 58 CI checks passing |
| **Repository** | ProjectOdyssey PR #3017 |

## When to Use This Skill

Use this skill when you encounter:

- **Parse errors** with "use of unknown declaration" for variables that should exist
- **Assertion failures** after migrating types/dtypes (e.g., `float16` → `bfloat16`)
- **Merge conflicts** that may have left orphaned code references
- **CI failures** after rebasing on main with breaking changes

## Verified Workflow

### Phase 1: Diagnose the Failure

```bash
# Get failed job logs
gh run view <run_id> --repo <owner>/<repo> --log-failed 2>&1 | head -200

# Search for specific errors
gh run view <run_id> --repo <owner>/<repo> --log-failed 2>&1 | grep -A 50 "error:\|FAILED"
```

### Phase 2: Identify Placeholder Code Issues

**Pattern to look for:**

```mojo
# BAD - Function commented but usage code is not
# var parts = split(a, 3)  # TODO: Implement split()

# Should give 3 tensors of size 4 each
if len(parts) != 3:           # ❌ ERROR: 'parts' is undeclared
    raise Error("...")
```

**Fix pattern:**

```mojo
# GOOD - Comment out ALL code that uses the placeholder
# TODO(#3013): Implement split()
# var parts = split(a, 3)
#
# # Should give 3 tensors of size 4 each
# if len(parts) != 3:
#     raise Error("...")
_ = a  # Suppress unused variable warning
```

### Phase 3: Fix Type Migration Assertions

When migrating types (e.g., aliased `float16` → native `bfloat16`):

```mojo
# BEFORE (old aliased behavior)
assert_equal(
    tensor.dtype(),
    DType.float16,  # ❌ Wrong after migration
    "BF16 tensor should have float16 dtype (aliased)",
)

# AFTER (native type behavior)
assert_equal(
    tensor.dtype(),
    DType.bfloat16,  # ✅ Correct for native bfloat16
    "BF16 tensor should have native bfloat16 dtype",
)
```

### Phase 4: Always Rebase Before Pushing

**CRITICAL**: Never wait for CI when there are merge conflicts.

```bash
# 1. Fetch latest main
git fetch origin main

# 2. Rebase on main (use -X theirs for simple conflicts)
git rebase origin/main -X theirs

# 3. Handle modify/delete conflicts
git rm <deleted_files>
git rebase --continue

# 4. Run pre-commit locally
just pre-commit-all

# 5. Push to trigger CI
git push --force-with-lease origin <branch>
```

## Failed Attempts

| What Was Tried | Why It Failed | Correct Approach |
|----------------|---------------|------------------|
| Waited for CI with merge conflicts | "Pointless to wait" - CI will fail on conflicts | **Always rebase main first, then push** |
| Commented only the function call `# var parts = ...` | Code using `parts` still executed, causing parse error | **Comment out ALL code referencing the placeholder** |
| Left old dtype assertions after type migration | Assertions expected old aliased type, got new native type | **Update assertions to match new behavior** |
| Commented function but left orphaned docstring | Orphaned `Returns:` line caused parse error | **Comment out entire docstring blocks** |

## Results & Parameters

### Files Fixed in Session

1. **`tests/shared/core/test_shape.mojo`** (lines 283-317)
   - Issue: `parts` variable undeclared
   - Fix: Comment out all code using `parts`, add `_ = a` to suppress warnings

2. **`tests/shared/training/test_dtype_utils.mojo`** (lines 192-207)
   - Issue: Expected `DType.float16` but got `DType.bfloat16`
   - Fix: Update assertion to expect `DType.bfloat16`

3. **`tests/shared/conftest.mojo`** (line 77)
   - Issue: Orphaned `Returns:` docstring line
   - Fix: Properly comment out entire docstring block

### CI Commands Used

```bash
# Check PR status
gh pr checks <pr_number> --repo <owner>/<repo>

# View failed logs
gh run view <run_id> --repo <owner>/<repo> --log-failed

# Run pre-commit locally before pushing
just pre-commit-all

# Push after fixes
git push origin <branch>
```

## Key Lessons

1. **Placeholder code must be fully commented** - If you comment out a function call, comment out ALL code that uses its return value

2. **Type migrations require assertion updates** - When changing from aliased to native types, update all test assertions

3. **Rebase before CI** - Never wait for CI when merge conflicts exist; rebase first

4. **Check for orphaned docstrings** - Merge conflicts can leave partial docstrings that cause parse errors

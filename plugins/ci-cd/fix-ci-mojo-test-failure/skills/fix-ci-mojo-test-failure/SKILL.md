---
name: fix-ci-mojo-test-failure
description: "TRIGGER CONDITIONS: CI failing with Mojo test assertion error, edge case handling missing"
category: ci-cd
source: ProjectOdyssey
date: 2026-01-01
---

# fix-ci-mojo-test-failure

Systematic workflow for diagnosing and fixing CI failures caused by Mojo test assertion errors.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-01 |
| Objective | Fix CI failures for PR #3050 where test expected empty list but got non-empty |
| Outcome | Success - All 54 CI checks passed after fix |

## When to Use

- CI failing with "Values are not equal" or similar assertion error in Mojo tests
- Test expects specific return value (empty list, specific number) but implementation returns different
- Edge case not handled in implementation (empty inputs, single element, boundary conditions)
- New tests added in PR reveal implementation gaps

## Verified Workflow

Step-by-step process that worked:

1. **Check CI status**: Run `gh pr checks <pr-number>` to identify failing jobs
2. **Get failed logs**: Run `gh run view <run-id> --log-failed` to see detailed error output
3. **Locate failing test**: Grep for "FAILED", "error:", or "assertion" in the logs
4. **Checkout PR branch**: `git fetch origin <branch> && git checkout <branch>`
5. **Read the test file**: Understand what the test expects
6. **Read the implementation**: Identify why it returns unexpected value
7. **Apply minimal fix**: Add early return for edge cases or fix initialization
8. **Run test locally**: `pixi run mojo run <test-file>` (note: `mojo test` doesn't exist)
9. **Run pre-commit**: `just pre-commit-all` to ensure formatting passes
10. **Commit with conventional format**: `fix(scope): description`
11. **Push and verify CI**: Wait for all checks to pass

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Read main branch test file | Test didn't exist on main - was added in PR | Always checkout PR branch before investigating |
| Use `mojo test` command | Command doesn't exist in current Mojo version | Use `mojo run` for test files with `main()` function |
| Initial `max_class = 0` | Created 1x1 matrix for empty inputs instead of empty matrix | Initialize to -1 when empty input should produce empty output |

## Results & Parameters

The fix applied to `compute_confusion_matrix` function:

```mojo
fn compute_confusion_matrix(
    y_true: List[Int], y_pred: List[Int], num_classes: Int = 0
) -> List[List[Int]]:
    # Handle empty inputs - return empty matrix unless num_classes is specified
    if len(y_true) == 0 and len(y_pred) == 0 and num_classes == 0:
        return List[List[Int]]()

    # Initialize max_class to -1 (not 0) so empty lists give n_classes = 0
    var max_class = -1
    # ... rest of implementation
```

Key commands used:

```bash
# Check CI status
gh pr checks 3050

# Get failed logs
gh run view 20635532846 --log-failed 2>&1 | grep -A 50 -E "(FAILED|Error)"

# Run Mojo test locally
pixi run mojo run tests/shared/utils/test_visualization.mojo

# Pre-commit all files
just pre-commit-all
```

## References

- Source PR: ProjectOdyssey#3050
- Fix commit: 93f92a3b
- Related: Edge case handling patterns for list functions

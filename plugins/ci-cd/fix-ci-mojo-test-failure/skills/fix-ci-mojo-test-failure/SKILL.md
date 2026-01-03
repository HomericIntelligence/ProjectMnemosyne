---
name: fix-ci-mojo-test-failure
description: "TRIGGER CONDITIONS: CI failing with Mojo test assertion error, edge case handling missing"
category: ci-cd
date: 2026-01-01
---

# fix-ci-mojo-test-failure

Systematic workflow for diagnosing and fixing CI failures caused by Mojo test assertion errors.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-01 |
| Objective | Fix CI failures where test expects specific value but implementation returns different |
| Outcome | Success |

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
8. **Run test locally**: `<package-manager> run mojo run <test-file>` (note: `mojo test` may not exist in all versions)
9. **Run pre-commit**: Validate formatting passes
10. **Commit with conventional format**: `fix(scope): description`
11. **Push and verify CI**: Wait for all checks to pass

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Read main branch test file | Test didn't exist on main - was added in PR | Always checkout PR branch before investigating |
| Use `mojo test` command | Command doesn't exist in some Mojo versions | Use `mojo run` for test files with `main()` function |
| Initialize loop variable to 0 | Created 1x1 matrix for empty inputs instead of empty matrix | Initialize to -1 when empty input should produce empty output |

## Results & Parameters

Common pattern for fixing edge cases:

```mojo
fn some_function(input: List[T]) -> List[U]:
    # Handle empty inputs - return empty result
    if len(input) == 0:
        return List[U]()

    # Initialize max/min to -1 (not 0) so empty lists give correct result
    var max_val = -1
    # ... rest of implementation
```

Key commands:

```bash
# Check CI status
gh pr checks <pr-number>

# Get failed logs
gh run view <run-id> --log-failed 2>&1 | grep -A 50 -E "(FAILED|Error)"

# Run Mojo test locally
<package-manager> run mojo run <test-path>

# Pre-commit all files
<pre-commit-command>
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3050 - confusion matrix edge case | [notes.md](../../references/notes.md) |

## References

- Related: Edge case handling patterns for list functions
- Mojo test documentation: https://docs.modular.com/mojo/cli/test
